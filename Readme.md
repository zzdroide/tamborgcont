# Server control for tamborg repos

The backup server itself has no backup, so if a restore is needed:
- Install OS again
- Deploy with this repo
- Restore repository from remote backup
- Previous ssh private keys will be lost, new ones will have to be configured.

## Local setup
```sh
sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt update && sudo apt install python3.13
pipx install poetry
poetry env use python3.13
poetry sync
```

### Running tests

Requires [VirtualBox](https://www.virtualbox.org/wiki/Linux_Downloads#Debian-basedLinuxdistributions) and [Vagrant](https://developer.hashicorp.com/vagrant/install?product_intent=vagrant#Linux) installed.

```sh
eval $(poetry env activate)   # poetry shell

pytest

cd ansible
molecule test
```

Note: autosuspend is enabled in Vagrant too. If `molecule login` hangs, reset the instance in VirtualBox.

## Server setup

- Install Debian trixie
  - with ext4 `largefile`
  - with a strong password because SSH PasswordAuthentication defaults to yes
  - with "SSH server" and "standard system utilities" software
- Set static IP (preferably at the router, against MAC)
- `ssh-copy-id`

And from local, deploy to server with:
```sh
cd ansible
ANSIBLE_PIPELINING=True ANSIBLE_CALLBACK_RESULT_FORMAT=yaml poetry run ansible-playbook -i t@10.0.0.20, -l t@10.0.0.20 --ask-become-pass playbooks/deploy.yml
```

Some manual interactive setup after it finishes:
```sh
# In server:

# Run ext4_reserve.sh for non-root partitions

sudo su - borg

# Either create new repos:
borg init --encryption=repokey $HOME/TAM
borg key export $HOME/TAM   # Send the key in an email to self

# Or restore them to $HOME.

# The next line requires adding ~/.ssh/id_ed25519.pub in https://github.com/zzdroide/tamborgcont/settings/keys
git clone git@github.com:zzdroide/tamborgcont.git

cd tamborgcont
poetry sync --without=dev

take ~/env
cp ~/tamborgcont/env.example TAM
nano TAM

popd
cp config.test.yml config.yml
nano config.yml
./update_authorized_keys.sh

md state/TAM
touch state/TAM/enabled
```

To edit users later:
```sh
nano config.yml
./update_authorized_keys.sh
```

### Watching logs
```sh
sudo journalctl -ft sshd -t borg_ssh_hook -t borg_daily
```
