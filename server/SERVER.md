# Python backend

Run from the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m server.app
```

On Windows activate with `.venv\Scripts\activate`.

- GET `/health`: explicit scaffold status; it does not claim Meta/device connectivity.
- GET `/contracts`: sample messages, not real task data.

The server binds to localhost. It is not a deployed relay or a secure remote-control service. No model calls or actions run yet. Add authenticated endpoints before exposing task functionality.

Before Meta integration, use `server/.env.example` as your local template. The scaffold does not load `.env`; implement environment loading/configuration with the agent. Never send keys in tool messages or put them in Flutter.

LoGesH owns agent code and prompts. Santosh owns verification code and its tests. Coordinate edits to `app.py`, dependencies and shared messages. A different server framework is fine if the contract remains compatible.
