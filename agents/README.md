# Desktop companions and shared workflows

The computer experience is a character overlay and background helper, not a dashboard.

- `macos.py`, `companion.py`, `client.py`: Mac helper lifecycle, pairing and delivery.
- `native/`: Swift Mac controls and the C# Windows application.
- `skills/`: selected-file teaching, learned recipes, citations and verified outputs shared by both companions.
- `windows_worker.py`: private stdio bridge for the bundled Windows workflow engine. It receives no pairing credentials and opens no network listener.
- `handlers.py`, `task_execution.py`, `workspace.py`, `file_management.py`, `document_tools.py`: scoped tools and permission/conflict checks.
- `windows.py`: older Python fallback; the supported Windows download uses the native C# application.
- `head_start.py`: disabled legacy adapter; do not describe it as a working automatic Muse guess.

Muse calls and budgets run through the authenticated server. Native UI and platform integration stay separate from the shared workflow logic. See the root README and `docs/watch-and-repeat.md` for current behavior and limits.
