from pathlib import Path

import yaml


def get_config():
    with Path('./config.yml').open(encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_from_pk(pk: str):
    users = get_config()['users']
    user = next((u for u in users if u['pubkey'] == pk), None)
    if user:
        return user['repo'], user['user']
    msg = f'No user with pubkey {pk}'
    raise ValueError(msg)
