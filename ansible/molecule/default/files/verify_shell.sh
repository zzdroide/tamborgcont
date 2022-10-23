#!/bin/bash
set -euxo pipefail
readonly user=$1

user_shell=$(getent passwd "$user" | cut -d: -f7)
[[ "$user_shell" == /bin/zsh ]]

prompt=$(sudo -u "$user" zsh -i -c 'cd ~ && print -P $PS1')
expected="\x1B[01;37m${user}\x1B[00m@\x1B[01;32minstance\x1B[00m:\x1B[01;34m~\x1B[00m \x1B[01;32m%\x1B[00m "
[[ $(echo -e "$prompt") == $(echo -e "$expected") ]]
