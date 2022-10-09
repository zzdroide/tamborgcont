#!/bin/sh
cd "$(dirname "$0")" || exit 1
poetry -q run python -m src.hook "$@"
