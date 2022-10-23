# shellcheck shell=bash

# Prevent littering and mixing ~/.ansible/collections/
export ANSIBLE_COLLECTIONS_PATH="$PWD/.collections/"

# https://github.com/ansible/ansible/issues/27078#issuecomment-364560173
# But unfortunately "debug" is printing empty STDOUT at failed ansible.builtin.script task,
# so use yaml instead:
export ANSIBLE_STDOUT_CALLBACK=yaml
