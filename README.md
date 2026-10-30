# Pico

Hold a thought. Pick it up on your computer.

[Get Pico](https://pico-companion.fly.dev/setup)

| Device | Install |
| --- | --- |
| Mac | `.dmg` · Apple silicon, macOS 13+ |
| Windows | `.exe` · x64 |
| Android | `.apk` · Android 7+ |
| iPhone | Safari → Share → Add to Home Screen |

Sign up on your phone, get a code, and enter it on your computer.
Choose allowed apps in the companion’s **Open apps** menu. Choose read-only folders or a write workspace in permissions. Snapshot exclusions are separate.

## Development

Flutter · Supabase · native desktop helpers.

```sh
flutter pub get
sh scripts/run_phone.sh
flutter analyze
flutter test
```

`agents/` contains desktop helpers. `server/agent/` contains the planner.
Keep secrets server-only and outside version control.

## Tasks

Search and read approved folders, send a selected file to your phone, save uploads, create or revise notes, and copy unique photos. File changes require a write workspace and phone approval. Commands also require computer approval. Shell commands are disabled.

Muse is account-restricted and opt-in. The connection dot checks access without inference. **Ask Pico:** uses one bounded planning call; summaries run only when requested and confirmed. No automatic summaries or model retries.

AI attempts reserve $0.10 against a shared $1/day and $5 total test allowance. Actual provider billing is separate. Keys stay server-only.

Installers are development builds. Physical Windows UI testing remains. Rebuild the phone and desktop packages together when testing changes from source.
