#!/usr/bin/env bash
# Run a command on the production backup server through an existing SSH ControlMaster.
# The agent cannot create that mux; a human must run this script with --setup.
set -euo pipefail

CONTROL_PATH="${HOME}/.ssh/cm-borg2"
HOST="$(yq .server_ip /etc/borgmatic/config/constants.yaml)"
SETUP=0
SETUP_USER=

usage() {
  echo "Usage: prod_ssh.sh --setup [--user USER]" >&2
  echo "       prod_ssh.sh [--] command [args...]" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --setup)
      SETUP=1
      shift
      ;;
    --user)
      SETUP_USER="${2:-}"
      shift 2
      ;;
    --user=*)
      SETUP_USER="${1#--user=}"
      shift
      ;;
    --help|-h)
      usage
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage
      ;;
    *)
      break
      ;;
  esac
done

if [[ -n "$SETUP_USER" && "$SETUP" -eq 0 ]]; then
  echo "--user is only valid with --setup" >&2
  usage
fi

if [[ "$SETUP" -eq 1 ]]; then
  echo "ControlMaster in this terminal (no remote shell). Ctrl-C closes it." >&2
  if [[ -n "$SETUP_USER" ]]; then
    exec ssh -M -N -S "$CONTROL_PATH" -l "$SETUP_USER" "$HOST"
  fi
  exec ssh -M -N -S "$CONTROL_PATH" "$HOST"
fi

if ! ssh -S "$CONTROL_PATH" -O check "$HOST" >/dev/null 2>&1; then
  echo "ControlMaster is not running. A human must complete interactive SSH login with:" >&2
  echo "  ${BASH_SOURCE[0]} --setup [--user USER]" >&2
  exit 2
fi

if [[ $# -eq 0 ]]; then
  usage
fi

# Join as one remote shell command. Quote globs locally (`ls "env/*"`) so they
# are not expanded here; the remote zsh expands them as borg.
#
# The command travels on stdin because both ssh's remote shell and `sudo -i`
# re-parse anything passed as argv, which ate quotes and expanded `$var` and `;`
# before the target zsh saw them. `zsh -l -s` reads it verbatim instead.
printf '%s\n' "$*" |
  ssh -S "$CONTROL_PATH" -o ControlMaster=no -o BatchMode=yes "$HOST" \
    'sudo -i -u borg zsh -l --shinstdin'
