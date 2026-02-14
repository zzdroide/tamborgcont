from __future__ import annotations

import shutil
from contextlib import contextmanager, suppress
from datetime import datetime
from typing import TYPE_CHECKING

import sh
import wakeonlan

from daily.http_server import HttpServer
from daily.smarthealthc import smarthealthc
from daily.utils import JoinRaiseThread, hc_ping
from shared.config import (
    get_config,
    get_config_repos,
)
from shared.constants import Paths
from shared.pubsub import PubSub
from shared.shell import Borg, Mirror
from shared.utils import LoggerPurpose, get_logger, mkdir_lock

if TYPE_CHECKING:
    from pathlib import Path


def get_is_weekly():
    TUESDAY = 1
    now = datetime.now().astimezone()

    if now.weekday() == TUESDAY:
        return True

    force_until = get_config().get('force_weekly_until')
    if force_until:
        if isinstance(force_until, str):
            force_until = datetime.fromisoformat(force_until).date()
        if now.date() <= force_until:
            return True

    return False


def main():
    hc_url = get_config()['weekly_healthcheck']
    is_weekly = get_is_weekly()

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


class ProcessRepo(JoinRaiseThread):
    def __init__(self, repo: str, http_server: HttpServer, *, is_weekly: bool):
        logger = get_logger(repo, LoggerPurpose.DAILY)
        super().__init__(repo, logger)
        self.repo = repo
        self.logger = logger
        self.is_weekly = is_weekly
        self.paths = Paths(repo)
        self.borg = Borg(self.paths)
        self.pubsub = PubSub(self.paths, start=True)

        mirror_host = get_config()['repos'][repo].get('mirror_host')
        self.mirror = Mirror(mirror_host) if mirror_host else None

        def set_waiting_for(user: str | None):
            if user:
                http_server.repo_waiting[repo] = user
            else:
                http_server.repo_waiting.pop(repo, None)
        self.set_waiting_for = set_waiting_for

    def _run(self):
        if not self.paths.repo_enabled.exists():
            self.logger.debug('Repo is disabled')
            return
        if self.paths.lock.is_dir():
            self.logger.debug(f'Lock is taken by {self.paths.lock_user.read_text()}')
            return

        auto_users = (u for u in get_config()['users'] if u['repo'] == self.repo and u.get('ssh'))
        try:
            for user in auto_users:
                self.run_user(user)

            if self.is_weekly:
                self.set_waiting_for('run_weekly')
                self.run_weekly()
            else:
                self.set_waiting_for(None)
                if self.mirror:
                    self.rsync_current(link_dest=self.mirror.CURRENT)
        finally:
            self.set_waiting_for(None)

    def run_user(self, user):
        self.logger.debug(f'{user['user']}: waiting_for')
        self.set_waiting_for(user['user'])

        ssh_cfg = SshConfig(user['ssh'])
        started, ssh_error = ssh_tamborgmatic_auto(ssh_cfg)

        if started:
            self.logger.debug(f'{user['user']}: started by ssh')
        else:
            wol_timed_out = False
            if user.get('mac'):
                wol(ssh_cfg, user['mac'])
                # Wait for on_auto_backup.sh signal:
                started = self.pubsub.wait_for(match=f'lock_acquired {user['user']}', timeout=60)

                if started:
                    self.pubsub.wait_for(prefix=f'lock_released {user['user']} ')
                    self.logger.debug(f'{user['user']}: WOL success')
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

    @contextmanager
    def data_snapshot(self, to_path: Path):
        '''
        Using a hardlinked copy is safe:
        - "[segments] are strictly append-only and modified only once."  https://borgbackup.readthedocs.io/en/stable/internals/data-structures.html#segments
        - https://github.com/borgbackup/borg/commit/4a2ab496e09b5feb5dcdb326f0c56aba1563e7ed#diff-57498cd583e81bed522aee757fb13023a9a6f99b343af93c6082f4da1bec69a0R228-R229
        '''
        with suppress(FileNotFoundError):
            shutil.rmtree(to_path)
        self.borg.with_lock.cp('-al', self.paths.repo_data, to_path)
        try:
            yield
        finally:
            shutil.rmtree(to_path)

    def rsync_current(self, *, link_dest):
        self.logger.debug('Rsyncing current to mirror...')
        with self.mirror.mount(), self.data_snapshot(self.paths.repo_snap_current):
            self.mirror.rsync(
                '-rt',
                f'--link-dest={link_dest}',
                f'{self.paths.repo_snap_current}/',
                f'{self.mirror.destination}:{self.mirror.CURRENT_NEW}'
            )
            self.mirror.promote(self.mirror.CURRENT_NEW, self.mirror.CURRENT)

    def delete_mirror_damaged(self):
        '''
        The mirror keeps two copies of the repo data: onec current and one checked.
        When a new copy is rsynced, it's made into current.new/checked.new first,
        and then promoted to current/checked.
        They use hardlinks across segments to save space, but before rsyncing `checked`,
        confirm that its sources (that will be hardlinked) are intact.
        Detects if a file got corrupted, but not if it got deleted.
        '''
        checksum_out = self.mirror.nice_stdout_rsync(
            '-rt',
            '--checksum',
            '--dry-run',
            '--itemize-changes',
            f'{self.paths.repo_snap_checked}/',
            f'{self.mirror.destination}:{self.mirror.CURRENT}',
            _iter='out',
        )
        damaged_files = [
            line.rstrip('\n').split(' ')[1]
            for line in checksum_out
            if line.startswith('<f') and not line.startswith('<f+++')
        ]
        if damaged_files:
            self.logger.warning(f'Deleting damaged files in mirror: {damaged_files}')
            self.mirror.rsync(
                '--files-from=-',
                '--delete-missing-args',
                '/var/empty/',
                f'{self.mirror.destination}:{self.mirror.CURRENT}',
                _in='\n'.join(damaged_files),
                _ok_code=[0, 24],  # 24: "some files vanished" is expected when source is empty
            )
        else:
            self.logger.debug('No damaged files in mirror')
        return damaged_files

    def prune_compact(self):
        self.logger.debug('Pruning...')
        prune_kwargs = get_config()['repos'][self.repo]['prune']
        within_kwargs = {
            **prune_kwargs,
            'keep_within': f"{prune_kwargs['keep_daily']}d",
        }
        within_kwargs.pop('keep_daily', None)

        for u in filter(lambda u: u['repo'] == self.repo, get_config()['users']):
            self.borg.prune(u['user'], **within_kwargs)
            self.borg.prune(u['user'], **prune_kwargs)
            # Two similar prunes to handle different cases. Assume today is 2026-01-01:
            #
            # Pass 1 (keep_within={keep_daily}d + keep_weekly + ...):
            #   Ensures not too much far granularity is kept. For example, a computer which backups once a month,
            #   but that backed up every day from 2025-08-01 to 2025-08-10,
            #   keep_daily=15 would keep the following 15 archives:
            #   2025-12-01, 2025-11-01, 2025-10-01, 2025-09-01, 2025-08-10, 2025-08-09, ... 2025-08-01, ...
            #   Instead, keep_within=15d and keep_weekly leave only backups for 3 and 10 of August (one per week).
            #
            # Pass 2 (keep_daily + keep_weekly + ...):
            #   Prunes same-day duplicates. If a computer backed up twice on 2025-12-30 (within keep_within=15d),
            #   only the second archive of those is kept.
            #
            # Swapping the order of the passes would protect more far archives.

        self.logger.debug('Compacting...')
        compaction_threshold = get_config()['repos'][self.repo].get('compaction_threshold', 10)
        self.borg.compact(compaction_threshold)
        self.logger.debug('Compaction completed')

    def run_weekly(self):
        self.logger.debug('run_weekly: started')
        try:
            mkdir_lock(self.paths)
            self.paths.lock_user.write_text('run_weekly')
        except FileExistsError:
            msg = f'Lock taken by {self.paths.lock_user.read_text()}'
            raise RuntimeError(msg) from None

        autorelease_lock = True
        try:
            # Delete temp archives now, to skip checking them.
            self.logger.debug('Deleting temp archives...')
            self.borg.delete_temp_archives()

            # Check repo
            def on_check_output_line(line: str):
                self.logger.debug(f'borg check: {line}')
            try:
                autorelease_lock = False
                self.borg.check(on_check_output_line)
                autorelease_lock = True
            except sh.ErrorReturnCode as e:
                self.logger.info('Append-only rollback instructions: https://borgbackup.readthedocs.io/en/stable/usage/notes.html#append-only-mode-forbid-compaction')
                msg = f'borg check failed with rc={e.exit_code}'
                raise RuntimeError(msg) from None

            damaged_files = []
            if self.mirror:
                with self.mirror.mount(), self.data_snapshot(self.paths.repo_snap_checked):
                    damaged_files = self.delete_mirror_damaged()
                    # The method above is HDD-bound (uses ionice),
                    # so trying to do other operations in parallel would be slower, because of HDD thrasing.

                    # `compact` is HDD-bound too (uses ionice), but the next rsync is internet-bound,
                    # so both can run in parallel. TODO: does this thrash?
                    outer_self = self

                    class PruneThread(JoinRaiseThread):
                        def _run(self):
                            outer_self.prune_compact()

                    prune_thread = PruneThread(self.repo, self.logger)
                    prune_thread.start()

                    self.logger.debug('Rsyncing checked to mirror...')
                    self.mirror.rsync(
                        '-rt',
                        f'--link-dest={self.mirror.CURRENT}',
                        f'{self.paths.repo_snap_checked}/',
                        f'{self.mirror.destination}:{self.mirror.CHECKED_NEW}',
                    )
                    self.mirror.promote(self.mirror.CHECKED_NEW, self.mirror.CHECKED)
                    self.logger.debug('Rsync checked to mirror completed')
                    # Note: Usually no "...completed" messages are logged,
                    # but it's made here because there are two threads running in parallel.

                prune_thread.join_raise()
                # After prune+compact+rsync_checked, the new "current" copy is ready to be rsynced.
                self.rsync_current(
                    link_dest=self.mirror.CHECKED  # The latest copy was to checked instead of current
                )
            else:
                self.prune_compact()

        finally:
            if autorelease_lock:
                shutil.rmtree(self.paths.lock)
                # Note: this could release the lock while prune_thread is running. But it doesn't matter:
                # instead of the hook reliably blocking access with "Repo is locked by user run_weekly",
                # it will less reliably block with "Underlying repo is locked".

        if damaged_files:
            msg = 'run_weekly completed successfully, but mirror had damaged files'
            raise RuntimeError(msg)
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
            'sudo systemctl start tamborgmatic-auto.service',
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
