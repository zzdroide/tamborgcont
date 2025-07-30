#!/bin/bash
set -euxo pipefail

# Key for vagrant user:
if ! [ -s ~/.ssh/id_ed25519 ]; then
  ssh-keygen -f ~/.ssh/id_ed25519 -t ed25519 -N ""
fi

# AK for vagrant user:
cat ~/.ssh/id_ed25519.pub >>~/.ssh/authorized_keys

# AK for borg user:
# shellcheck disable=SC2024
<~/.ssh/id_ed25519.pub \
  sudo -u borg \
    tee -a /home/borg/.ssh/authorized_keys \
>/dev/null

# known_hosts for vagrant user:
ssh-keyscan -p 1701 localhost >>~/.ssh/known_hosts
ssh-keyscan         localhost >>~/.ssh/known_hosts
