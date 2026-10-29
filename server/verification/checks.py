"""Tool-specific outcome checks with synthetic fixtures."""
from __future__ import annotations

from ..contract import ContractError


def check_search_outcome(result: dict) -> dict:
    """Search must return bounded candidates or a stable no_match/denied code."""
    if result.get("status") == "succeeded":
        candidates = (result.get("data") or {}).get("candidates", [])
        if not isinstance(candidates, list) or not candidates:
            raise ContractError("no_match", "Search succeeded without candidates.")
        if len(candidates) > 20:
            raise ContractError("invalid_message", "Too many candidates.")
        for candidate in candidates:
            if not candidate.get("candidate_id") or not candidate.get("name"):
                raise ContractError("invalid_message", "Candidate missing id or name.")
        return {"ok": True, "count": len(candidates)}
    code = (result.get("error") or {}).get("code", "")
    if code not in ("no_match", "permission_denied", "timeout", "device_offline",
                    "invalid_args", "unsupported_tool"):
        raise ContractError("invalid_message", f"Unexpected search error: {code}.")
    return {"ok": False, "code": code}


def check_exact_file(candidate: dict, approval: dict, evidence: dict) -> dict:
    """User selection resolves ambiguity; helper rechecks exact identity."""
    if candidate.get("candidate_id") != approval.get("candidate_id"):
        raise ContractError("candidate_changed", "Approved file does not match candidate.")
    if evidence.get("candidate_id") != candidate.get("candidate_id"):
        raise ContractError("candidate_changed", "Native evidence is for another file.")
    # Size/digest mismatch means the file changed between approval and transfer.
    if "size_bytes" in candidate and "size_bytes" in evidence:
        if candidate["size_bytes"] != evidence["size_bytes"]:
            raise ContractError("candidate_changed", "File changed before transfer.")
    if "digest" in candidate and "digest" in evidence:
        if candidate["digest"] != evidence["digest"]:
            raise ContractError("candidate_changed", "File changed before transfer.")
    return {"ok": True}


def check_transfer_receipt(evidence: dict, receipt: dict) -> dict:
    """Upload is not phone receipt. Both expected and received size/digest must match."""
    if not receipt.get("authenticated"):
        raise ContractError("unauthorized", "Phone receipt must be authenticated.")
    for field in ("size_bytes", "digest"):
        expected, received = evidence.get(field), receipt.get(field)
        if expected is None or received is None:
            raise ContractError("invalid_message", f"Missing {field} in transfer evidence.")
        if expected != received:
            raise ContractError("candidate_changed", f"{field} mismatch: not the approved file.")
    return {"ok": True}


def check_checklist(approved: list, saved: list) -> dict:
    """Saved checklist content must equal approved content."""
    if [str(x)[:300] for x in approved] != [str(x)[:300] for x in saved]:
        raise ContractError("candidate_changed", "Checklist differs from approved content.")
    return {"ok": True, "count": len(saved)}


def check_fs_manifest(manifest: dict, kind: str) -> dict:
    """Filesystem results must carry complete, shaped evidence."""
    if not isinstance(manifest, dict):
        raise ContractError("invalid_message", "Missing file manifest.")
    if kind == "fs_list":
        entries = manifest.get("entries")
        if not isinstance(entries, list):
            raise ContractError("invalid_message", "Folder listing is malformed.")
        return {"ok": True, "count": len(entries)}
    for field in ("path", "size_bytes", "digest"):
        if manifest.get(field) is None:
            raise ContractError("invalid_message", f"Manifest lacks {field}.")
    if kind == "fs_read" and manifest.get("binary") is not True and "content" not in manifest:
        raise ContractError("invalid_message", "Text read lacks content.")
    return {"ok": True}


def check_process_result(data: dict) -> dict:
    """Process results must carry exit code and both streams.

    A nonzero exit is data (the command ran and reported), not a
    verification failure; missing fields are.
    """
    if not isinstance(data, dict) or not isinstance(data.get("exit_code"), int):
        raise ContractError("invalid_message", "Process result lacks an exit code.")
    if "stdout" not in data or "stderr" not in data:
        raise ContractError("invalid_message", "Process result lacks streams.")
    return {"ok": True, "exit_code": data["exit_code"]}


def check_organize_manifest(data: dict) -> dict:
    """Photo triage must report folder + honest counts. Zero photos is a
    valid empty result, not a failure; missing or negative counts are."""
    if not isinstance(data, dict):
        raise ContractError("invalid_message", "Missing organize manifest.")
    if not data.get("folder") or not isinstance(data.get("folder"), str):
        raise ContractError("invalid_message", "Organize manifest lacks a folder.")
    for field in ("copied_count", "duplicates_skipped", "found"):
        value = data.get(field)
        if not isinstance(value, int) or value < 0:
            raise ContractError("invalid_message", f"Organize manifest lacks {field}.")
    if data["copied_count"] + data["duplicates_skipped"] > data["found"]:
        raise ContractError("invalid_message", "Organize counts do not add up.")
    return {"ok": True, "copied": data["copied_count"]}


def check_open_document(data: dict) -> dict:
    """An opened document must name the file and its candidate identity."""
    if not isinstance(data, dict):
        raise ContractError("invalid_message", "Missing open manifest.")
    if not data.get("name") or not isinstance(data.get("name"), str):
        raise ContractError("invalid_message", "Open manifest lacks a name.")
    if not data.get("candidate_id"):
        raise ContractError("invalid_message", "Open manifest lacks identity.")
    return {"ok": True, "name": data["name"]}
