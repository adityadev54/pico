"""Server-only configuration. Never import from Flutter."""
from __future__ import annotations

import os
from pathlib import Path


def load_env_file(path: str | None) -> None:
    if not path:
        return
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def muse_config() -> dict:
    return {
        "url": os.environ.get("MUSE_API_URL", ""),
        "key": os.environ.get("MUSE_API_KEY", ""),
        "model": os.environ.get("MUSE_MODEL", "muse-spark-1.3"),
    }


def muse_configured() -> bool:
    cfg = muse_config()
    return bool(cfg["url"] and cfg["key"])
