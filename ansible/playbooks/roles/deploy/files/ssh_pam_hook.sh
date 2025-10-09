#!/bin/bash
set -euo pipefail


# Require logins to be approved by pressing the power button.
# Whitelist for users "borg" and "vagrant".
if [[ "$PAM_TYPE" == "open_session" && "$PAM_USER" != "borg" && "$PAM_USER" != "vagrant" ]]; then
  #   echo "Press power button to approve login..."
  # The echo in the line above is useless. Stdout is only sent to client after this script exits.
  # Alternative:
  beep -f1397 -l80

  if acpi_listen -t30 -c1 | grep -q "^button/power "; then
    beep -f2093 -l80
  else
    beep -f175 -l80
    echo "Did not press power button to approve login."
    exit 1
  fi
fi


# Handle borg lock and verify repo
if [[ "$PAM_USER" == "borg" ]]; then
  if [[ "$PAM_TYPE" == "open_session" && "$PAM_SERVICE" != "hpnsshd" ]]; then
    # Prevent accidental connections without None cipher
    echo "Please use hpnssh."
    exit 1
  elif [[ "$PAM_TYPE" == "open_session" || "$PAM_TYPE" == "close_session" ]]; then
    sudo --login -u borg \
      PAM_TYPE="$PAM_TYPE" \
      SSH_AUTH_INFO_0="$SSH_AUTH_INFO_0" \
      /home/borg/tamborgcont/hook.sh pam
  fi
fi
