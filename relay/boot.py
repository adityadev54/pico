"""Initialize the mounted state directory, then drop root before serving."""
import os
from pathlib import Path
from .app import main

if os.getuid() == 0:
    folder=Path('/data');folder.mkdir(exist_ok=True)
    os.chown(folder,10001,10001)
    # Existing persistent files can predate the restricted runtime user.
    # Only fix known SQLite state files, never arbitrary mounted contents.
    ledger = Path(os.environ.get('PICO_MODEL_LEDGER', '/data/model-budget.sqlite'))
    for state_file in (folder / 'relay.sqlite', ledger):
        if state_file.parent == folder and state_file.is_file() and not state_file.is_symlink():
            os.chown(state_file,10001,10001)
    os.setgid(10001);os.setuid(10001)
main()
