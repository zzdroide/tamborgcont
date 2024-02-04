import os
from pathlib import Path
import shutil
import sys

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from . import Borg
from .config import does_user_exist
from .constants import Paths, RC
from .utils import getidx, mkfile


def check_repo():
    try:
        with (
            open(Paths.lock_user, 'r') as f_user,
            open(Paths.lock_prev_arcs, 'r') as f_pa,
        ):
            user_prefix = f_user.read() + '-'
            prev_arcs = f_pa.read()
            cur_arcs = Borg.dump_arcs()

            # Check that previous archives are intact
            if not cur_arcs.startswith(prev_arcs):
                return False, 'Previous archives were modified!'

            # Check that new archives begin with user_prefix
            new_arcs = cur_arcs.replace(prev_arcs, '', 1)
            while new_arcs:
                arc_id, sep, new_arcs = new_arcs.partition('\x00')
                arc_name, sep, new_arcs = new_arcs.partition('\x00')
                if not arc_name.startswith(user_prefix):
                    return False, f"Created [{arc_name}] that doesn't start with [{user_prefix}]!"

        return True, None

    except FileNotFoundError:
        # We are at release_lock(). Assume that fill_lock() wasn't called.
        # Anyway, with any of the two files missing we can't check the repo.
        return True, None


def get_repo_locked_msg():
    with open(Paths.lock_ip, 'r') as f:
        ip = f.read()

    try:
        with open(Paths.lock_user, 'r') as f:
            user = f.read()
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
    '''
    When two ssh commands are executed consecutively,
    the first close_session is executed about 0.5s after the second open_session.
    So retry for 3s instead of failing immediately.
    '''
    os.remove(Paths.repo_is_ok)


def acquire_lock():
    try:
        remove_repo_is_ok()
    except FileNotFoundError:
        print('Repo is NOT OK')
        sys.exit(RC.access_denied)

    if not Borg.is_repo_unlocked():
        print('Underlying repo is locked')
        sys.exit(RC.access_denied)

    try:
        os.mkdir(Paths.lock)
    except FileExistsError:
        print(get_repo_locked_msg())
        sys.exit(RC.access_denied)

    with open(Paths.lock_ip, 'x') as f:
        f.write(os.environ.get('PAM_RHOST'))


def fill_lock(key_user):
    if not does_user_exist(key_user):
        print(f'User not in config: {key_user}')
        sys.exit(RC.access_denied)

    with open(Paths.lock_user, 'x') as f:
        f.write(key_user)

    with open(Paths.lock_prev_arcs, 'x') as f:
        f.write(Borg.dump_arcs())


def release_lock():
    ok, errmsg = check_repo()

    if ok:
        shutil.rmtree(Paths.lock)
        mkfile(Paths.repo_is_ok)
    else:
        print(errmsg)
        sys.exit(RC.generic_error)


def main(argv):
    """
    This script is called on 3 occasions:
      1. by PAM when the session is opened (`acquire_lock()`)
      2. by the forced SSH command (`fill_lock()`)
      3. by PAM when the session is closed (`release_lock()`)

    (1) takes the lock, (2) fills it, and (3) checks and releases.
    """

    Path(Paths.state).mkdir(exist_ok=True)

    hook_src = getidx(argv, 1)
    if hook_src == 'pam':
        pam_type = os.environ.get('PAM_TYPE')
        if pam_type == 'open_session':
            acquire_lock()
        elif pam_type == 'close_session':
            release_lock()
        else:
            print(f'Invalid $PAM_TYPE: {pam_type}')
            sys.exit(RC.invalid_usage)

    elif hook_src == 'ssh_command':
        key_user = getidx(argv, 2)
        if key_user:
            fill_lock(key_user)
        else:
            print('"ssh_command" without key_user')
            sys.exit(RC.invalid_usage)

    else:
        print(f'Invalid hook_src: {hook_src}')
        sys.exit(RC.invalid_usage)


if __name__ == '__main__':
    main(sys.argv)
