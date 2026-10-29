"""Meta smoke test. Runnable setup, no secrets in output or logs."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request


def smoke_test(endpoint: str, key: str, model: str = "muse-spark-1.3", timeout: int = 20) -> dict:
    """One tiny OpenAI-compatible request. Returns {ok, model, latency_ms} or raises."""
    import time

    if not endpoint or not key:
        raise ValueError("Configure MUSE_API_URL and MUSE_API_KEY first.")
    if urllib.parse.urlparse(endpoint).scheme != "https":
        raise ValueError("The Meta endpoint must use HTTPS.")
    body = {
        "model": model,
        "max_tokens": 5,
        "messages": [{"role": "user", "content": "Reply with: ok"}],
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
    )
    start = time.monotonic()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    text = str(payload["choices"][0]["message"]["content"]).strip()
    return {"ok": True, "model": model, "latency_ms": int((time.monotonic() - start) * 1000),
            "reply_prefix": text[:20]}


if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, ".")
    from server.config import load_env_file, muse_config

    load_env_file(os.environ.get("PICO_ENV_FILE", "server/.env"))
    cfg = muse_config()
    try:
        print(json.dumps(smoke_test(cfg["url"], cfg["key"], cfg["model"])))
    except Exception as error:
        print(f"Meta smoke test failed: {type(error).__name__}", file=sys.stderr)
        raise SystemExit(1)
