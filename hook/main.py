from __future__ import annotations

import os
import re
import shutil
import sys

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from . import borg
from .config import get_config, get_from_pk
from .constants import RC, Paths
from .utils import BadRepoError, get_logger, without_temp

logger = get_logger()


def check_repo(repo: str, user: str | None, *, release_on_restart=False):
    if not release_on_restart:
        logger.info(f'Checking repo {repo} for user {user}...')

        lock_user = Paths.lock_user.read_text()
        if user != lock_user:
            msg = f'User from pk is {user} but lock was taken by {lock_user}'
            raise AssertionError(msg)

        prev_arcs = without_temp(Paths.lock_prev_arcs.read_text(), user)

    else:
        logger.info(f'Checking repo {repo} for release_on_restart...')

        try:
            user = Paths.lock_user.read_text()
            prev_arcs = without_temp(Paths.lock_prev_arcs.read_text(), user)
        except FileNotFoundError as e:
            # Lock was incompletely written, so no "borg serve" should have taken place.
            # Anyway, can't check without any of those files.
            logger.info('...but lock is incomplete. Skipping.', exc_info=e)
            return

        # Note: `borg break-lock` is not used, because it's possible for borg-daily to be running.

    cur_arcs = without_temp(borg.dump_arcs(repo), user)

    # Check that previous archives are intact, except for f'{user}(temp)'
    if not cur_arcs.startswith(prev_arcs):
        msg = 'Previous archives were modified!'
        raise BadRepoError(msg)

    # Check that new archives begin with user prefix (excluding f'{user}(temp)')
    new_arcs = cur_arcs.replace(prev_arcs, '', 1)
    while new_arcs:
        _arc_id, _sep, new_arcs = new_arcs.partition('\x00')
        arc_name, _sep, new_arcs = new_arcs.partition('\x00')
        if not arc_name.startswith(user + '-'):
            msg = f"Created [{arc_name}] that doesn't start with [{user}-]!"
            raise BadRepoError(msg)

    logger.info('...OK')


@retry(
    retry=retry_if_exception_type(FileExistsError),
    wait=wait_fixed(1),
    stop=stop_after_attempt(4),
    reraise=True,
)
def mkdir_lock():
    """
    When two ssh commands are executed consecutively,
    the first close_session is executed about 0.5s after the second open_session.
    So retry for 3s so the late hook can finish releasing.
    """
    Paths.lock.mkdir()


def acquire_lock(repo: str, user: str):
    logger.info(f'{user} is acquiring lock for {repo}...')

    if not Paths.repo_enabled.exists():
        logger.warning('Repo access is disabled')
        sys.exit(RC.access_denied)

    if not borg.is_repo_unlocked(repo):
        logger.warning('Underlying repo is locked')
        sys.exit(RC.access_denied)

    try:
        mkdir_lock()
    except FileExistsError:
        logger.warning(f'Repo is locked by user {Paths.lock_user.read_text()}')
        # Note: there's a small window for lock_user read to fail. Ignore.
        sys.exit(RC.access_denied)

    Paths.lock_user.write_text(user)
    Paths.lock_prev_arcs.write_text(borg.dump_arcs(repo))
    logger.info('...OK')


def release_lock(repo: str, user: str):
    try:
        check_repo(repo, user)
        shutil.rmtree(Paths.lock)
    except Exception:
        logger.exception('Error releasing lock')
        sys.exit(RC.generic_error)


def release_lock_on_restart():
    config_users = get_config()['users']
    repos = {u['repo'] for u in config_users}

    for repo in repos:
        Paths.set_repo_name(repo)
        is_enabled = Paths.repo_enabled.exists()
        if not is_enabled:
            continue
        is_locked = Paths.lock.is_dir()
        if not is_locked:
            continue
        try:
            check_repo(repo, None, release_on_restart=True)
            shutil.rmtree(Paths.lock)
        except Exception:
            logger.exception('Error releasing lock')


def main(argv):
    """
    When a client requests the repository, this hook can be called on 3 occasions:

    (1) By PAM when the session is opened (open_session).
        If the hook fails, access is denied and close_session is not called.
        So it's better to acquire lock here.

    (2) By the forced SSH command.
        If the hook fails, borg serve is denied but close_session is called.
        With command="pre && borg serve; post", post is not executed on broken connection.
        I don't know if there's a reliable way to trigger it.

    (3) By PAM when the session is closed (close_session).
        This is called even on broken connections, so lock release should happen here.
        Also lock should be released on boot, before starting hpnsshd in case server crashed with lock held.
        Nothing can be done by failing this hook, even stdout is not delivered haha.

    So don't even call on (2). PAM hooks can get repo and user from $SSH_AUTH_INFO_0
    """

    hook_src = argv[1] if len(argv) > 1 else None
    if hook_src == 'tamborg-release-lock':
        release_lock_on_restart()
        return
    if hook_src != 'pam':
        logger.error(f'Invalid hook_src: {hook_src}')
        sys.exit(RC.invalid_usage)

    ssh_auth_info = os.environ.get('SSH_AUTH_INFO_0')
    try:
        pk = re.fullmatch(r'publickey ([a-z0-9-]+ [a-zA-Z0-9+/=]+)\n?', ssh_auth_info)[1]
        repo, user = get_from_pk(pk)
    except Exception:
        logger.exception(f'Failed to get user from pubkey. $SSH_AUTH_INFO_0: {ssh_auth_info!r}')
        sys.exit(RC.invalid_usage)

    Paths.set_repo_name(repo)
    Paths.repo_state.mkdir(parents=True, exist_ok=True)

    pam_type = os.environ.get('PAM_TYPE')
    match pam_type:
        case 'open_session':
            acquire_lock(repo, user)
        case 'close_session':
            release_lock(repo, user)
        case _:
            logger.error(f'Bad $PAM_TYPE: [{pam_type}]')
            sys.exit(RC.invalid_usage)


if __name__ == '__main__':
    main(sys.argv)
