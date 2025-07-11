from pathlib import Path


class RC:
    generic_error = 1
    invalid_usage = 2
    access_denied = 3


class Paths:
    state = Path('state')

    repo_is_ok = state / 'repo_is_ok'

    lock = state / 'lock'
    lock_prev_arcs = lock / 'prev_arcs.bin'
    lock_user = lock / 'user.txt'
    lock_ip = lock / 'ip.txt'
