## Mac 0.8.4 (24)

- Avoid unsafe macOS system proxy discovery in the packaged Python networking client; explicit proxy environment settings remain supported.
- Show server pairing errors instead of always suggesting an expired code.
- Unpair cleanly when the phone has already revoked the computer; repeated phone-side unpair requests are owner-scoped and idempotent.
- Include the runtime’s CA policy file in the Mac app so HTTPS initialization works after packaging.

## Mac 0.8.3 (23) / Windows 0.8.7

- Persistent focus gate: silent result cards wait in Places until you finish; interrupting incoming actions stay queued.
- Mac return cards now show saved local previews. All Places remain reachable in the scrolling list.
- Windows Continue reopens the captured app through its existing approval, with a reopening switch.
- New installs default to a one-minute step-away timer; existing timer settings are preserved.
- Phone remains 0.8.4 (24). No new APK is needed for these desktop changes.

# Windows 0.8.6 / Phone 0.8.4 (24)

- Natural requests resolve approved app names (including Chat GPT / Galaxy Buds spacing) instead of treating them as filenames. App approval remains local and mandatory.
- Older phones receive an explicitly typed approved-app result when Windows resolves an exact app name from a document-open request. No file candidate evidence is fabricated; server verification checks the requested name and app identity.
- Windows rechecks task activity before launch; Store activation failures retain a bounded Windows error rather than reporting success.
- Approved app catalogs are announced when an existing paired companion starts.

# Windows 0.8.5

- Search apps by name from running windows, Start-menu shortcuts and registered Microsoft Store applications. Manual EXE browsing remains a fallback; shortcut scripts/arguments are not imported.
- Store entries retain bounded app identities, while only approved IDs/names are sent to the phone. Existing EXE permissions remain compatible.
- App preview selection uses the same named picker for executable apps, and app exclusions are enforced during capture.

# Windows 0.8.4

- Fix clipped companion menu labels at high display scaling. Menu width follows measured text and icon/check gutters; narrow screens wrap labels and short screens scroll. Recalculates on monitor DPI changes.

# Windows 0.8.3

- Native Windows companion bundles the shared Python workflow engine and document dependencies. No Python installation or new server credentials required.
- Teach from selected text/Markdown/CSV/DOCX/PDF inputs and an edited Markdown example; run from the computer or paired phone. Citation validation, revoked-access checks and replay protection use the same engine as Mac.
- Reviewed PDF/image conversions, PDF merge/split/rotate/watermark, ZIP creation/extraction, recoverable trash/restore, and separately approved permanent trash clearing.
- Folder permissions refresh from disk. Delete permission remains a separate explicit choice.
- Step-away detection runs independently of network polling, with a 1–60 minute setting.
- Optional local active-window previews require an explicitly selected app. Browsers, messaging/password apps and protected windows are excluded. Previews are never uploaded to Muse or the relay.
- Parked Places lists waiting and saved places with local image previews; installer explains how to close a running copy before updating.
- Compiled for Windows 10/11 x64. Automated engine/IPC and native permission tests pass; physical Windows UI/capture validation is still required. Word-to-PDF requires an existing LibreOffice installation. No OCR or browser-preview support is claimed.

# Pico 0.8.2 (22)

Download at https://pico-companion.fly.dev/setup.

Android updates the original com.pico.app using the existing signing certificate. iPhone uses the updated Safari Home Screen web app; no publicly installable native IPA is provided. The Mac DMG targets Apple silicon, macOS 13+. It is development-signed, not Apple-notarized. Windows x64 is rebuilt, but teaching and the new document/archive/trash tools remain Mac-only. Phone-local games and timers work independently of those tools.

All website builds connect to the public HTTPS relay, not the private localhost test tunnel. Source ZIP and SHA256SUMS are included. No credentials, local user files or private test state belong in these downloads.

The Mac companion saves installed-app state under Library/Application Support/Pico. Existing paired accounts and server data are retained; a fresh companion state may require pairing with the phone. Update the existing phone web app with a full close and reopen if it shows stale UI.


Automatic companion reactions now include curious (learning or waiting for a game answer), happy (success), angry (failure), sleepy (quiet idle) and surprised (new step-away prompt). They preserve the original animated GIFs with distinct restrained motion. Needs-you and active work keep priority and renew their desktop pose lease without replaying historical success. Windows reply dismissal no longer clears an active non-talking mood.

Windows native helper currently supports pairing, encrypted connection storage, approved app and HTTPS website opening, folder grants, filename search, bounded text reads, document opening, file transfer, reviewed file writes and phone uploads, copy-only photo deduplication, reviewed commands, saved/parked Places and a two-minute step-away prompt. It does not yet implement the Mac/Python teaching engine, PDF/image conversions, ZIP/trash tools, or Mac-style snapshot/privacy controls. These are implementation gaps in its separate C# helper, not Windows OS limitations. Windows is cross-built, not physically verified in this release.
