#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/ansible"

export ANSIBLE_CALLBACK_RESULT_FORMAT=yaml  # Readable and correct

poetry -q run \
  ansible-playbook \
  --inventory localhost, --limit localhost \
  playbooks/update_ak.yml
