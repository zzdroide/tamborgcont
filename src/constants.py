class RC:
    generic_error = 1
    invalid_usage = 2
    access_denied = 3


class Paths:
    state = 'state'

    repo_is_ok = f'{state}/repo_is_ok'

    lock = f'{state}/lock'
    lock_prev_arcs = f'{lock}/prev_arcs.bin'
    lock_user = f'{lock}/user.txt'
    lock_ip = f'{lock}/ip.txt'
