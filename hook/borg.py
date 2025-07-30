import sh


def is_repo_unlocked(repo: str):
    try:
        sh.borg('with-lock', f'/home/borg/{repo}', 'true')
        return True
    except sh.ErrorReturnCode:
        return False


def dump_arcs(repo: str):
    return sh.borg.list(
        # Separates with {NUL} ('\x00') because it's the only forbidden character
        # in archive names.
        '--format={id}{NUL}{barchive}{NUL}',
        '--consider-checkpoints',
        f'/home/borg/{repo}',
    )
