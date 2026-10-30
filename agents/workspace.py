"""Workspace-scoped file operations for the desktop helper (A07).

A Workspace binds all reads/writes/listings to one granted root directory.
Callers pass RELATIVE paths; every operation resolves symlinks first and
then enforces containment, so `..` escapes and absolute paths fail closed.
Writes are atomic (temp file + rename) and revision-checked: creates must
target a missing path, revisions must present the current content digest.
The existing file is always preserved on failure.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from native_search import NativeError, digest_of

DEFAULT_READ_LIMIT = 64 * 1024
MAX_READ_LIMIT = 1024 * 1024
MAX_LIST_ENTRIES = 500


def digest_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class Workspace:
    def __init__(self, root):
        resolved = Path(root).expanduser().resolve()
        if not resolved.is_dir():
            raise NativeError('permission_denied', 'Workspace is not available.')
        self.root = resolved

    def resolve(self, rel_path):
        """Map a relative path to an absolute path inside the workspace."""
        text = str(rel_path or '')
        if not text or '\x00' in text or Path(text).is_absolute():
            raise NativeError('permission_denied', 'Path must be relative.')
        target = (self.root / text).resolve()
        if target != self.root and not target.is_relative_to(self.root):
            raise NativeError('permission_denied', 'Path escapes the workspace.')
        return target

    def list(self, rel_dir='.'):
        """List one directory: [{name, type, size_bytes}], sorted, bounded."""
        directory = self.resolve(rel_dir)
        if not directory.is_dir():
            raise NativeError('no_match', 'Folder not found.')
        entries = []
        for child in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
            try:
                if child.is_symlink() or child.is_file():
                    kind = 'file'
                elif child.is_dir():
                    kind = 'dir'
                else:
                    continue
                size = child.stat().st_size if kind == 'file' else 0
            except OSError:
                continue
            entries.append({'name': child.name, 'type': kind, 'size_bytes': size})
            if len(entries) >= MAX_LIST_ENTRIES:
                break
        return entries

    def read(self, rel_path, limit=DEFAULT_READ_LIMIT):
        """Read a file. Text decodes as UTF-8; binary returns a manifest."""
        path = self.resolve(rel_path)
        try:
            size = path.stat().st_size
            with path.open('rb') as stream:
                raw = stream.read(min(int(limit), MAX_READ_LIMIT))
        except OSError:
            raise NativeError('no_match', 'File not found.') from None
        manifest = {'path': str(Path(rel_path)), 'size_bytes': size,
                    'digest': digest_of(path)}
        try:
            text = raw.decode('utf-8')
        except UnicodeError:
            manifest['binary'] = True
            return manifest
        manifest['content'] = text
        manifest['truncated'] = size > len(raw)
        return manifest

    def write(self, rel_path, content, base_revision=None):
        """Create a missing file, or revise one presenting its digest.

        Creates fail if the path exists; revisions fail unless
        base_revision matches the current content digest. Either way the
        pre-existing bytes are untouched on failure.
        """
        if not isinstance(content, str):
            raise NativeError('invalid_args', 'Content must be text.')
        return self.write_bytes(rel_path, content.encode('utf-8'),
                                base_revision)

    def write_bytes(self, rel_path, raw, base_revision=None):
        """Binary twin of write(): same create-or-revision rules, same
        atomic rename, same untouched-on-failure guarantee."""
        if not isinstance(raw, (bytes, bytearray)):
            raise NativeError('invalid_args', 'Content must be bytes.')
        raw = bytes(raw)
        path = self.resolve(rel_path)
        if len(raw) > MAX_READ_LIMIT:
            raise NativeError('permission_denied', 'Content too large.')
        if not path.parent.is_dir():
            raise NativeError('no_match', 'Parent folder not found.')
        if path.exists() or path.is_symlink():
            if base_revision is None:
                raise NativeError('candidate_changed',
                                  'File exists. Read it first, then revise with its revision.')
            try:
                current = digest_bytes(path.read_bytes())
            except OSError:
                raise NativeError('candidate_changed', 'File changed during write.') from None
            if current != base_revision:
                raise NativeError('candidate_changed',
                                  'File changed since read. Your newer version is preserved.')
        elif base_revision is not None:
            raise NativeError('no_match', 'Nothing to revise; file does not exist.')
        tmp = path.with_name(f'.{path.name}.{os.getpid()}.tmp')
        try:
            tmp.write_bytes(raw)
            os.replace(tmp, path)
        except OSError:
            raise NativeError('permission_denied', 'Could not save the file.') from None
        finally:
            tmp.unlink(missing_ok=True)
        return {'path': str(Path(rel_path)), 'size_bytes': len(raw),
                'digest': digest_bytes(raw)}
