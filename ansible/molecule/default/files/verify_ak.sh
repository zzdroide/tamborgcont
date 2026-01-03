#!/bin/bash
set -euxo pipefail
cd ~/.ssh

AK="$(\
echo 'command="zsh -l -c '\''borg serve --append-only --restrict-to-repository /home/borg/TAM'\''",restrict ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEEzh7eIUFgJy/CLTHN+B0wlq3QK0aTZz/0FVfKCtdA0 TAM_2009'; \
echo 'command="zsh -l -c '\''borg serve --append-only --restrict-to-repository /home/borg/AMGS'\''",restrict ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMji6955pM7IL2rcaCYYJOxJcdMXY3fuXmB3itcOMTCw AMGS'; \
echo 'command="zsh -l -c '\''borg serve --append-only --restrict-to-repository /home/borg/TAM'\''",restrict ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICJwCmpqfCPFg4vCj95Qx656XQwyaLEA+J1McvZR5gGw old_laptop' \
)"

diff authorized_keys.old <(echo authk1)
diff authorized_keys-molecule <(echo "$AK")
