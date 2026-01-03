from pathlib import Path


class RC:
    generic_error = 1
    invalid_usage = 2
    access_denied = 3


class Paths:
    base_state = Path('state')

    def __init__(self, repo: str):
        self.repo_state = self.base_state / repo

        self.repo_enabled = self.repo_state / 'enabled'

        self.lock = self.repo_state / 'lock'
        self.lock_prev_arcs = self.lock / 'prev_arcs.bin'
        self.lock_user = self.lock / 'user.txt'

        self.pubsub = self.repo_state / 'pubsub.fifo'
