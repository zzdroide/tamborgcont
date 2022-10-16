import yaml


def get_config():
    with open('./config.yml', 'r') as f:
        return yaml.safe_load(f)


def does_user_exist(user):
    users = get_config()['users']
    gen = (u for u in users if u['user'] == user)
    return bool(next(gen, None))
