#!/bin/bash
set -euxo pipefail

ssh-keygen -f ~/.ssh/id_ed25519 -t ed25519 -N ""
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
# No ssh-keyscan here, as the one from to-be-installed hpnsshd is needed.
