from __future__ import annotations

import logging
import shutil
from datetime import datetime
from threading import Thread

import sh
import wakeonlan

from daily.http_server import HttpServer
from daily.smarthealthc import smarthealthc
from daily.utils import hc_ping
from shared.borg import Borg
from shared.config import get_config, get_config_repos, get_config_weekly_healthcheck
from shared.constants import Paths
from shared.pubsub import PubSub
from shared.utils import get_logger, mkdir_lock

TUESDAY = 1


def main():
    hc_url = get_config_weekly_healthcheck()
    is_weekly = datetime.now().astimezone().weekday() == TUESDAY

    def weekly_ping(action: str, data: str | None = None):
        if is_weekly:
            hc_ping(f'{hc_url}/{action}', data)

    weekly_ping('start')
    try:
        http_server = HttpServer()
        threads: list[ProcessRepo] = []

        # Assume each repo is on separate hardisk and can be processed in parallel:
        for repo in get_config_repos():
            t = ProcessRepo(repo, http_server, is_weekly=is_weekly)
            t.start()
            threads.append(t)

        smarthealthc()

        for t in threads:
            t.join_raise()

    except Exception as e:
        weekly_ping('fail', str(e))
        raise
    else:
        weekly_ping('0')  # Success


class ProcessRepo(Thread):
    def __init__(self, repo: str, http_server: HttpServer, *, is_weekly: bool):
        super().__init__(name=repo)
        self.repo = repo
        self.is_weekly = is_weekly
        self.paths = Paths(repo)
        self.borg = Borg(repo)
        self.logger = get_logger(name=repo, syslog_identifier='borg_daily', stderr_level=logging.DEBUG)
        self.pubsub = PubSub(self.paths)
        self.exception: Exception | None = None

        def set_waiting_for(user: str | None):
            if user:
                http_server.repo_waiting[repo] = user
            else:
                http_server.repo_waiting.pop(repo)
        self.set_waiting_for = set_waiting_for

    def run(self):
        try:
            self._run()
        except Exception as e:
            self.logger.exception('')
            self.exception = e

    def join_raise(self, timeout=None):
        self.join(timeout)
        if self.exception:
            raise self.exception

    def _run(self):
        if not self.paths.repo_enabled.exists():
            self.logger.debug('Repo is disabled')
            return

        auto_users = (u for u in get_config()['users'] if u['repo'] == self.repo and u.get('ssh'))
        try:
            for user in auto_users:
                self.run_user(user)
            if self.is_weekly:
                self.set_waiting_for('run_weekly')
                self.run_weekly()
        finally:
            self.set_waiting_for(None)

    def run_user(self, user):
        self.logger.debug(f'Waiting for {user['user']}')
        self.set_waiting_for(user['user'])

        ssh_cfg = SshConfig(user['ssh'])
        started, ssh_error = ssh_tamborgmatic_auto(ssh_cfg)

        if not started:
            wol_timed_out = False
            if user.get('mac'):
                wol(ssh_cfg, user['mac'])
                # Wait for on_auto_backup.sh signal:
                started = self.pubsub.wait_for(match=f'lock_acquired {user['user']}', timeout=60)

                if started:
                    self.pubsub.wait_for(prefix=f'lock_released {user['user']} ')
                    self.logger.debug(f"WOL {user['user']}: success")
                else:
                    wol_timed_out = True

            if not started:
                self.logger.warning(f"Couldn't start tamborgmatic-auto.service on {user['user']}")
                self.logger.warning(f'- SSH: {ssh_error}')
                if wol_timed_out:
                    self.logger.warning('- WOL timed out')
                return

        new_arcs_count = 0
        while new_arcs_count == 0:
            # Lock can be unacquired for long because client is running hooks.sh. Wait up to 30m:
            acquired = self.pubsub.wait_for(match=f'lock_acquired {user['user']}', timeout=30 * 60)
            if not acquired:
                self.logger.error(f'Timeout waiting for {user['user']} to acquire lock')
                return

            # Wait infinitely for lock release. Rely on ssh timeout.
            released = self.pubsub.wait_for(prefix=f'lock_released {user['user']} ')
            new_arcs_count = int(released.split(' ')[2])
            # And loop until an archive is created.
            # This will be smooth on happy path. On failure, it will uselessly wait for 30m.
        self.logger.debug(f'{user['user']}: success')

    def run_weekly(self):
        self.logger.debug('run_weekly started')
        try:
            mkdir_lock(self.paths)
        except FileExistsError:
            msg = f'Lock taken by {self.paths.lock_user.read_text()}'
            raise RuntimeError(msg) from None

        def on_check_output_line(line: str):
            self.logger.debug(f'borg check: {line}')
        try:
            self.borg.check(on_check_output_line)
        except sh.ErrorReturnCode as e:
            self.logger.info('Append-only rollback instructions: https://borgbackup.readthedocs.io/en/stable/usage/notes.html#append-only-mode-forbid-compaction')
            msg = f'borg check failed with rc={e.exit_code}'
            raise RuntimeError(msg) from None

        # TODO: rsync
        # TODO: prune

        shutil.rmtree(self.paths.lock)
        self.logger.debug('run_weekly: success')


class SshConfig:
    user: str
    host: str
    port: str | None

    def __init__(self, ssh_config: str):
        if '@' not in ssh_config:
            msg = f'Invalid SSH config format: {ssh_config}'
            raise ValueError(msg)

        user_host, *port_part = ssh_config.rsplit(':', 1)
        user, host = user_host.rsplit('@', 1)
        port = port_part[0] if port_part else None

        self.user = user
        self.host = host
        self.port = port


def ssh_tamborgmatic_auto(ssh_cfg: SshConfig):
    ssh_opts = ['-oBatchMode=yes', '-oConnectTimeout=5']
    if ssh_cfg.port:
        ssh_opts.append(f'-p{ssh_cfg.port}')
    try:
        sh.ssh(
            *ssh_opts,
            f'{ssh_cfg.user}@{ssh_cfg.host}',
            'systemctl --user start tamborgmatic-auto.service',
            _err_to_out=True,
        )
        return True, ''
    except sh.ErrorReturnCode as e:
        return False, e.stdout.decode().strip()


def wol(ssh_cfg: SshConfig, mac: str):
    # Fixes WOL for a server infested with docker networks.
    # Assumes a /24 netmask.
    # Example: ssh_cfg.host = 10.20.30.40 --> broadcast_ip = 10.20.30.255
    broadcast_ip = f"{ssh_cfg.host.rsplit('.', 1)[0]}.255"

    wakeonlan.send_magic_packet(mac, ip_address=broadcast_ip)


if __name__ == '__main__':
    main()
