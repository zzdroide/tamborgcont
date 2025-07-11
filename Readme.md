# Server control for tamborg repo

## Local setup
```sh
sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt update && sudo apt install python3.13
pipx install poetry
poetry env use python3.13
poetry sync

cp config.example.yml config.yml
nano config.yml
```

### Running tests

Requires [VirtualBox](https://www.virtualbox.org/wiki/Linux_Downloads#Debian-basedLinuxdistributions) and [Vagrant](https://developer.hashicorp.com/vagrant/install?product_intent=vagrant#Linux) installed.

```sh
eval $(poetry env activate)   # poetry shell

pytest

cd ansible
molecule test
```

## Server setup

- Install Debian bookworm
  - with a strong password because SSH PasswordAuthentication defaults to yes
  - with "SSH server" and "standard system utilities" software
- Set static IP (preferably at the router, against MAC)
- `ssh-copy-id`

And from local, deploy to server with:
```sh
cd ansible
ANSIBLE_PIPELINING=True ANSIBLE_CALLBACK_RESULT_FORMAT=yaml poetry run ansible-playbook -i t@192.168.0.63, -l t@192.168.0.63 --ask-become-pass playbooks/deploy.yml
```

Some manual interactive setup after it finishes:
```sh
# In server:
sudo su - borg

# Either create a new repo:
borg init --encryption=repokey
borg key export  # Send the key to an email to self

# Or restore it to $HOME/TAM.

cd ~
git clone git@github.com:zzdroide/tamborgcont.git
cd tamborgcont
poetry install

nano ~/.zprofile  # Add "export BORG_PASSPHRASE=<pass>"

cp config.example.yml config.yml
nano config.yml
./update_authorized_keys.sh

touch state/repo_is_ok
```
