from pathlib import Path

import yaml


def get_config():
    with Path('./config.yml').open(encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_config_repos():
    users = get_config()['users']
    return {u['repo'] for u in users}


def get_config_from_pk(pk: str):
    users = get_config()['users']
    user = next((u for u in users if u['pubkey'] == pk), None)
    if user:
        return user['repo'], user['user']
    msg = f'No user with pubkey {pk}'
    raise ValueError(msg)


def get_config_weekly_healthcheck():
    return get_config()['weekly_healthcheck']


def get_config_smarthealthc():
    return get_config()['smarthealthc']


def get_config_force_weekly_until():
    return get_config().get('force_weekly_until')
