#!/bin/bash
set -euo pipefail
cd ~/.ssh
umask 077

echo authk1 > authorized_keys-molecule
touch yes-this-is-borg-repo-server-user
