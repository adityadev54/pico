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

## Current status

Pairing, chat history and companion sync are implemented. Head Start needs a configured model provider.

Mac and Windows installers are development builds without publisher verification. Physical Android/iPhone and Windows testing remain.
