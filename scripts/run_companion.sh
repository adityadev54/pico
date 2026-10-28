#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
PICO_PYTHON="${PICO_PYTHON:-python3}"
case "$(uname -s)" in
  Darwin)
    if [ ! -x agents/native/macos_context ] || [ agents/native/macos_context.swift -nt agents/native/macos_context ]; then
      swiftc -target "$(uname -m)-apple-macos13.0" agents/native/macos_context.swift -o agents/native/macos_context
    fi
    "$PICO_PYTHON" scripts/make_macos_app.py
    exec "$PICO_PYTHON" agents/macos.py "$@" ;;
  *) echo 'On Windows, run: python agents/windows.py'; exit 1 ;;
esac
