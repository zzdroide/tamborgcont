import os
import sys

from .utils import getidx


RC_INVALID_USAGE = 2


def acquire_lock():
    raise NotImplementedError


def fill_lock(key_user):
    raise NotImplementedError


def release_lock():
    raise NotImplementedError


def main(argv):
    """
    This script is called on 3 occasions:
      1. by PAM when the session is opened
      2. by the forced SSH command
      3. by PAM when the session is closed

    (1) takes the lock, (2) fills it, and (3) checks and releases.
    """

    hook_src = getidx(argv, 1)
    if hook_src == 'pam':
        pam_type = os.environ.get('PAM_TYPE')
        if pam_type == 'open_session':
            acquire_lock()
        elif pam_type == 'close_session':
            release_lock()
        else:
            print(f'Invalid $PAM_TYPE: {pam_type}')
            sys.exit(RC_INVALID_USAGE)

    elif hook_src == 'ssh_command':
        key_user = getidx(argv, 2)
        if key_user:
            fill_lock(key_user)
        else:
            print('"ssh_command" without key_user')
            sys.exit(RC_INVALID_USAGE)

    else:
        print(f'Invalid hook_src: {hook_src}')
        sys.exit(RC_INVALID_USAGE)


if __name__ == '__main__':
    main(sys.argv)
