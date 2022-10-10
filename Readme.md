# Server control for tamborg repo

## Setup
```sh
pipx install poetry~=1.2.0
poetry install
./install_ansible_collections.sh

cp config.example.yml config.yml
nano config.yml
```

## Running tests

Requires VirtualBox installed.

```sh
poetry shell

pytest

cd ansible
molecule test
```
