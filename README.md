# Pico

A phone and desktop companion for picking up work across devices—and repeating useful routines you have shown it once.

[Download Pico](https://pico-companion.fly.dev/setup#setup) · [Watch & repeat guide](docs/watch-and-repeat.md) · [Build and release](docs/runbook.md) · [Release notes](RELEASE-NOTES.md)

## What you can do

- **Hold your place.** Step away from your computer, save your next step on your phone, and return to it through the companion. Park unfinished work for later.
- **Work with your computer from your phone.** Open approved apps and websites, find files in approved folders, transfer a selected file, save an upload, and review file changes.
- **Teach a repeatable result.** Select source documents, edit an example result, and let Muse learn the transformation. Run that routine on updated inputs from the conversation. Pico checks source quotations and verifies the saved output.
- **Use local tools.** File search, bounded text reads/writes, supported PDF/image operations, archives, reviewed trash/restore, games and timers do not need a model call.
- **Capture from your phone.** The composer’s **+** menu contains microphone, camera and Watch & repeat. Camera uploads use the existing reviewed save flow.

Pico teaches selected-file transformations. It does not record arbitrary mouse/keyboard activity or promise to automate every application.

## Install and connect

| Device | Current download | Requirements |
| --- | --- | --- |
| Android | APK · 0.8.3 (23) | Android 7+; update over the existing app |
| iPhone | Web app | Safari → Share → Add to Home Screen; no native IPA is published |
| Mac | DMG · 0.8.2 (22) | Apple silicon, macOS 13+; development-signed, not notarized |
| Windows | EXE · 0.8.4 | Windows 10/11 x64; runtime bundled |

1. Install the phone app and desktop companion.
2. Sign in on the phone, get a six-digit pairing code, and enter it on the computer.
3. Choose the applications and folders Pico may use. Read, write and reviewed-trash permissions are separate.
4. Try an ordinary request such as “Find my lecture notes.” Only approved folders are searched.

On Windows, **Open apps → Choose app…** currently selects an installed `.exe`; a searchable installed-app catalog is not implemented. Quit the running companion before installing a desktop update. Pairing and settings are retained.

## What uses Muse?

| Work | Processing |
| --- | --- |
| Pairing, connection checks, approved app/site opening, file tools, Places, games and timers | Deterministic/local tools; connected actions still need the relay |
| Learning or running a taught routine; supported AI planning and requested summaries | Muse through the authenticated server and configured account/budget limits |
| Companion moods | Local activity state and device messages; no model call |
| Optional window previews | Saved on the computer; this release does not send them to Muse |

Model access can be restricted by account. Spending limits are server-configured; reservation estimates are not actual provider invoices. Failed model requests are not automatically retried. Provider and Supabase service credentials never belong in Flutter or version control.

## Are the new moods real?

Yes: they are automatic activity reactions, not a manual picker. Both characters keep their original animated GIFs, with additional shake, tilt, bounce, sway or pop motion.

| Mood | Trigger | Original GIF |
| --- | --- | --- |
| Curious | Learning/waiting for a local game answer | Thinking |
| Happy | A successful task or routine | Done |
| Angry | A failed task or routine | Stuck |
| Sleepy | Quiet idle, driven by the phone activity timer | Idle |
| Surprised | A new step-away prompt | Needs-you |

Approvals take priority. Brief reactions return to the current activity; old completed tasks do not replay them. Active moods refresh before their desktop lease expires. Reduced-motion behavior is respected by the phone and native motion layers.

These are **not five newly drawn facial GIFs**. Flutter tests cover triggers, original-GIF selection and mood refresh; relay tests cover delivery. The Mac/Windows native implementations compile. Physical Windows visual/capture checks and physical Android camera checks are still incomplete.

## Permissions and current boundaries

- Folder access is explicit; revocation is checked before sensitive operations. Writes use conflict checks rather than silently replacing changed files.
- Reviewed trash access is stronger than ordinary write access. Permanently emptying Pico trash requires a separate computer approval.
- Commands require computer approval, run without a shell, and have bounded time/output. App opening grants do not grant screen access.
- Windows previews are opt-in for selected apps. Browsers, messaging/password apps and protected windows are excluded; previews stay local.
- Current transfer/conversion limits include a 1 MB file/output cap. Taught routines accept 1–4 readable documents, at most 6,000 characters total, and an example up to 2,000 characters. Scanned PDFs need OCR elsewhere first.
- Word-to-PDF requires an existing LibreOffice installation. Other bundled document tools do not require installing Python on Windows.
- Legacy automatic Head Start/“guess my next step” is not the working Muse feature in this version; taught routines are.

## Develop

Flutter/Dart powers the phone UI. Python runs the relay and shared workflow engine. Native Swift and C# provide the desktop overlays and controls. Supabase supplies accounts and persistent service data.

```sh
flutter pub get
python3 -m venv .venv-runtime
.venv-runtime/bin/python -m pip install -r requirements-document-tools.txt

# Phone: defaults to the configured public relay
sh scripts/run_phone.sh

# Mac companion: uses .venv-runtime by default
sh scripts/run_companion.sh
```

On Windows, create the environment with `py -3 -m venv .venv-runtime` and use `.venv-runtime\Scripts\python.exe`. Build the native installer with .NET 10 using the commands in the [runbook](docs/runbook.md). Override `RELAY_URL`/`--relay` only when deliberately testing your own relay. A local relay needs server-only Supabase configuration and the schema documented in [security](docs/security.md); starting it does not provision a backend.

```sh
flutter analyze
flutter test
.venv-runtime/bin/python -m unittest discover -s agents/tests
.venv-runtime/bin/python -m unittest discover -s test -p '*test.py'
.venv-runtime/bin/python -m unittest discover -s relay/tests
.venv-runtime/bin/python -m unittest discover -s server/tests

dotnet run --project test/windows_core/WindowsCore.csproj
```

## Project map

| Folder | Responsibility |
| --- | --- |
| `lib/components`, `lib/screens`, `lib/theme` | Reusable Flutter UI, screens and visual roles |
| `lib/services`, `lib/models`, `lib/platforms` | App state/networking, data types and platform adapters |
| `agents` | Desktop helper lifecycle, scoped tools and shared `skills` engine |
| `agents/native` | Swift Mac overlay and C# Windows companion |
| `relay`, `server` | Authenticated transport, budgets, model calls and verification |
| `test`, `agents/tests`, `relay/tests`, `server/tests` | Regression tests and native checks |
| `scripts`, `config` | Launch/build tools and public configuration |
| `website`, `docs` | Download page and maintained guides |

`build/`, `downloads/`, `.local/` and virtual environments are generated or machine-local and ignored. Local pairing state, signing keys, private reports and credentials are not pushed. Release binaries are distributed through the download website rather than committed to Git.
