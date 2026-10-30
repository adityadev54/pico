"""Meta Model API Client for Pico.

Handles communication with the Meta Model API (e.g. muse-spark-1.3) or local mock.
Rules:
- Never print or leak API keys in logs or exceptions.
- Enforce timeouts (config.request_timeout_seconds).
- Bounded retries with exponential backoff on transient errors (HTTP 429, 5xx).
- Tracks cumulative and per-call token usage and estimated cost against spending limit.
- Supports MOCK_MODEL=true mode returning deterministic synthetic tool calls.
- Simulated responses must be labeled [SIMULATED].
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from server.config import PicoConfig, config as default_config

logger = logging.getLogger(__name__)


@dataclass
class UsageMetrics:
    """Tracks token and latency usage across turns."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    call_count: int = 0
    total_latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0

    def record_turn(self, prompt: int, completion: int, latency_ms: float) -> None:
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += (prompt + completion)
        self.call_count += 1
        self.total_latency_ms += latency_ms
        # Conservative rate assumption: $0.15 / 1M prompt, $0.60 / 1M completion
        cost = (prompt * 0.15 + completion * 0.60) / 1_000_000.0
        self.estimated_cost_usd += cost


@dataclass
class MetaResponse:
    """Standardized response from Meta API or Mock."""
    content: Optional[str]
    tool_calls: List[Dict[str, Any]]
    usage: Dict[str, int]
    latency_ms: float
    model_name: str
    simulated: bool = False


class MetaClient:
    """Client for Meta Model API with bounded retries and spending limit enforcement."""

    def __init__(self, cfg: Optional[PicoConfig] = None):
        self.config = cfg or default_config
        self.usage = UsageMetrics()
        self.max_retries = 3
        self.backoff_factor = 0.5

    def _check_spending_limit(self) -> None:
        if self.usage.estimated_cost_usd >= self.config.spending_limit_dollars:
            raise RuntimeError(
                f"Spending limit exceeded: spent ${self.usage.estimated_cost_usd:.4f} "
                f"(limit: ${self.config.spending_limit_dollars:.2f})"
            )

    def _mock_chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> MetaResponse:
        """Deterministic mock response for offline development and unittests."""
        start_time = time.perf_counter()
        # Analyze last message to produce appropriate tool call
        last_msg = messages[-1]["content"] if messages else ""
        tool_calls: List[Dict[str, Any]] = []
        content: Optional[str] = None

        if tools and any(t.get("function", {}).get("name") == "search_documents" for t in tools):
            tool_calls.append(
                {
                    "id": f"call_mock_search_{int(time.time())}",
                    "type": "function",
                    "function": {
                        "name": "search_documents",
                        "arguments": json.dumps({"query": last_msg or "project brief"}),
                    },
                }
            )
            content = "I will search the computer documents for that file."
        elif tools and any(t.get("function", {}).get("name") == "transfer_selected_file" for t in tools):
            tool_calls.append(
                {
                    "id": f"call_mock_transfer_{int(time.time())}",
                    "type": "function",
                    "function": {
                        "name": "transfer_selected_file",
                        "arguments": json.dumps(
                            {"candidate_id": "cand_brief_123", "approval_id": "appr_mock_123"}
                        ),
                    },
                }
            )
            content = "Initiating transfer of the approved file."
        else:
            content = f"[SIMULATED] Echo: {last_msg}"

        latency_ms = (time.perf_counter() - start_time) * 1000
        mock_usage = {"prompt_tokens": 30, "completion_tokens": 15, "total_tokens": 45}
        self.usage.record_turn(30, 15, latency_ms)

        return MetaResponse(
            content=content,
            tool_calls=tool_calls,
            usage=mock_usage,
            latency_ms=round(latency_ms, 2),
            model_name=f"{self.config.meta_model} [SIMULATED]",
            simulated=True,
        )

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        temperature: float = 0.0,
    ) -> MetaResponse:
        """Sends chat request with bounded retries, timeouts, and usage tracking."""
        self._check_spending_limit()

        if self.config.mock_model or not self.config.meta_api_key:
            return self._mock_chat(messages, tools)

        endpoint = f"{self.config.meta_base_url.rstrip('/')}/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.config.meta_model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.meta_api_key}",
            "User-Agent": "Pico-Backend-Agent/1.0",
        }

        req_bytes = json.dumps(payload).encode("utf-8")
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries):
            start_time = time.perf_counter()
            req = urllib.request.Request(endpoint, data=req_bytes, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.config.request_timeout_seconds) as resp:
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    body = resp.read().decode("utf-8")
                    data = json.loads(body)
                    break
            except urllib.error.HTTPError as e:
                latency_ms = (time.perf_counter() - start_time) * 1000
                status_code = e.code
                error_body = ""
                try:
                    error_body = e.read().decode("utf-8", errors="replace")[:300]
                except Exception:
                    pass

                # Retry on 429 (Rate limit) or 5xx (Server error)
                if status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries - 1:
                    sleep_time = self.backoff_factor * (2 ** attempt)
                    time.sleep(sleep_time)
                    continue

                raise RuntimeError(
                    f"Meta API error (HTTP {status_code}): {error_body}"
                ) from None
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < self.max_retries - 1:
                    sleep_time = self.backoff_factor * (2 ** attempt)
                    time.sleep(sleep_time)
                    continue
                raise RuntimeError(f"Meta API network/timeout error: {e}") from None

        # Parse response
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"Meta API returned no choices: {data}")

        choice = choices[0]
        msg = choice.get("message", {})
        raw_tools = msg.get("tool_calls", []) or []
        usage_dict = data.get("usage", {})
        prompt_tokens = usage_dict.get("prompt_tokens", 0)
        completion_tokens = usage_dict.get("completion_tokens", 0)

        self.usage.record_turn(prompt_tokens, completion_tokens, latency_ms)

        return MetaResponse(
            content=msg.get("content"),
            tool_calls=raw_tools,
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            latency_ms=round(latency_ms, 2),
            model_name=data.get("model", self.config.meta_model),
            simulated=False,
        )

