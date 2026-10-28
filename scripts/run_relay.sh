#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ -n "${PICO_ENV_FILE:-}" ]; then
    exec python3 -m relay.app --env-file "$PICO_ENV_FILE" "$@"
fi
exec python3 -m relay.app "$@"
