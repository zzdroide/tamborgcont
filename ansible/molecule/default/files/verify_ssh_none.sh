#!/bin/bash
set -euxo pipefail

(umask 077; ssh-keyscan -p 2222 localhost >> ~/.ssh/known_hosts)

hpnssh \
    -oBatchMode=yes -oNoneEnabled=yes -oNoneSwitch=yes \
    localhost \
    true \
  1>/tmp/hpn_ssh_none.out \
  2>/tmp/hpn_ssh_none.err

[[ $(cat /tmp/hpn_ssh_none.out) == "" ]]
[[ $(cat /tmp/hpn_ssh_none.err) == "WARNING: ENABLED NONE CIPHER!!!" ]]
