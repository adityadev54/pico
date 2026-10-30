# QA matrix

Two layers: automated gates that run on any release machine, and a hardware
checklist that needs physical devices. Do not ship 1.0.0 with either red.

## Automated gates

Requires Flutter ≥3.47.8 (see `pubspec.yaml`) and Python 3.12+.

```sh
flutter pub get
flutter analyze
flutter test
python3 -m unittest discover -s server/tests
python3 -m unittest discover -s relay/tests
python3 -m unittest discover -s agents/tests
python3 -m py_compile relay/*.py agents/*.py agents/tests/*.py server/*.py server/*/*.py scripts/*.py
python3 scripts/make_macos_app.py   # macOS only; proves the overlay still builds
python3 scripts/package_companion.py
```

Live backend (needs `server.env` with `SUPABASE_URL` +
`SUPABASE_SERVICE_ROLE_KEY`; never commit it):

```sh
python3 scripts/check_connection.py --env-file /path/to/server.env --report /tmp/pico-check.json
```

Expect a green report: sign-up, pairing, claim, mailbox, task queue,
transfer, receipt, unpair, lockout. Run it once against a review project and
once against production before tagging.

## Hardware checklist

One clean machine per row. “Clean” means no prior Pico install, no
`~/.pico`, no dev relay running.

Phone — Android APK (`downloads/Pico-Android.apk`):

- [ ] Install, sign up, stay signed in across restart (Remember me on/off).
- [ ] Pairing code appears; entering it on desktop connects within seconds.
- [ ] Save a Place by typing and by voice; mic prompt explains itself.
- [ ] Voice command “find my project brief” creates a document search task.
- [ ] Candidate list shows exact names + sizes; Send transfers the tapped file.
- [ ] Downloaded file opens from share sheet; task shows verified.
- [ ] Airplane mode: Places save locally, delivery retries on reconnect.
- [ ] Unpair from Devices; desktop returns to the code screen immediately.

Phone — iPhone PWA (`/phone/` in Safari → Add to Home Screen):

- [ ] Same pairing, Place, search, transfer, and unpair rows as Android.
- [ ] Standalone launch (no Safari chrome) after Add to Home Screen.

Desktop — macOS (`Pico-macOS.dmg`):

- [ ] Drag to Applications, open: Gatekeeper behavior noted (signed + notarized
      expected for production; ad-hoc dev builds warn — never ship those).
- [ ] Enter the phone code; character appears and follows picker changes.
- [ ] Idle timeout parks a Place; return shows the welcome card.
- [ ] Search/transfer tasks from the phone execute and report back.
- [ ] Permissions window toggles persist; Quit + relaunch resumes paired state.
- [ ] Unpair from the phone revokes the desktop token at once.

Desktop — Windows (`Pico-Setup.exe`):

- [ ] Install per-user; SmartScreen behavior noted (signed expected).
- [ ] Same pairing, character sync, task execution, and unpair rows as macOS.

Relay + backend:

- [ ] `/health` reports both checks true; Fly logs show access lines with no
      query strings, codes, or tokens.
- [ ] Five wrong codes from one address locks out for 10 minutes.
- [ ] Deployed `/download/SHA256SUMS` matches every served artifact.

## Sign-off

| Surface | Device/OS | Build | Result | Tester | Date |
| ------- | --------- | ----- | ------ | ------ | ---- |
| Android |           |       |        |        |      |
| iPhone  |           |       |        |        |      |
| macOS   |           |       |        |        |      |
| Windows |           |       |        |        |      |
| Relay   | Fly       |       |        |        |      |
