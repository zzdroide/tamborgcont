#!/bin/bash
set -euo pipefail

umask 077

mkdir -p ~/.ssh
cd ~/.ssh

echo authk1 > ~/.ssh/authorized_keys-molecule

touch yes-this-is-borg-repo-server-user
