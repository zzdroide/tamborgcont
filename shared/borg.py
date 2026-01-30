import os

import sh


class Borg:
    def __init__(self, repo: str):
        self.repo = repo

        self.env = os.environ.copy()
        self.env['BORG_REPO'] = f'/home/borg/{repo}'
        self.env['BORG_PASSCOMMAND'] = f'bash -c "source ~/env/{repo} && echo $BORG_PASSPHRASE"'

    def is_repo_unlocked(self):
        try:
            sh.borg(
                'with-lock',
                '::',
                'true',
                _env=self.env,
                _no_out=True,
            )
            return True
        except sh.ErrorReturnCode:
            return False

    def dump_arcs(self):
        return sh.borg.list(
            # Separates with {NUL} ('\x00') because it's the only forbidden character
            # in archive names.
            format='{id}{NUL}{barchive}{NUL}',
            consider_checkpoints=True,
            _env=self.env,
        )

    def delete_temp_archives(self):
        sh.borg.delete(
            glob_archives='*(temp)-*',
            _env=self.env,
        )

    def check(self, on_output_line):
        sh.borg(
            '--verbose',
            'check',
            '--verify-data',
            _env=self.env,
            _out=on_output_line,
            _err_to_out=True,
        )
        # This will detect malicious tampering:
        #   The archive id is authenticating the metadata chunks list,
        #   which is authenticating the metadata chunks,
        #   which are authenticating the metadata and the data chunks.
        # Source: https://github.com/borgbackup/borg/issues/2251#issuecomment-284189633
