#!/bin/bash
set -euxo pipefail
cd ~/.ssh

echo authk1 >authorized_keys-molecule
touch yes-this-is-borg-repo-server-user
