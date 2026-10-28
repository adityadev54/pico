"""Initialize the mounted state directory, then drop root before serving."""
import os
from pathlib import Path
from .app import main

if os.getuid() == 0:
    folder=Path('/data');folder.mkdir(exist_ok=True)
    os.chown(folder,10001,10001)
    os.setgid(10001);os.setuid(10001)
main()
