# Build and release

The relay image includes `downloads/` and `build/web`. Build artifacts first; deploying source alone does not update installed phone or desktop apps. No release script should upload signing credentials.

## Prerequisites

- Flutter with the relevant platform SDKs; Python 3.12+.
- `python3 -m venv .venv-runtime`, then `.venv-runtime/bin/python -m pip install -r requirements-document-tools.txt`.
- Mac installer: macOS, Xcode command-line tools, and PyInstaller in that environment.
- Windows installer: .NET 10 SDK. Cross-builds from macOS are supported; the script bundles official CPython plus Windows document wheels. Run native verification on Windows as well.
- Android release: Java/Android SDK and the existing release keystore configured in ignored `android/key.properties`. Reuse the signing identity for upgrades.

## Checks

```sh
flutter pub get
flutter analyze
flutter test
.venv-runtime/bin/python -m unittest discover -s agents/tests
.venv-runtime/bin/python -m unittest discover -s test -p '*test.py'
.venv-runtime/bin/python -m unittest discover -s relay/tests
.venv-runtime/bin/python -m unittest discover -s server/tests
dotnet run --project test/windows_core/WindowsCore.csproj
```

`test/windows_apps`, `test/windows_files` and `test/windows_pairing` contain additional native checks. Windows capture and real high-DPI rendering still need device verification; a successful cross-build is not that verification.

## Build downloads

```sh
# Android; copies the signed release artifact to the download directory.
flutter build apk --release --dart-define-from-file=config/pico.public.json \
  --dart-define=RELAY_URL=https://pico-companion.fly.dev
mkdir -p downloads
cp build/app/outputs/flutter-apk/app-release.apk downloads/Pico-Android.apk

# iPhone web app, not a native signed IPA.
sh scripts/build_phone.sh --release \
  --dart-define=RELAY_URL=https://pico-companion.fly.dev

# Self-contained desktop installers.
PICO_RELAY_URL=https://pico-companion.fly.dev \
  .venv-runtime/bin/python scripts/build_windows_installer.py
PICO_RELAY_URL=https://pico-companion.fly.dev \
PICO_SIGN_IDENTITY='YOUR_EXISTING_SIGNING_IDENTITY' \
  .venv-runtime/bin/python scripts/build_macos_installer.py

# Public source, release manifest and checksums; all four downloads must exist.
.venv-runtime/bin/python scripts/package_companion.py
shasum -a 256 -c downloads/SHA256SUMS
```

Use `.venv-runtime\Scripts\python.exe` instead on Windows. The Mac installer is development-signed unless a suitable distribution identity is supplied; this script does not notarize it. The Windows script does not Authenticode-sign its EXE. Keep release claims accurate.

Versions are currently maintained separately in `pubspec.yaml`, the desktop build definitions, `scripts/package_companion.py` and the website. Keep the manifest’s per-platform versions aligned with the binaries actually built; do not label an unchanged artifact as a newer build.

## Deploy and verify

Only deploy to an account/environment you are authorized to change. Server secrets belong in deployment configuration, never the Flutter public config or source ZIP.

```sh
fly deploy -a pico-companion
curl --fail https://pico-companion.fly.dev/health
```

Fetch the live release manifest and hash the served downloads, comparing both bytes and SHA-256 against local artifacts. Check the served `phone/main.dart.js` against `build/web/main.dart.js`. Open the setup page and verify that every link/version matches. Preserve the previous Fly image for rollback.

The optional private test launcher is a development tool, not a prerequisite for the product. It restores a temporary relay on the configured test machine; it must not be run against somebody else’s deployment. Machine-local reports and sessions live under `.local/`.
