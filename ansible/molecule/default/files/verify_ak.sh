#!/bin/bash
set -euxo pipefail
cd ~/.ssh

readonly AK='command="/home/borg/tamborgcont/hook.sh ssh_command TAM_2009 && borg serve --append-only --restrict-to-repository /home/borg/TAM",restrict ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEEzh7eIUFgJy/CLTHN+B0wlq3QK0aTZz/0FVfKCtdA0 TAM_2009'

diff authorized_keys.old <(echo authk1)
diff authorized_keys-molecule <(echo "$AK")
