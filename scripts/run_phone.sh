#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
exec flutter run --dart-define-from-file=config/pico.public.json "$@"
