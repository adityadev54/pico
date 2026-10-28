#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
exec flutter build web --base-href /phone/ --dart-define-from-file=config/pico.public.json "$@"
