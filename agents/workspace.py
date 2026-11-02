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
from datetime import datetime, timezone
from pathlib import Path

from native_search import NativeError, digest_of

DEFAULT_READ_LIMIT = 64 * 1024
MAX_READ_LIMIT = 1024 * 1024
MAX_LIST_ENTRIES = 500
HISTORY_DIR = '.pico-history'
HISTORY_BACKUPS = 'backups'
JOURNAL_NAME = 'journal.jsonl'
JOURNAL_MAX_ENTRIES = 500
JOURNAL_PRUNE_TO = 400
HISTORY_BACKUP_BYTES = 1024 * 1024


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

    def trash(self, rel_path):
        """Move one file into .pico-trash with a sidecar manifest. Files
        only; the trash dir itself is never trashed. Same-filesystem
        atomic move; the original is gone only after the move lands."""
        import json as _json
        path = self.resolve(rel_path)
        try:
            inner = path.relative_to(self.root / '.pico-trash')
            raise NativeError('invalid_args', 'That is already in trash.')
        except ValueError:
            pass
        if not path.is_file() or path.is_symlink():
            raise NativeError('no_match', 'Only files can be trashed.')
        trash_dir = self.root / '.pico-trash'
        try:
            trash_dir.mkdir(exist_ok=True)
        except OSError:
            raise NativeError('permission_denied', 'Trash is unavailable.') from None
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
        dest = trash_dir / f'{stamp}_{path.name}'
        for n in range(2, 102):
            if not dest.exists() and not dest.with_suffix(dest.suffix + '.json').exists():
                break
            dest = trash_dir / f'{stamp}_{path.stem}_{n}{path.suffix}'
        else:
            raise NativeError('permission_denied', 'Trash is full for that name.')
        try:
            raw = path.read_bytes()
        except OSError:
            raise NativeError('no_match', 'Could not read that file.') from None
        manifest = {'original': str(path.relative_to(self.root)),
                    'trashed': dest.name, 'trashed_at': stamp,
                    'size_bytes': len(raw), 'digest': digest_bytes(raw)}
        try:
            os.replace(path, dest)
            dest.with_suffix(dest.suffix + '.json').write_text(_json.dumps(manifest))
        except OSError:
            raise NativeError('permission_denied', 'Could not trash that file.') from None
        return manifest

    def restore(self, name):
        """Bring back the latest trashed file matching a trash name or an
        original basename. Collisions at home gain a numeric suffix."""
        import json as _json
        trash_dir = self.root / '.pico-trash'
        if not trash_dir.is_dir():
            raise NativeError('no_match', 'Trash is empty.')
        matches = []
        for sidecar in sorted(trash_dir.glob('*.json')):
            try:
                manifest = _json.loads(sidecar.read_text())
            except (OSError, ValueError):
                continue
            if name not in (manifest.get('trashed'), Path(manifest.get('original', '')).name):
                continue
            target = trash_dir / str(manifest.get('trashed', ''))
            if target.is_file():
                matches.append((sidecar, target, manifest))
        if not matches:
            raise NativeError('no_match', 'Nothing trashed under that name.')
        sidecar, target, manifest = matches[-1]
        home = self.resolve(manifest.get('original', ''))
        if home.exists():
            for n in range(2, 102):
                candidate = home.parent / f'{home.stem}_{n}{home.suffix}'
                if not candidate.exists():
                    home = candidate
                    break
            else:
                raise NativeError('permission_denied', 'Home folder is full for that name.')
        try:
            os.replace(target, home)
            sidecar.unlink()
        except OSError:
            raise NativeError('permission_denied', 'Could not restore that file.') from None
        return {'path': str(home.relative_to(self.root)),
                'size_bytes': manifest.get('size_bytes'),
                'digest': manifest.get('digest')}

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
        existed = path.exists() or path.is_symlink()
        previous = None
        if existed:
            if base_revision is None:
                raise NativeError('candidate_changed',
                                  'File exists. Read it first, then revise with its revision.')
            try:
                previous = path.read_bytes()
            except OSError:
                raise NativeError('candidate_changed', 'File changed during write.') from None
            if digest_bytes(previous) != base_revision:
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
        manifest = {'path': str(Path(rel_path)), 'size_bytes': len(raw),
                    'digest': digest_bytes(raw)}
        try:
            if existed:
                self.note_revised(rel_path, manifest['digest'], previous)
            else:
                self.note_created(rel_path, manifest['digest'])
        except OSError:
            pass  # History is best-effort; the write itself succeeded.
        return manifest

    def _journal_rel(self, rel_path):
        """Normalize a journal path the way undo looks it up."""
        try:
            return str((self.root / rel_path).resolve().relative_to(self.root))
        except (OSError, ValueError):
            return str(Path(rel_path))

    def note_created(self, rel_path, digest):
        """Journal one Pico-created file so undo can remove it if untouched."""
        import json as _json
        history = self.root / HISTORY_DIR
        history.mkdir(exist_ok=True)
        entry = {'op': 'create', 'path': self._journal_rel(rel_path),
                 'digest': digest, 'backup': None,
                 'at': datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}
        with (history / JOURNAL_NAME).open('a') as stream:
            stream.write(_json.dumps(entry) + '\n')
        self._prune_journal()

    def note_revised(self, rel_path, digest, previous):
        """Journal one Pico revision with the previous bytes for undo.
        Previous versions over 1 MB are noted without a backup."""
        import json as _json
        import uuid as _uuid
        backup_rel = None
        if previous is not None and len(previous) <= HISTORY_BACKUP_BYTES:
            backups = self.root / HISTORY_DIR / HISTORY_BACKUPS
            backups.mkdir(parents=True, exist_ok=True)
            name = f'{_uuid.uuid4().hex[:12]}.bak'
            (backups / name).write_bytes(bytes(previous))
            backup_rel = f'{HISTORY_DIR}/{HISTORY_BACKUPS}/{name}'
        history = self.root / HISTORY_DIR
        history.mkdir(exist_ok=True)
        entry = {'op': 'revise', 'path': self._journal_rel(rel_path),
                 'digest': digest, 'backup': backup_rel,
                 'at': datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}
        with (history / JOURNAL_NAME).open('a') as stream:
            stream.write(_json.dumps(entry) + '\n')
        self._prune_journal()

    def _prune_journal(self):
        """Cap the journal; sweep backups nothing references anymore."""
        import json as _json
        journal = self.root / HISTORY_DIR / JOURNAL_NAME
        try:
            lines = journal.read_text().splitlines()
        except OSError:
            return
        if len(lines) <= JOURNAL_MAX_ENTRIES:
            return
        keep = lines[-JOURNAL_PRUNE_TO:]
        try:
            journal.write_text('\n'.join(keep) + ('\n' if keep else ''))
        except OSError:
            return
        referenced = set()
        for line in keep:
            try:
                backup = _json.loads(line).get('backup')
            except ValueError:
                continue
            if backup:
                referenced.add(backup)
        backups = self.root / HISTORY_DIR / HISTORY_BACKUPS
        try:
            children = list(backups.iterdir())
        except OSError:
            return
        for child in children:
            rel = f'{HISTORY_DIR}/{HISTORY_BACKUPS}/{child.name}'
            if child.is_file() and not child.is_symlink() and rel not in referenced:
                try:
                    child.unlink()
                except OSError:
                    continue

    def journal_entries(self):
        """Journal lines oldest-first as (line index, entry) pairs."""
        import json as _json
        journal = self.root / HISTORY_DIR / JOURNAL_NAME
        try:
            lines = journal.read_text().splitlines()
        except OSError:
            return []
        entries = []
        for index, line in enumerate(lines):
            try:
                entry = _json.loads(line)
            except ValueError:
                continue
            if isinstance(entry, dict) and entry.get('path'):
                entries.append((index, entry))
        return entries

    def forget_entry(self, index):
        """Drop one journal line and its backup, if still present."""
        import json as _json
        journal = self.root / HISTORY_DIR / JOURNAL_NAME
        lines = journal.read_text().splitlines()
        if not 0 <= index < len(lines):
            return
        try:
            backup = _json.loads(lines[index]).get('backup')
        except ValueError:
            backup = None
        remaining = lines[:index] + lines[index + 1:]
        journal.write_text('\n'.join(remaining) + ('\n' if remaining else ''))
        if backup:
            try:
                resolved = (self.root / backup).resolve()
            except OSError:
                return
            if resolved.is_relative_to(self.root) and resolved.is_file() \
                    and not resolved.is_symlink():
                try:
                    resolved.unlink()
                except OSError:
                    pass
