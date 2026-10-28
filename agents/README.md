# Desktop helpers

This folder runs Pico’s desktop companion: the character overlay, pairing, device sync and native windows. It is **not the AI agent backend**.

- `macos.py` / `windows.py` — desktop entry points.
- `companion.py` / `client.py` — helper lifecycle and relay connection.
- `native/` — platform windows and installers’ UI.
- `prompts/` / `head_start.py` — character instructions and an optional model adapter; no model is configured by default.

The team’s AI agent backend lives in `server/agent/`. The existing `agents/` path is retained for launcher and installer compatibility.
