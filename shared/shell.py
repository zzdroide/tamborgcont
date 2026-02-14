import os
import sys
from contextlib import contextmanager
from pathlib import Path

import sh

from shared.constants import Paths

nice = sh.nice.bake('-n19', 'ionice', '-c2', '-n7')


class Borg:
    def __init__(self, paths: Paths):
        env = os.environ.copy()
        env['BORG_REPO'] = str(paths.repo)
        env['BORG_PASSCOMMAND'] = f'bash -c "source {paths.env} && echo $BORG_PASSPHRASE"'
        self._borg = sh.borg.bake(_env=env)
        self._nice_borg = nice.borg.bake(_env=env)
        self.with_lock = self._borg.bake('with-lock', '::')

    def is_repo_unlocked(self):
        try:
            self.with_lock('true', _no_out=True)
            return True
        except sh.ErrorReturnCode:
            return False

    def dump_arcs(self):
        return self._borg.list(
            # Separates with {NUL} ('\x00') because it's the only forbidden character
            # in archive names.
            format='{id}{NUL}{barchive}{NUL}',
            consider_checkpoints=True,
        )

    def delete_temp_archives(self):
        self._borg.delete(glob_archives='*(temp)-*')

    def check(self, on_output_line):
        self._nice_borg(
            '--verbose',
            'check',
            '--verify-data',
            _out=on_output_line,
            _err_to_out=True,
        )
        # This will detect malicious tampering:
        #   The archive id is authenticating the metadata chunks list,
        #   which is authenticating the metadata chunks,
        #   which are authenticating the metadata and the data chunks.
        # Source: https://github.com/borgbackup/borg/issues/2251#issuecomment-284189633

    def prune(self, user, **kwargs):
        self._borg.prune(glob_archives=f'{user}-*', **kwargs)

    def compact(self, threshold):
        self._nice_borg.compact(threshold=threshold)


class Mirror:
    MOUNT_POINT = Path('/mnt/tamborg_mirror')
    CURRENT = MOUNT_POINT / 'current'
    CURRENT_NEW = MOUNT_POINT / 'current.new'
    CHECKED = MOUNT_POINT / 'checked'
    CHECKED_NEW = MOUNT_POINT / 'checked.new'

    def __init__(self, host: str):
        ssh_opts = [
            '-oBatchMode=yes',
            '-oNoneEnabled=yes',
            '-oNoneSwitch=yes',
            '-oConnectTimeout=10',
            '-oServerAliveInterval=30',
            '-oServerAliveCountMax=2',
            '-p1701',
        ]
        self.destination = f'mirror@{host}'
        self.ssh = sh.hpnssh.bake(*ssh_opts, self.destination)

        rsync_rsh = ' '.join(['hpnssh', *ssh_opts])
        self.rsync = sh.rsync.bake(rsh=rsync_rsh, stats=True, _out=sys.stdout, _err_to_out=True)
        self.nice_stdout_rsync = nice.rsync.bake(rsh=rsync_rsh, _err=sys.stderr)

    @contextmanager
    def mount(self):
        self.ssh(f'grep -q {self.MOUNT_POINT} /proc/mounts || mount {self.MOUNT_POINT}')
        # Note: mount --onlyonce didn't work together with `users` option.
        try:
            yield
        finally:
            self.ssh.umount(self.MOUNT_POINT)

    def promote(self, source, dest):
        self.ssh(f'rm -rf {dest} && mv {source} {dest}')
