import sh


def is_repo_unlocked():
    try:
        sh.borg('with-lock', 'true')
        return True  # noqa: TRY300
    except sh.ErrorReturnCode:
        return False


def dump_arcs():
    return sh.borg.list(
            # Separates with {NUL} ('\x00') because it's the only forbidden character
            # in archive names.
            format='{id}{NUL}{barchive}{NUL}',
            consider_checkpoints=True,
    )
