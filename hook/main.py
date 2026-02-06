from __future__ import annotations

import logging
import os
import re
import shutil
import sys

from shared.borg import Borg
from shared.config import get_config_from_pk, get_config_repos
from shared.constants import RC, Paths
from shared.pubsub import PubSub
from shared.utils import get_logger, mkdir_lock

from .utils import BadRepoError, get_waiting_for, without_user_temp

logger = get_logger(
    'borg_ssh_hook',
    # stdout/stderr from this script breaks borg with: Got unexpected RPC data format from server: <message>
    # So if access is going to be granted, log up to INFO only.
    # On access denied, you can output whatever you want.
    stderr_level=logging.WARNING,
)


class Hook:
    def __init__(self, repo: str):
        self.repo = repo
        self.paths = Paths(repo)
        self.paths.repo_state.mkdir(parents=True, exist_ok=True)
        self.borg = Borg(repo)
        self.pubsub = PubSub(self.paths, start=False)

    def check_repo(self, user: str | None, *, release_on_restart=False) -> int:
        if not release_on_restart:
            logger.info(f'Checking repo {self.repo} for user {user}...')

            lock_user = self.paths.lock_user.read_text()
            if user != lock_user:
                msg = f'User from pk is {user} but lock was taken by {lock_user}'
                raise AssertionError(msg)

            prev_arcs = without_user_temp(self.paths.lock_prev_arcs.read_text(), user)

        else:
            logger.info(f'Checking repo {self.repo} for release_on_restart...')

            try:
                user = self.paths.lock_user.read_text()
                prev_arcs = without_user_temp(self.paths.lock_prev_arcs.read_text(), user)
            except FileNotFoundError as e:
                # Lock was incompletely written, so no "borg serve" should have taken place.
                # Anyway, can't check without any of those files.
                logger.info('...but lock is incomplete. Skipping.', exc_info=e)
                return 0

            # Note: `borg break-lock` is not used, because it's possible for borg_daily to be running.

        cur_arcs = without_user_temp(self.borg.dump_arcs(), user)

        # Check that previous archives are intact, except for f'{user}(temp)-*'
        if not cur_arcs.startswith(prev_arcs):
            msg = 'Previous archives were modified!'
            raise BadRepoError(msg)

        # Check that new archives begin with user prefix (excluding f'{user}(temp)-*')
        new_arcs = cur_arcs.replace(prev_arcs, '', 1)
        new_count = 0
        while new_arcs:
            _arc_id, _sep, new_arcs = new_arcs.partition('\x00')
            arc_name, _sep, new_arcs = new_arcs.partition('\x00')
            if not arc_name.startswith(user + '-'):
                msg = f"Created [{arc_name}] that doesn't start with [{user}-]!"
                raise BadRepoError(msg)
            new_count += 1

        logger.info('...OK')
        return new_count

    def acquire_lock(self, user: str):
        logger.info(f'{user} is acquiring lock for {self.repo}...')

        if not self.paths.repo_enabled.exists():
            logger.warning('Repo access is disabled')
            sys.exit(RC.access_denied)

        waiting_for = get_waiting_for(self.repo)
        if waiting_for and waiting_for != user:
            logger.warning(f'Repo is waiting_for {waiting_for} instead')
            sys.exit(RC.access_denied)

        if not self.borg.is_repo_unlocked():
            logger.warning('Underlying repo is locked')
            sys.exit(RC.access_denied)

        try:
            mkdir_lock(self.paths)
        except FileExistsError:
            logger.warning(f'Repo is locked by user {self.paths.lock_user.read_text()}')
            # Note: there's a small window for lock_user read to fail. Ignore.
            sys.exit(RC.access_denied)

        self.paths.lock_user.write_text(user)
        self.paths.lock_prev_arcs.write_text(self.borg.dump_arcs())
        self.pubsub.publish(f'lock_acquired {user}')
        logger.info('...OK')

    def release_lock(self, user: str):
        try:
            new_arcs_count = self.check_repo(user)
            shutil.rmtree(self.paths.lock)
            self.pubsub.publish(f'lock_released {user} {new_arcs_count}')
        except Exception:
            logger.exception('Error releasing lock')
            sys.exit(RC.generic_error)

    def release_lock_on_restart(self):
        is_enabled = self.paths.repo_enabled.exists()
        if not is_enabled:
            return
        is_locked = self.paths.lock.is_dir()
        if not is_locked:
            return
        try:
            self.check_repo(None, release_on_restart=True)
            shutil.rmtree(self.paths.lock)
        except Exception:
            logger.exception(f'Error releasing lock on restart for repo {self.repo}')

    def release_locks_on_restart():
        for repo in get_config_repos():
            hook = Hook(repo)
            hook.release_lock_on_restart()


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
        Hook.release_locks_on_restart()
        return
    if hook_src != 'pam':
        logger.error(f'Invalid hook_src: {hook_src}')
        sys.exit(RC.invalid_usage)

    ssh_auth_info = os.environ.get('SSH_AUTH_INFO_0')
    try:
        pk = re.fullmatch(r'publickey ([a-z0-9-]+ [a-zA-Z0-9+/=]+)\n?', ssh_auth_info)[1]
        repo, user = get_config_from_pk(pk)
    except Exception:
        logger.exception(f'Failed to get user from pubkey. $SSH_AUTH_INFO_0: {ssh_auth_info!r}')
        sys.exit(RC.invalid_usage)

    hook = Hook(repo)

    pam_type = os.environ.get('PAM_TYPE')
    match pam_type:
        case 'open_session':
            hook.acquire_lock(user)
        case 'close_session':
            hook.release_lock(user)
        case _:
            logger.error(f'Bad $PAM_TYPE: [{pam_type}]')
            sys.exit(RC.invalid_usage)


if __name__ == '__main__':
    # When an uncaught exception is raised, it's sent to stderr,
    # but borg prints just the first characters of it so it's useless.
    # Ensure they are logged to systemd journal:
    def excepthook(exc_type, exc_value, exc_tb):
        logger.error('', exc_info=(exc_type, exc_value, exc_tb))
    sys.excepthook = excepthook

    main(sys.argv)
