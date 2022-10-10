# shellcheck shell=bash

# Prevent littering and mixing ~/.ansible/collections/
export ANSIBLE_COLLECTIONS_PATH="$PWD/.collections/"

# https://github.com/ansible/ansible/issues/27078#issuecomment-364560173
export ANSIBLE_STDOUT_CALLBACK=debug
