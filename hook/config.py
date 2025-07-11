from pathlib import Path

import yaml


def get_config():
    with Path('./config.yml').open(encoding='utf-8') as f:
        return yaml.safe_load(f)


def does_user_exist(user):
    users = get_config()['users']
    gen = (u for u in users if u['user'] == user)
    return bool(next(gen, None))
