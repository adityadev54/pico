"""Meta Model Smoke Test for Pico.

Tests connectivity, model ID verification, tool-calling capability,
multimodal (image) capability check, latency, and token usage.

Can run against live Meta Model API or in MOCK_MODEL mode (scripted/simulated).
Hard rules:
- No secrets in logs.
- Simulated responses must be labeled [SIMULATED].
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict

from server.config import PicoConfig


# Shared tool contract: search_documents tool definition
SEARCH_DOCUMENTS_TOOL = {
    "type": "function",
    "function": {
        "name": "search_documents",
        "description": "Search computer documents by query and optional folder-grant ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query text to find documents.",
                },
                "grant_id": {
                    "type": "string",
                    "description": "Optional folder-grant ID authorizing the search.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}

KNOWN_MULTIMODAL_MODELS = {
    "muse-spark-1.3",
    "muse-spark-1.2",
    "muse-spark-1.1",
    "llama-3.2-11b-vision-instruct",
    "llama-3.2-90b-vision-instruct",
}


def run_mock_smoke_test(config: PicoConfig) -> Dict[str, Any]:
    """Execute scripted mock test when MOCK_MODEL=true."""
    start_time = time.perf_counter()
    # Simulate a slight realistic parsing delay (e.g. 10ms)
    time.sleep(0.01)
    latency_ms = (time.perf_counter() - start_time) * 1000

    simulated_tool_call = {
        "id": "call_mock_search_001",
        "type": "function",
        "function": {
            "name": "search_documents",
            "arguments": json.dumps({"query": "project brief"}),
        },
    }

    return {
        "mode": "SIMULATED",
        "model_requested": config.meta_model,
        "model_confirmed": f"{config.meta_model} [SIMULATED]",
        "tool_calling_supported": True,
        "tool_call_emitted": simulated_tool_call["function"]["name"],
        "tool_call_arguments": simulated_tool_call["function"]["arguments"],
        "image_input_supported": True,
        "latency_ms": round(latency_ms, 2),
        "usage": {
            "prompt_tokens": 42,
            "completion_tokens": 18,
            "total_tokens": 60,
        },
    }


def run_live_smoke_test(config: PicoConfig) -> Dict[str, Any]:
    """Execute live request against Meta Model API."""
    if not config.meta_api_key:
        raise ValueError(
            "META_API_KEY is missing. Provide it in your environment/.env or run with --mock."
        )

    endpoint = f"{config.meta_base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": config.meta_model,
        "messages": [
            {
                "role": "user",
                "content": "Find my project brief using available tools.",
            }
        ],
        "tools": [SEARCH_DOCUMENTS_TOOL],
        "tool_choice": "auto",
        "temperature": 0.0,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.meta_api_key}",
        "User-Agent": "Pico-Backend-Agent/1.0",
    }

    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(endpoint, data=req_data, headers=headers, method="POST")

    start_time = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=config.request_timeout_seconds) as response:
            latency_ms = (time.perf_counter() - start_time) * 1000
            status_code = response.getcode()
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        error_body = ""
        try:
            error_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        # Never leak authorization headers or keys
        raise RuntimeError(
            f"Meta API HTTP {e.code}: {e.reason}. Details: {error_body[:300]}"
        ) from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"Failed to connect to Meta API at {endpoint}: {e.reason}") from None

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise RuntimeError(f"Invalid JSON returned from Meta API: {body[:200]}")

    model_confirmed = data.get("model", config.meta_model)
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError(f"No choices returned by Meta API: {data}")

    message = choices[0].get("message", {})
    tool_calls = message.get("tool_calls", [])
    tool_calling_supported = bool(tool_calls)

    tool_name = tool_calls[0]["function"]["name"] if tool_calls else None
    tool_args = tool_calls[0]["function"]["arguments"] if tool_calls else None

    # Inspect multimodal support (based on model capabilities / model series)
    image_input_supported = config.meta_model.lower() in KNOWN_MULTIMODAL_MODELS or "vision" in config.meta_model.lower() or "spark" in config.meta_model.lower()

    usage = data.get("usage", {})
    return {
        "mode": "REAL",
        "http_status": status_code,
        "model_requested": config.meta_model,
        "model_confirmed": model_confirmed,
        "tool_calling_supported": tool_calling_supported,
        "tool_call_emitted": tool_name,
        "tool_call_arguments": tool_args,
        "image_input_supported": image_input_supported,
        "latency_ms": round(latency_ms, 2),
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Pico Meta Model Smoke Test")
    parser.add_argument("--mock", action="store_true", help="Force scripted mock execution")
    parser.add_argument("--model", type=str, help="Override model ID")
    parser.add_argument("--base-url", type=str, help="Override API base URL")
    args = parser.parse_args()

    cfg = PicoConfig.from_env()
    # CLI overrides
    if args.mock:
        cfg = PicoConfig(
            meta_api_key=cfg.meta_api_key,
            meta_model=args.model or cfg.meta_model,
            meta_base_url=args.base_url or cfg.meta_base_url,
            max_model_turns=cfg.max_model_turns,
            max_tool_calls=cfg.max_tool_calls,
            request_timeout_seconds=cfg.request_timeout_seconds,
            tool_timeout_seconds=cfg.tool_timeout_seconds,
            task_deadline_seconds=cfg.task_deadline_seconds,
            spending_limit_dollars=cfg.spending_limit_dollars,
            mock_model=True,
        )
    elif args.model or args.base_url:
        cfg = PicoConfig(
            meta_api_key=cfg.meta_api_key,
            meta_model=args.model or cfg.meta_model,
            meta_base_url=args.base_url or cfg.meta_base_url,
            max_model_turns=cfg.max_model_turns,
            max_tool_calls=cfg.max_tool_calls,
            request_timeout_seconds=cfg.request_timeout_seconds,
            tool_timeout_seconds=cfg.tool_timeout_seconds,
            task_deadline_seconds=cfg.task_deadline_seconds,
            spending_limit_dollars=cfg.spending_limit_dollars,
            mock_model=cfg.mock_model,
        )

    print("==================================================")
    print("           PICO META API SMOKE TEST               ")
    print("==================================================")
    summary = cfg.safe_summary()
    print(f"Model ID Requested : {summary['meta_model']}")
    print(f"Base URL           : {summary['meta_base_url']}")
    print(f"API Key Status     : {summary['api_key_masked']}")
    print(f"Mock Mode Active   : {summary['mock_model']}")
    print("--------------------------------------------------")

    should_mock = cfg.mock_model or not cfg.meta_api_key

    try:
        if should_mock:
            if not cfg.mock_model and not cfg.meta_api_key:
                print("Notice: No META_API_KEY provided; falling back to [SIMULATED] mock mode.")
            result = run_mock_smoke_test(cfg)
        else:
            result = run_live_smoke_test(cfg)

        print("\nResults:")
        prefix = "[SIMULATED] " if result["mode"] == "SIMULATED" else ""
        print(f"  Execution Mode        : {prefix}{result['mode']}")
        print(f"  Model ID Confirmed    : {result['model_confirmed']}")
        print(f"  Tool Calling Support  : {result['tool_calling_supported']} (emitted: {result.get('tool_call_emitted')})")
        if result.get("tool_call_arguments"):
            print(f"  Tool Call Arguments   : {result['tool_call_arguments']}")
        print(f"  Image Input Support   : {result['image_input_supported']} (multimodal)")
        print(f"  Latency               : {result['latency_ms']} ms")
        print(f"  Token Usage           : Prompt={result['usage']['prompt_tokens']}, "
              f"Completion={result['usage']['completion_tokens']}, "
              f"Total={result['usage']['total_tokens']}")
        print("--------------------------------------------------")
        print("SMOKE TEST PASSED" if result["tool_calling_supported"] else "SMOKE TEST WARNING: No tool call emitted")
        return 0

    except Exception as e:
        print(f"\nSMOKE TEST FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

