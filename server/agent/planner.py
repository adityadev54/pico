"""Model planner — one OpenAI-compatible call that returns a structured tool call.

The planner converts the task text + available tools into a validated
tool_call dict the AgentLoop can consume.  It has no side effects: no file
writes, no process spawns.  If the model is not configured or the response
cannot be parsed the planner returns a clarification instead of pretending
to succeed.

LoGesH owns this file.  Santosh's verifier never touches it.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
import uuid


SYSTEM_PROMPT = """You are a task planner for Pico, a personal desktop assistant.
The user has sent a task from their phone. Select exactly one tool call
from the available tools to progress the task, or ask ONE short
clarification question if the task is ambiguous.

Respond with ONLY valid JSON in one of these two shapes:

Tool call:
{
  "action": "tool_call",
  "tool": "<tool name>",
  "arguments": { ... }
}

Clarification:
{
  "action": "clarify",
  "question": "What would you like me to search for?"
}

Rules:
- Never invent tool names. Only use names from the tool list.
- Never include secrets, file paths or personal data in progress messages.
- A search always comes before a transfer; never transfer without approval.
- Keep arguments short; query max 500 chars, paths relative and inside the workspace.
"""


def _tool_summary(tools: list[dict]) -> str:
    lines = []
    for tool in tools:
        if not tool.get("available", True):
            continue
        args = ", ".join(
            f"{k} ({'required' if v.get('required') else 'optional'})"
            for k, v in (tool.get("args") or {}).items()
        )
        lines.append(f"- {tool['name']}: {tool['description']}  args: {args}")
    return "\n".join(lines) if lines else "(no tools available)"


def plan(task: dict, tools: list[dict], cfg: dict) -> dict:
    """Call the model once; return a partial tool_call dict or a question string.

    Returns:
        {"tool_call": {...}}  — ready for AgentLoop.plan()
        {"question": "..."}  — ready for AgentLoop.plan(tool_call=None, question=...)
        {"error": "..."}     — model unavailable or parse failure
    """
    endpoint = cfg.get("url", "")
    key = cfg.get("key", "")
    model = cfg.get("model", "muse-spark-1.3")

    if not endpoint or not key:
        return {"error": "Model not configured (MUSE_API_URL / MUSE_API_KEY)."}

    if urllib.parse.urlparse(endpoint).scheme != "https":
        return {"error": "MUSE_API_URL must use HTTPS."}

    user_content = (
        f"Task: {task.get('input', '')[:2000]}\n\n"
        f"Available tools:\n{_tool_summary(tools)}"
    )
    body = {
        "model": model,
        "max_tokens": 400,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + key,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
        raw_text = str(payload["choices"][0]["message"]["content"]).strip()
    except Exception as exc:
        return {"error": f"Model call failed: {type(exc).__name__}"}

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        # Try to extract JSON from a markdown code block, if the model wrapped it.
        import re
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(1))
            except json.JSONDecodeError:
                return {"error": f"Model returned unparseable JSON: {raw_text[:200]}"}
        else:
            return {"error": f"Model returned unparseable JSON: {raw_text[:200]}"}

    action = parsed.get("action")
    if action == "clarify":
        question = str(parsed.get("question", "What should I do?"))[:500]
        return {"question": question}

    if action == "tool_call":
        tool_name = str(parsed.get("tool", ""))
        arguments = parsed.get("arguments")
        if not isinstance(arguments, dict):
            arguments = {}
        task_id = task.get("id", str(uuid.uuid4()))
        step_id = f"step-{uuid.uuid4().hex[:8]}"
        call_id = f"call-{uuid.uuid4().hex[:8]}"
        return {
            "tool_call": {
                "contract_version": 1,
                "type": "tool_call",
                "task_id": task_id,
                "step_id": step_id,
                "call_id": call_id,
                "tool": tool_name,
                "arguments": arguments,
                "idempotency_key": f"{task_id}:{step_id}",
                "deadline_seconds": 30,
            }
        }

    return {"error": f"Model returned unknown action: {action!r}"}
