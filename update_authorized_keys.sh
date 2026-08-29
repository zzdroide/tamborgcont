#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/ansible"

# This runs in server instead of development machine, so hardcoded dependency instead of requirements.yml:
poetry -q run ansible-galaxy collection install ansible.posix

poetry -q run \
  ansible-playbook \
  --inventory localhost, --limit localhost \
  playbooks/update_ak.yml
