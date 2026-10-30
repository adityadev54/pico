"""Native search/transfer adapter. Aditya owns this module.

Folder-grant scoped: only files under explicitly granted roots are visible.
Grants are enforced here AND rechecked at transfer time. No unrestricted
paths ever leave this module; callers get candidate IDs + bounded metadata.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import uuid

MAX_CANDIDATES = 20
MAX_FILE_BYTES = 20 * 1024 * 1024
NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")


class NativeError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def granted_roots(grants: list[dict], access: str | None = None) -> list[Path]:
    """Usable roots, optionally filtered by access level (A10).

    Levels: read < write (write implies read). Legacy {path}-only grants
    count as read. access=None keeps the old behavior: every usable root.
    """
    roots = []
    for grant in grants or []:
        level = grant.get("access", "read")
        if access == "write" and level != "write":
            continue
        path = Path(str(grant.get("path", ""))).expanduser().resolve()
        if path.is_dir():
            roots.append(path)
    if roots:
        return roots
    if grants:
        # Explicit grants were given but none resolve: fail closed rather
        # than silently searching somewhere the user never approved.
        return []
    # Demo default: Documents only. Production requires explicit grants.
    docs = Path.home() / "Documents"
    if docs.is_dir():
        roots.append(docs.resolve())
    return roots


def candidate_id_for(path: Path) -> str:
    return str(uuid.uuid5(NAMESPACE, str(path.resolve())))


def digest_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(256 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def search_documents(query: str, grants: list[dict] | None = None) -> list[dict]:
    """Case-insensitive filename match under granted roots."""
    query = (query or "").strip().lower()
    if not query:
        raise NativeError("no_match", "Empty query.")
    roots = granted_roots(grants or [])
    if not roots:
        raise NativeError("permission_denied", "No folder access granted.")
    matches: list[dict] = []
    for root in roots:
        try:
            for dirpath, _, filenames in os.walk(root, followlinks=False):
                # Skip hidden dirs and packages.
                if "/." in dirpath.replace(str(root), ""):
                    continue
                for name in filenames:
                    if query in name.lower():
                        full = Path(dirpath) / name
                        if full.is_symlink():continue
                        try:
                            size = full.stat().st_size
                        except OSError:
                            continue
                        if size > MAX_FILE_BYTES:
                            continue
                        matches.append({
                            "candidate_id": candidate_id_for(full),
                            "name": name[:120],
                            "size_bytes": size,
                        })
                        if len(matches) >= MAX_CANDIDATES:
                            return sorted(matches, key=lambda c: c["name"].lower())
        except OSError:
            continue
    if not matches:
        raise NativeError("no_match", "No matching files.")
    return sorted(matches, key=lambda c: c["name"].lower())


def resolve_candidate(candidate_id: str, grants: list[dict] | None = None) -> Path:
    """Map candidate ID back to a path under current grants. Enforces grants."""
    roots = granted_roots(grants or [])
    for root in roots:
        for dirpath, _, filenames in os.walk(root, followlinks=False):
            for name in filenames:
                full = Path(dirpath) / name
                try:
                    if candidate_id_for(full) == candidate_id:
                        # Re-resolve to defeat symlink swaps.
                        resolved = full.resolve()
                        if any(resolved.is_relative_to(r) for r in roots):
                            return resolved
                except OSError:
                    continue
    raise NativeError("candidate_changed", "File is no longer available.")


def transfer_evidence(candidate_id: str, grants: list[dict] | None = None) -> dict:
    """Recheck exact file at transfer time. Returns size/digest evidence."""
    path = resolve_candidate(candidate_id, grants)
    try:
        size = path.stat().st_size
    except OSError:
        raise NativeError("candidate_changed", "File changed before transfer.") from None
    if size > MAX_FILE_BYTES:
        raise NativeError("permission_denied", "File too large.")
    return {
        "candidate_id": candidate_id,
        "name": path.name[:120],
        "size_bytes": size,
        "digest": digest_of(path),
    }


def read_excerpt(candidate_id: str, grants: list[dict] | None = None, limit: int = 4000) -> str:
    """Bounded text excerpt for summaries. Binary files return empty."""
    path = resolve_candidate(candidate_id, grants)
    try:
        raw = path.read_bytes()[:limit]
        return raw.decode("utf-8", errors="strict")[:limit]
    except (OSError, UnicodeError):
        return ""
