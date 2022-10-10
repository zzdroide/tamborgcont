#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/ansible"
# shellcheck source=ansible/vars.sh
source vars.sh

poetry -q run \
  ansible-playbook \
  --inventory localhost, --limit localhost \
  playbooks/update_ak.yml
