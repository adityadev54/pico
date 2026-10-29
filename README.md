# Pico

Hold a thought. Pick it up on your computer.

[Get Pico](https://pico-companion.fly.dev/setup)

| Device | Install |
| --- | --- |
| Mac | `.dmg` · Apple silicon, macOS 13+ |
| Windows | `.exe` · x64 |
| Android | `.apk` · Android 7+ |
| iPhone | Safari → Share → Add to Home Screen |

Sign up on your phone, get a connection code, and enter it on your computer.

## Development

Flutter · Supabase (Auth & Devices) · native desktop helpers.

`agents/` contains desktop helpers, not the AI agent backend. The team’s backend lives in `server/agent/`.

```sh
flutter pub get
sh scripts/run_phone.sh
flutter analyze
flutter test
```

For a local relay, set server-only `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`, then run `sh scripts/run_relay.sh`. An environment file can be supplied with `PICO_ENV_FILE`. Keep secrets out of apps and downloads.

## Production status (1.0.0)

Pairing, Places, companion sync, and the document task queue (search →
exact-file approval → verified transfer) are implemented with 43 Python
tests and a Flutter suite. Start here for a release:

- Backend: `supabase/README.md` + `supabase/migrations/`
- Operations: `docs/runbook.md` (build order, secrets, rollback)
- Release gates: `docs/qa-matrix.md` (automated + hardware checklist)
- Security record: `docs/security.md` (enforcement, gaps)

Before tagging: run `flutter pub get` (adds `crypto`), the QA gates, and
`check_connection.py` against production. Head Start stays disabled until
a model provider is configured. Account deletion is the one documented
functional gap (see `docs/security.md`).
