"""Configuration loader for Pico server.

Loads settings from environment variables and local .env files.
Never prints or leaks secrets in logs.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _load_env_file(path: Path) -> None:
    """Lightweight .env file parser that does not require external dependencies."""
    if not path.is_file():
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    # Do not overwrite existing environment variables
                    if key and key not in os.environ:
                        os.environ[key] = val
    except Exception:
        # Failing to read a malformed .env should not crash initialization
        pass


def load_environment() -> None:
    """Finds and loads .env from current directory, server directory, or repo root."""
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv()
    except ImportError:
        pass

    # Fallback / manual check in standard locations
    repo_root = Path(__file__).resolve().parents[1]
    candidates = [
        Path.cwd() / ".env",
        repo_root / "server" / ".env",
        repo_root / ".env",
    ]
    for env_path in candidates:
        if env_path.is_file():
            _load_env_file(env_path)
            break


@dataclass(frozen=True)
class PicoConfig:
    meta_api_key: str
    meta_model: str
    meta_base_url: str
    max_model_turns: int
    max_tool_calls: int
    request_timeout_seconds: float
    tool_timeout_seconds: float
    task_deadline_seconds: float
    spending_limit_dollars: float
    mock_model: bool

    @classmethod
    def from_env(cls) -> "PicoConfig":
        load_environment()

        def _get_int(key: str, default: int) -> int:
            val = os.getenv(key)
            if val is None or not val.strip():
                return default
            try:
                return int(val.strip())
            except ValueError:
                raise ValueError(f"Invalid integer for {key}: {val!r}")

        def _get_float(key: str, default: float) -> float:
            val = os.getenv(key)
            if val is None or not val.strip():
                return default
            try:
                return float(val.strip())
            except ValueError:
                raise ValueError(f"Invalid float for {key}: {val!r}")

        def _get_bool(key: str, default: bool) -> bool:
            val = os.getenv(key)
            if val is None or not val.strip():
                return default
            return val.strip().lower() in ("1", "true", "yes", "on")

        api_key = os.getenv("META_API_KEY", "").strip()
        model = os.getenv("META_MODEL", "muse-spark-1.3").strip() or "muse-spark-1.3"
        base_url = os.getenv("META_BASE_URL", "https://api.meta.ai/v1").strip() or "https://api.meta.ai/v1"
        max_turns = _get_int("MAX_MODEL_TURNS", 5)
        max_tools = _get_int("MAX_TOOL_CALLS", 6)
        req_timeout = _get_float("REQUEST_TIMEOUT_SECONDS", 30.0)
        tool_timeout = _get_float("TOOL_TIMEOUT_SECONDS", 30.0)
        deadline = _get_float("TASK_DEADLINE_SECONDS", 120.0)
        spending_limit = _get_float("SPENDING_LIMIT_DOLLARS", 5.00)
        mock_mode = _get_bool("MOCK_MODEL", False)

        return cls(
            meta_api_key=api_key,
            meta_model=model,
            meta_base_url=base_url,
            max_model_turns=max_turns,
            max_tool_calls=max_tools,
            request_timeout_seconds=req_timeout,
            tool_timeout_seconds=tool_timeout,
            task_deadline_seconds=deadline,
            spending_limit_dollars=spending_limit,
            mock_model=mock_mode,
        )

    def validate(self, require_api_key: bool = False) -> None:
        """Validate bounded limits and required keys."""
        if require_api_key and not self.mock_model and not self.meta_api_key:
            raise ValueError(
                "META_API_KEY is required when MOCK_MODEL=false. "
                "Provide META_API_KEY or set MOCK_MODEL=true for simulated execution."
            )
        if self.max_model_turns <= 0:
            raise ValueError(f"MAX_MODEL_TURNS must be positive, got {self.max_model_turns}")
        if self.max_tool_calls <= 0:
            raise ValueError(f"MAX_TOOL_CALLS must be positive, got {self.max_tool_calls}")
        if self.request_timeout_seconds <= 0:
            raise ValueError(f"REQUEST_TIMEOUT_SECONDS must be positive, got {self.request_timeout_seconds}")
        if self.tool_timeout_seconds <= 0:
            raise ValueError(f"TOOL_TIMEOUT_SECONDS must be positive, got {self.tool_timeout_seconds}")
        if self.task_deadline_seconds <= 0:
            raise ValueError(f"TASK_DEADLINE_SECONDS must be positive, got {self.task_deadline_seconds}")
        if self.spending_limit_dollars < 0:
            raise ValueError(f"SPENDING_LIMIT_DOLLARS cannot be negative, got {self.spending_limit_dollars}")

    def safe_summary(self) -> dict[str, object]:
        """Return safe dictionary for logging without leaking secrets."""
        masked_key = (
            f"{self.meta_api_key[:4]}...{self.meta_api_key[-2:]}"
            if len(self.meta_api_key) >= 6
            else ("<set>" if self.meta_api_key else "<unset>")
        )
        return {
            "meta_model": self.meta_model,
            "meta_base_url": self.meta_base_url,
            "api_key_configured": bool(self.meta_api_key),
            "api_key_masked": masked_key,
            "mock_model": self.mock_model,
            "max_model_turns": self.max_model_turns,
            "max_tool_calls": self.max_tool_calls,
            "request_timeout_seconds": self.request_timeout_seconds,
            "tool_timeout_seconds": self.tool_timeout_seconds,
            "task_deadline_seconds": self.task_deadline_seconds,
            "spending_limit_dollars": self.spending_limit_dollars,
        }


# Global default configuration instance
config = PicoConfig.from_env()

