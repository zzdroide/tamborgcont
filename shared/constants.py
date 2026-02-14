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

        self.env = Path('/home/borg/env') / repo
        self.repo = Path('/home/borg') / repo
        self.repo_data = self.repo / 'data'
        self.repo_snap_current = self.repo / 'data.snap.current'
        self.repo_snap_checked = self.repo / 'data.snap.checked'
