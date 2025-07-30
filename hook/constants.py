from pathlib import Path


class RC:
    generic_error = 1
    invalid_usage = 2
    access_denied = 3


class Paths:
    base_state = Path('state')

    @classmethod
    def set_repo_name(cls, repo: str):
        cls.repo_state = cls.base_state / repo

        cls.repo_enabled = cls.repo_state / 'enabled'

        cls.lock = cls.repo_state / 'lock'
        cls.lock_prev_arcs = cls.lock / 'prev_arcs.bin'
        cls.lock_user = cls.lock / 'user.txt'
