#!/bin/bash
set -euo pipefail

if [[ "$PAM_USER" == "borg" ]]; then
  if [[ "$PAM_TYPE" == "open_session" && "$PAM_SERVICE" != "hpnsshd" ]]; then
    # Prevent accidental connections without None cipher
    echo "Please use hpnssh."
    exit 1
  fi

  if [[ "$PAM_TYPE" == "open_session" || "$PAM_TYPE" == "close_session" ]]; then
    sudo --login -u borg \
      PAM_TYPE="$PAM_TYPE" \
      PAM_RHOST="$PAM_RHOST" \
      /home/borg/tamborgcont/hook.sh pam
  fi
fi
