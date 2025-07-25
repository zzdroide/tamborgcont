
import os
import shutil
import sys

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from . import borg
from .config import does_user_exist
from .constants import RC, Paths
from .utils import get_logger, mkfile, without_temp

logger = get_logger()


def check_repo():
    logger.info('Checking repo...')
    try:
        user = Paths.lock_user.read_text()
        prev_arcs = without_temp(Paths.lock_prev_arcs.read_text(), user)
        cur_arcs = without_temp(borg.dump_arcs(), user)

        # Check that previous archives are intact, except for f'{user}[temp]'
        if not cur_arcs.startswith(prev_arcs):
            return False, 'Previous archives were modified!'

        # Check that new archives begin with user prefix (excluding f'{user}[temp]')
        new_arcs = cur_arcs.replace(prev_arcs, '', 1)
        while new_arcs:
            _arc_id, _sep, new_arcs = new_arcs.partition('\x00')
            arc_name, _sep, new_arcs = new_arcs.partition('\x00')
            if not arc_name.startswith(user + '-'):
                return False, f"Created [{arc_name}] that doesn't start with [{user}-]!"

        logger.info(f'...for user {user}, is OK')
        return True, None

    except FileNotFoundError:
        # We are at release_lock(). Assume that fill_lock() wasn't called.
        # Anyway, with any of the two files missing we can't check the repo.
        logger.info('...but lock is not filled.')
        return True, None


def get_repo_locked_msg():
    ip = Paths.lock_ip.read_text()

    try:
        user = Paths.lock_user.read_text()
    except FileNotFoundError:
        user = '<unavailable>'

    return f'Repo is locked by user {user} from {ip}'


@retry(
    retry=retry_if_exception_type(FileNotFoundError),
    wait=wait_fixed(1),
    stop=stop_after_attempt(4),
    reraise=True,
)
def remove_repo_is_ok():
    """
    When two ssh commands are executed consecutively,
    the first close_session is executed about 0.5s after the second open_session.
    So retry for 3s instead of failing immediately.
    """
    Paths.repo_is_ok.unlink()


def acquire_lock():
    logger.info(f'{os.environ['PAM_RHOST']} is acquiring lock...')

    try:
        remove_repo_is_ok()
    except FileNotFoundError:
        logger.error('Repo is NOT OK')
        sys.exit(RC.access_denied)

    if not borg.is_repo_unlocked():
        logger.error('Underlying repo is locked')
        sys.exit(RC.access_denied)

    try:
        Paths.lock.mkdir()
    except FileExistsError:
        logger.error(get_repo_locked_msg())
        sys.exit(RC.access_denied)

    Paths.lock_ip.write_text(os.environ['PAM_RHOST'])
    logger.info('...OK')


def fill_lock(key_user):
    logger.info(f'{key_user} is filling lock...')

    if not does_user_exist(key_user):
        logger.error(f'User not in config: {key_user}')
        sys.exit(RC.access_denied)

    Paths.lock_user.write_text(key_user)
    Paths.lock_prev_arcs.write_text(borg.dump_arcs())
    logger.info('...OK')


def release_lock():
    ok, errmsg = check_repo()

    if ok:
        shutil.rmtree(Paths.lock)
        mkfile(Paths.repo_is_ok)
    else:
        logger.error(errmsg)
        sys.exit(RC.generic_error)


def main(argv):
    """
    This script is called on 3 occasions:
      1. by PAM when the session is opened (`acquire_lock()`)
      2. by the forced SSH command (`fill_lock()`)
      3. by PAM when the session is closed (`release_lock()`)

    (1) takes the lock, (2) fills it, and (3) checks and releases.
    """
    hook_src = argv[1] if len(argv) > 1 else None
    key_user = argv[2] if len(argv) > 2 else None

    Paths.state.mkdir(exist_ok=True)

    if hook_src == 'pam':
        pam_type = os.environ.get('PAM_TYPE')
        if pam_type == 'open_session':
            acquire_lock()
        elif pam_type == 'close_session':
            release_lock()
        else:
            logger.error(f'Invalid $PAM_TYPE: {pam_type}')
            sys.exit(RC.invalid_usage)

    elif hook_src == 'ssh_command':
        if key_user:
            fill_lock(key_user)
        else:
            logger.error('"ssh_command" without key_user')
            sys.exit(RC.invalid_usage)

    else:
        logger.error(f'Invalid hook_src: {hook_src}')
        sys.exit(RC.invalid_usage)


if __name__ == '__main__':
    main(sys.argv)
