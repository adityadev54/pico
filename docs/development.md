# Development


Prerequisites: Flutter with the relevant platform SDK, Python 3.12+, and .NET 10 for the native Windows companion. Mac builds require Xcode command-line tools.

```sh
git clone https://github.com/adityadev54/pico.git
cd pico
flutter pub get
python3 -m venv .venv-runtime
.venv-runtime/bin/python -m pip install -r requirements-document-tools.txt

# Phone app: uses the configured relay by default.
sh scripts/run_phone.sh

# Mac companion.
sh scripts/run_companion.sh
```

On Windows use `py -3 -m venv .venv-runtime` and `.venv-runtime\Scripts\python.exe`. To build the native companion:

```sh
python scripts/build_windows_installer.py
```

This downloads the bundled runtime and builds `downloads/Pico-Setup.exe`. See the [build and release guide](runbook.md) for signed Android builds, Mac packaging and the iPhone web app.

### Running your own relay

Configure an existing compatible Supabase backend; this repository does not provision its database policies. Put `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in an ignored server environment file. Muse additionally needs server-only `MUSE_API_URL`, `MUSE_API_KEY`, `MUSE_MODEL` and the required account/budget configuration.

```sh
PICO_ENV_FILE=/path/to/server.env sh scripts/run_relay.sh
sh scripts/run_phone.sh --dart-define=RELAY_URL=http://localhost:8765
sh scripts/run_companion.sh --relay http://localhost:8765
```

Use your computer’s reachable address for physical-phone development; `localhost` on a phone refers to that phone. Non-local plain HTTP is disabled by default in the helper. Keep public Flutter configuration separate from service credentials. [Security notes →](security.md)

### Tests

```sh
flutter analyze
flutter test
.venv-runtime/bin/python -m unittest discover -s agents/tests
.venv-runtime/bin/python -m unittest discover -s test -p '*test.py'
.venv-runtime/bin/python -m unittest discover -s relay/tests
.venv-runtime/bin/python -m unittest discover -s server/tests
dotnet run --project test/windows_core/WindowsCore.csproj
```

Windows CI exercises the shared worker, permissions, app grants, file operations, pairing and installer build on a Windows runner. UI/device checks are still needed for camera behavior and monitor-specific rendering.

### Repository layout

```text
lib/            Flutter components, screens, services, models and theme
agents/         Desktop helpers, native UI and shared workflow engine
relay/          Authenticated transport, mailbox and budget integration
server/         AI planning and verification
scripts/        Run, build and packaging commands
config/         Public application configuration
website/        Download and setup page
test/           Flutter/integration tests and native Windows checks
docs/           Workflow, security and release guides
```

Generated builds, downloads, environments, private reports and pairing state are ignored. Do not commit signing material or service credentials.

## Current limits


- This is a development release: the Mac download is development-signed rather than notarized, and no native iPhone IPA is published.
- File transfers and supported conversion outputs currently have a 1 MB cap. Taught routines use 1–4 readable documents, at most 6,000 characters total, and an example up to 2,000 characters. Scanned PDFs need OCR elsewhere; Word-to-PDF needs LibreOffice.
- Windows window previews are opt-in, remain local, and exclude browsers and sensitive apps. They are not uploaded to Muse.
- New moods are automatic motion on the original GIFs, not five newly drawn facial animations. [Mood behavior →](companion-moods.md)
- Muse access and spending limits are server-controlled. A reservation is not a provider invoice. Model requests are not automatically retried.

