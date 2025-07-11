#!/bin/bash
set -euxo pipefail

# Test None cipher on vagrant user:
hpnssh \
    -oBatchMode=yes -oNoneEnabled=yes -oNoneSwitch=yes \
    localhost \
    true \
  1>/tmp/hpn_ssh_none.out \
  2>/tmp/hpn_ssh_none.err
[[ $(cat /tmp/hpn_ssh_none.out) == "" ]]
[[ $(cat /tmp/hpn_ssh_none.err) == "WARNING: ENABLED NONE CIPHER!!!" ]]

sudo -u borg mkdir -p /home/borg/tamborgcont/

# Test hook deny/allow on borg user:
sudo -u borg ln -sf /bin/false /home/borg/tamborgcont/hook.sh
(! hpnssh -oBatchMode=yes borg@localhost true)
sudo -u borg ln -sf /bin/true /home/borg/tamborgcont/hook.sh
hpnssh -oBatchMode=yes borg@localhost true

# Test hook deny on plain ssh for borg user:
out=$(ssh -oBatchMode=yes borg@localhost true || true)
[[ $out == "Please use hpnssh." ]]
