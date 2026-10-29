# Pico runbook

Operations for the 1.0.0 production release: relay on Fly (`pico-companion`,
region `ewr`), Supabase project from `supabase/README.md`, artifacts served
from the relay's `/download` route.

## Release build order

Order matters: the Fly image bundles `downloads/` and `build/web`
(`relay/Dockerfile`), so build everything before deploying.

```sh
# 1. Backend first (review diff on an existing project)
#    Apply supabase/migrations/20261029_pico_core.sql, then:
python3 scripts/check_connection.py --env-file /path/to/server.env

# 2. Version (single source; desktop installers read it)
#    pubspec.yaml -> version: 1.0.0+N, then:
flutter pub get && flutter analyze && flutter test

# 3. Desktop (on macOS; Windows needs dotnet + signtool on PATH)
PICO_RELAY_URL=https://pico-companion.fly.dev \
PICO_MAC_IDENTITY="Developer ID Application: ..." \
PICO_NOTARY_PROFILE=pico \
  python3 scripts/build_macos_installer.py
PICO_RELAY_URL=https://pico-companion.fly.dev \
PICO_WIN_CERT=/path/to/cert.pfx PICO_WIN_CERT_PASSWORD=... \
  python3 scripts/build_windows_installer.py   # on Windows

# 4. Phone
sh scripts/build_phone.sh          # PWA into build/web
sh scripts/build_android.sh        # release APK, needs android/key.properties

# 5. Package + checksums, then full gates (docs/qa-matrix.md)
python3 scripts/package_companion.py
sha256sum -c downloads/SHA256SUMS   # or: shasum -a 256 -c

# 6. Deploy relay, then verify live
fly deploy
curl -s https://pico-companion.fly.dev/health
python3 scripts/check_connection.py --env-file /path/to/server.env \
  --relay-url https://pico-companion.fly.dev --report /tmp/pico-prod.json

# 7. Tag the release (artifacts + image + migration move together)
git tag -a v1.0.0 -m "Pico 1.0.0" && git push origin v1.0.0
```

## One-time setup

- **Fly secrets** (never in `fly.toml` or git):
  `fly secrets set SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=...`
- **Android keystore** (stays on the release machine, gitignored):
  generate with `keytool -genkeypair`, then create `android/key.properties`:
  `storeFile`, `storePassword`, `keyAlias`, `keyPassword` (see
  `android/app/build.gradle.kts`). Back the keystore up; losing it
  orphans Play updates.
- **Apple notarization**: create a `notarytool` keychain profile on the
  release Mac and export its name as `PICO_NOTARY_PROFILE`.
- **Docker digest**: `relay/Dockerfile` pins `python:3.12-slim` by tag.
  At release time, resolve and record the image digest in the release
  notes so rebuilds are bit-identical.

## Local relay (no Fly deploy)

Runs the current tree's relay on your own machine against the same
Supabase project. Same devices/tokens (no data migration), but the
phone and helper must both point at it, and the computer must be
re-paired once (claim refuses while the old device row exists).

```sh
# 0. One-time: service key where only you can read it (never in chat
#    or git). Supabase dashboard -> project -> Settings -> API ->
#    service_role secret:
cat > ~/.pico/server.env <<'EOF'
SUPABASE_URL=https://YOUR-PROJECT.supabase.co
SUPABASE_SERVICE_ROLE_KEY=paste-service-role-key-here
EOF
chmod 600 ~/.pico/server.env

# 1. Start the relay (keep this terminal running; stdlib only):
cd /Users/santoshadabala/PICO/pico
python3 -m relay.app --env-file ~/.pico/server.env --port 8765

# 2. Sanity (second terminal):
curl -s http://127.0.0.1:8765/health
# expect: "supabase_connected": true, "state_writable": true

# 3. Phone: restart flutter run pointed at it:
flutter run -d chrome --dart-define-from-file=config/pico.public.json \
  --dart-define=RELAY_URL=http://localhost:8765

# 4. Helper: stop it, drop the cloud pairing, start it the same way
#    as before (a fresh helper pairs against http://127.0.0.1:8765
#    by default), then: phone Devices -> disconnect old computer ->
#    get code -> enter it on the computer.
rm ~/.pico/connection.json
```

## Day-to-day

- Health: `GET /health` returns per-check `supabase_connected` and
  `state_writable`; Fly restarts the machine when it goes 503.
- Logs: `fly logs` shows `METHOD /path status ms` access lines plus
  tracebacks for 500s. Paths only — queries, codes, tokens, and user
  text never appear. There is deliberately no per-user request tracing.
- Pairing abuse: lockout is automatic (5 wrong codes → 10 minutes).
  No manual intervention; do not delete lockout rows to “help” — that
  disables the protection.

## Back up before risky changes

- Supabase: take a project backup/snapshot from the dashboard before
  applying migrations.
- Relay state: snapshot the `pico_state` Fly volume before deploys that
  touch `relay/state.py`. The volume holds lockouts and 24h delivery
  receipts only — losing it degrades to re-delivery, never data loss.

## Rollback

- Relay: `fly deploy` again from the previous release tag. The image is
  self-contained; no data migration to reverse (migrations here are
  additive-only by convention — keep it that way).
- Desktop/mobile: previous `downloads/` artifacts stay valid against the
  rolled-back relay; re-publish them on the setup page if already replaced.
- If a bad pairing-code or token format ever ships: clients show “reconnect”
  and users re-pair with a fresh code; no server-side purge needed.

## Support triage

| Symptom | Cause | Fix |
| ------- | ----- | --- |
| “Session expired / sign in again” | Supabase JWT expired | Sign in again on the phone |
| “This computer was unpaired” (401) | Revoked or unknown device token | Re-pair with a fresh code |
| “Too many incorrect codes” (429) | Lockout | Wait 10 minutes |
| “Tasks are not available” (503) | `tasks` table missing | Apply `supabase/migrations/` |
| “Update pico on your computer” | Old `helper_version` | Install the latest desktop build |
| File “couldn’t finish · candidate_changed” | File changed between approval and transfer | Search again, approve, resend |
| Push 413 on transfer | File over 1 MB | Demo limit; split or shrink the file |
