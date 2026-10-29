# Security and privacy

Audited 2026-10-29 for the 1.0.0 production pass. No secrets were found in
the repo (see verification below); the gaps at the bottom are accepted and
owned, not silent.

## What is enforced where

| Concern | Enforcement |
| ------- | ----------- |
| Owner identity | Derived from auth on every call (`relay/service.py` `user()`/`device()`); device IDs and request bodies never authorize |
| Pairing codes | Single-use, 5-minute expiry, sha256-hashed; 5 wrong tries per address locks out for 10 minutes (`relay/state.py`) |
| Device tokens | `pico_`-prefixed, hashed at rest, checked against `revoked_at` on every call |
| Task approvals | Phone binds exact `candidate_id` + `approval_id`; helper rechecks size/digest at transfer; phone receipt must match both (`server/verification/checks.py`) |
| Cancellation | Terminal states never leave; late results are acknowledged but ignored |
| File transfer | ≤1 MB, base64 over HTTPS, digest-verified before storage and again at phone receipt |
| Native search | Folder-grant scoped; explicit-but-unresolvable grants fail closed (`agents/native_search.py`) |
| Transport | Fly `force_https`; desktop client requires HTTPS except localhost or explicit `PICO_ALLOW_LAN=1`; agent server binds 127.0.0.1 only |
| Database access | Phone JWT: own `tasks` (read), own `handoffs` (read/insert), own `pico-transfers/` paths; everything else is service-key-only (`supabase/migrations/`) |
| Logs | Relay access lines carry method/path/status/ms only — no query, codes, tokens, or user text (`relay/app.py` `access_line`); agent server logs nothing per request |

## Secrets handling

- Service key and Meta key live in `server.env`, passed via `--env-file` /
  `PICO_ENV_FILE`, and in Fly secrets. Never in apps, downloads, logs, or git
  (`.gitignore` covers `**/.env`, keystores, certs).
- `config/pico.public.json` holds the publishable key only — safe to ship.
- Release signing: `PICO_MAC_IDENTITY` + `PICO_NOTARY_PROFILE`,
  `PICO_WIN_CERT` + `PICO_WIN_CERT_PASSWORD`, `android/key.properties`. All
  owner-held; builds warn loudly when absent.
- `Pico-source.zip` excludes `.env`, keystores, certs, and build output
  (`scripts/package_companion.py`); re-audit with
  `unzip -l downloads/Pico-source.zip` before each release.

## Permissions and retention

- Android declares `RECORD_AUDIO`; iOS declares mic + speech recognition with
  user-visible strings; macOS snapshots require Screen Recording and are
  skipped without it; private-browsing windows are never snapshotted.
- Desktop snapshots purge after `retention_days` (default 7); relay delivery
  receipts expire in 24h; pairing attempts reset on success.
- Supabase rows (`tasks`, `handoffs`, `devices`) persist until the user
  clears history or unpairs. There is no automatic server-side expiry.

## Dev-only switches (never set in production)

- `PICO_ALLOW_LOCAL_AUTH=1` (agent server trusts any bearer token as an owner)
- `PICO_ALLOW_LAN=1` (desktop client allows plain-HTTP LAN relays)
- `PICO_SEARCH_ROOTS` (extra search folders for the desktop helper)

## Accepted gaps

1. **No self-serve account/data deletion.** Users can clear history and unpair
   per device, but Supabase rows and stored transfers have no user-facing
   delete-everything path. Recommended follow-up: relay `POST /account/delete`
   (service key) + a Settings entry, with a checklist row.
2. **No general rate limiting.** Pairing has lockout; authenticated endpoints
   rely on per-account abuse containment. Recommended follow-up if abuse
   appears: per-token mail/task quotas in `RelayState`.
3. **Helper version is not reported.** The phone tolerates missing
   `helper_version`; outdated-helper warnings only fire when the column is
   set. Recommended follow-up: companion reports its version on poll.
4. **Docker image tag floats.** `relay/Dockerfile` pins `python:3.12-slim`
   by tag, not digest (no network to resolve a digest at audit time).
   Pin a digest at release: record it in the release notes.

## Verification

```sh
grep -rniE "sb_secret_|sk-[A-Za-z0-9]{16}|BEGIN [A-Z ]*PRIVATE KEY" \
  --include="*.py" --include="*.dart" --include="*.kts" --include="*.sql" \
  --include="*.toml" --include="*.json" lib relay server agents \
  supabase android ios | grep -v ".env.example"
# expect: no output
python3 -m unittest discover -s relay/tests
python3 -m unittest discover -s server/tests
python3 -m unittest discover -s agents/tests
```
