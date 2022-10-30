# Server control for tamborg repo

## Local setup
```sh
pipx install poetry~=1.2.0
poetry install
./install_ansible_collections.sh

cp config.example.yml config.yml
nano config.yml
```

### Running tests

Requires VirtualBox installed.

```sh
poetry shell

pytest

cd ansible
molecule test
```

## Server setup

- Install Debian, include OpenSSH server. Set a strong password because SSH PasswordAuthentication defaults to yes.
- Set static IP (preferably at the router, against MAC)
- `ssh-copy-id`, set `PasswordAuthentication no` in /etc/ssh/sshd_config, `sudo systemctl restart ssh`
