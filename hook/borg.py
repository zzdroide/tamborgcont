import os

import sh


def make_borg_env(repo: str):
    env = os.environ.copy()
    env['BORG_REPO'] = f'/home/borg/{repo}'
    env['BORG_PASSCOMMAND'] = f'bash -c "source ~/env/{repo} && echo $BORG_PASSPHRASE"'
    return env


def is_repo_unlocked(repo: str):
    try:
        sh.borg(
            'with-lock',
            '::',
            'true',
            _env=make_borg_env(repo),
        )
        return True
    except sh.ErrorReturnCode:
        return False


def dump_arcs(repo: str):
    return sh.borg.list(
        # Separates with {NUL} ('\x00') because it's the only forbidden character
        # in archive names.
        format='{id}{NUL}{barchive}{NUL}',
        consider_checkpoints=True,
        _env=make_borg_env(repo),
    )
