# Python backend

Run from the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m server.app
```

On Windows activate with `.venv\Scripts\activate`.

- GET `/health`: explicit status; it does not claim Meta/device connectivity.
- GET `/contracts`: sample messages, not real task data.
- POST `/request`, `/plan`, `/tool_result`, `/approve`, `/cancel`: localhost-only authenticated task loop.
- GET `/task?id=..`: read your own task.

The server binds to localhost. It is not a deployed relay or a secure remote-control service. No model calls run by default; use `python3 -m server.agent.meta` with `PICO_ENV_FILE=server/.env` for the Meta smoke test.

Before Meta integration, copy `server/.env.example` to `server/.env` (gitignored). Never send keys in tool messages or put them in Flutter. Deterministic tests: `python3 -m unittest discover -s server/tests`.

LoGesH owns agent code and prompts. Santosh owns verification code and its tests. Coordinate edits to `app.py`, dependencies and shared messages. A different server framework is fine if the contract remains compatible.
