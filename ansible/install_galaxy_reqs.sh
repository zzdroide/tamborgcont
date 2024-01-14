#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
source vars.sh

poetry -q run ansible-galaxy collection install -r requirements.yml
poetry -q run ansible-galaxy role install -r requirements.yml
