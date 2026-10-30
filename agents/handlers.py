"""Headless tool execution for the desktop helper (A06/A07).

Every handler takes validated (tool, args) plus an injected context and
returns (data, evidence) or raises NativeError/ToolError. tkinter never
loads here, so the whole layer runs under unit tests with fake side
effects. Companion.execute_tool validates, builds the context from live
objects, and queues the result.

Context keys: task_id, grants (folder list), transfer(raw, evidence),
open_url(url), reopen(bundle), notify(). Workspace tools use the first
granted root; multi-workspace selection is an A10 follow-up.
"""
from __future__ import annotations

import json
import os
import webbrowser

from native_search import (
    NativeError,
    candidate_id_for,
    digest_of,
    granted_roots,
    read_excerpt,
    resolve_candidate,
    search_documents,
    transfer_evidence,
)
from runner import run as run_process
from tools import ToolError
from workspace import Workspace

APP_BUNDLES = {'calculator': 'com.apple.Calculator', 'calendar': 'com.apple.iCal',
               'vscode': 'com.microsoft.VSCode', 'browser': 'com.apple.Safari',
               'notes': 'com.apple.Notes'}

MAX_TRANSFER_BYTES = 1024 * 1024
MAIL_JSON_LIMIT = 2000


def bounded_json(data, limit=MAIL_JSON_LIMIT):
    """Encode data as JSON that always fits the mailbox and always parses.

    Oversized payloads shrink (longest strings and lists first) and gain a
    truncation marker instead of being sliced mid-string into garbage.
    """
    raw = json.dumps(data)
    if len(raw) <= limit:
        return raw
    cut = dict(data) if isinstance(data, dict) else {'items': data}
    for _ in range(4):
        shrunk = False
        for key, value in list(cut.items()):
            if isinstance(value, str) and len(value) > 64:
                cut[key] = value[: len(value) // 2]
                shrunk = True
            elif isinstance(value, list) and len(value) > 1:
                cut[key] = value[: max(1, len(value) // 2)]
                shrunk = True
        raw = json.dumps({**cut, 'truncated': True})
        if len(raw) <= limit or not shrunk:
            return raw if len(raw) <= limit else json.dumps({'truncated': True})
    return json.dumps({'truncated': True})


def search_documents_handler(args, ctx):
    candidates = search_documents(args['query'], ctx.get('grants') or [])
    for candidate in candidates:
        try:
            path = resolve_candidate(candidate['candidate_id'], ctx.get('grants') or [])
            if path.stat().st_size <= MAX_TRANSFER_BYTES:
                candidate['digest'] = digest_of(path)
        except Exception:
            pass  # Enrichment is best-effort; the candidate itself still stands.
    return ({'candidates': candidates},
            {'grant_count': len(granted_roots(ctx.get('grants') or []))})


def transfer_selected_file_handler(args, ctx):
    grants = ctx.get('grants') or []
    evidence = transfer_evidence(args['candidate_id'], grants)
    path = resolve_candidate(args['candidate_id'], grants)
    raw = path.read_bytes()
    if len(raw) > MAX_TRANSFER_BYTES:
        raise NativeError('permission_denied', 'File too large.')
    ctx['transfer'](raw, evidence)
    try:
        excerpt = raw[:4000].decode('utf-8')[:1500]
    except UnicodeError:
        excerpt = ''
    return ({'name': evidence['name'], 'excerpt': excerpt}, evidence)


def read_back_file_handler(args, ctx):
    grants = ctx.get('grants') or []
    evidence = transfer_evidence(args['candidate_id'], grants)
    excerpt = read_excerpt(args['candidate_id'], grants)
    return ({'excerpt': excerpt[:1500], 'name': evidence['name']}, evidence)


def open_website_handler(args, ctx):
    url = args['url']
    (ctx.get('open_url') or webbrowser.open)(url)
    return ({'url': url[:200]}, {})


def open_app_handler(args, ctx):
    bundle = APP_BUNDLES.get(args['app'])
    if bundle is None:
        raise NativeError('unsupported_tool', 'Unknown app.')
    ctx['reopen'](bundle)
    return ({'app': args['app']}, {})


def manage_permissions_handler(args, ctx):
    ctx['notify']()
    return ({}, {})


def _workspace(ctx, access='read'):
    roots = granted_roots(ctx.get('grants') or [], access=access)
    if not roots:
        level = 'write' if access == 'write' else 'folder'
        raise NativeError('permission_denied', f'No {level} access granted.')
    return Workspace(roots[0])


def fs_list_handler(args, ctx):
    entries = _workspace(ctx).list(args.get('path') or '.')
    return ({'entries': entries}, {})


def fs_read_handler(args, ctx):
    manifest = _workspace(ctx).read(args['path'])
    data = dict(manifest)
    evidence = {'digest': manifest['digest'], 'size_bytes': manifest['size_bytes']}
    return (data, evidence)


def fs_write_handler(args, ctx):
    manifest = _workspace(ctx, 'write').write(args['path'], args['content'],
                                              args.get('base_revision'))
    return (manifest, {'digest': manifest['digest']})


PHOTO_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.heic', '.heif', '.webp',
                    '.gif', '.bmp', '.tif', '.tiff')
ORGANIZE_COPY_CAP = 2000


def organize_photos_handler(args, ctx):
    """Copy-only photo triage (B02 slice): gather images under the granted
    root, skip byte-identical duplicates by hash, and copy one of each
    into a single folder. Originals are never moved, renamed or deleted;
    same-name collisions gain a numeric suffix instead of overwriting."""
    import hashlib
    import shutil
    from pathlib import Path as _Path
    folder = args['folder']
    if '/' in folder or '\\' in folder or folder.startswith('.'):
        raise ToolError('invalid_args', 'Use a single folder name.')
    workspace = _workspace(ctx, 'write')
    target = workspace.resolve(folder)
    if target.exists() and not target.is_dir():
        raise ToolError('invalid_args', 'A file blocks that folder name.')
    target.mkdir(exist_ok=True)
    already = {}
    try:
        entries = sorted(target.iterdir())[:5001]
    except OSError:
        entries = []
    if len(entries) <= 5000:
        for child in entries:
            if not child.is_file() or child.is_symlink():
                continue
            try:
                already.setdefault(
                    digest_of(child), child.name)
            except OSError:
                pass
    found = []
    for dirpath, dirnames, filenames in os.walk(workspace.root):
        here = _Path(dirpath)
        dirnames[:] = [d for d in dirnames
                       if not d.startswith('.')
                       and (here / d).resolve() != target]
        dirnames[:] = [d for d in dirnames if not (here/d).is_symlink()]
        for filename in filenames:
            if filename.startswith('.'):
                continue
            if _Path(filename).suffix.lower() not in PHOTO_EXTENSIONS:
                continue
            candidate = here / filename
            if candidate.is_symlink():
                continue
            found.append(candidate)
    found.sort()
    seen, copied, unreadable, truncated = set(), [], 0, False
    duplicates = 0
    for candidate in found:
        if ctx.get('cancelled',lambda:False)():raise NativeError('cancelled','Photo copying cancelled. Completed copies are retained.')
        try:
            digest = digest_of(candidate)
        except OSError:
            unreadable += 1
            continue
        if digest in seen or digest in already:
            duplicates += 1
            continue
        if len(copied) >= ORGANIZE_COPY_CAP:
            truncated = True
            continue
        seen.add(digest)
        dest = target / candidate.name
        if dest.exists():
            stem, suffix = candidate.stem, candidate.suffix
            for n in range(2, 102):
                dest = target / f'{stem}_{n}{suffix}'
                if not dest.exists():
                    break
            else:
                unreadable += 1
                continue
        try:
            shutil.copyfile(candidate, dest)
        except OSError:
            unreadable += 1
            continue
        already[digest] = dest.name
        copied.append(dest.name)
    data = {'folder': folder, 'copied_count': len(copied),
            'duplicates_skipped': duplicates, 'found': len(found),
            'unreadable': unreadable, 'truncated': truncated,
            'copied': copied[:50]}
    return (data, {'count': len(copied)})


DOCUMENT_TYPES = (
    ('word document', ('.doc', '.docx', '.odt', '.rtf')),
    ('slide deck', ('.ppt', '.pptx', '.odp', '.key')),
    ('text file', ('.txt', '.md', '.rst')),
    ('spreadsheet', ('.xls', '.xlsx', '.csv', '.ods')),
    ('presentation', ('.ppt', '.pptx', '.odp', '.key')),
    ('document', ('.doc', '.docx', '.odt', '.rtf', '.pdf', '.txt', '.md')),
    ('picture', PHOTO_EXTENSIONS),
    ('image', PHOTO_EXTENSIONS),
    ('photo', PHOTO_EXTENSIONS),
    ('pdf', ('.pdf',)),
)


def default_open_file(path):
    """Open one path with the OS default app. No shell, fire-and-forget."""
    import subprocess
    import sys
    if sys.platform == 'darwin':
        subprocess.Popen(['open', path])
    elif sys.platform == 'win32':
        os.startfile(path)  # noqa: PGH100 (desktop-only helper)
    else:
        subprocess.Popen(['xdg-open', path])


def open_document_handler(args, ctx):
    """Open one document by name and/or file type ('quarterly report',
    'a word document', 'the trip spreadsheet'). Opens only on a unique
    match; zero or several matches fail honestly instead of guessing."""
    import re
    from pathlib import Path as _Path
    query = re.sub(r'^(?:the|my|a|an)\s+', '', (args['query'] or '').strip(),
                   flags=re.IGNORECASE).strip().lower()
    if not query:
        raise ToolError('invalid_args', 'Name a document to open.')
    extensions, remainder = None, query
    for phrase, exts in DOCUMENT_TYPES:
        if query == phrase or query.endswith(' ' + phrase):
            extensions, remainder = exts, query[: -len(phrase)].strip()
            remainder = re.sub(r'^(?:the|my|a|an)\s+', '', remainder).strip()
            break
    grants = ctx.get('grants') or []
    roots = granted_roots(grants)
    if not roots:
        raise NativeError('permission_denied', 'No folder access granted.')
    matches = []
    for root in roots:
        try:
            for dirpath, _, filenames in os.walk(root, followlinks=False):
                if '/.' in dirpath.replace(str(root), ''):
                    continue
                for name in filenames:
                    if extensions and _Path(name).suffix.lower() not in extensions:
                        continue
                    if remainder and remainder not in name.lower():
                        continue
                    full = _Path(dirpath) / name
                    try:
                        size = full.stat().st_size
                    except OSError:
                        continue
                    matches.append({'candidate_id': candidate_id_for(full),
                                    'name': name[:120], 'size_bytes': size})
        except OSError:
            continue
    matches.sort(key=lambda c: c['name'].lower())
    if len(matches) != 1:
        sample = ', '.join(m['name'] for m in matches[:5])
        detail = f'Found {len(matches)} matches' + (f' ({sample})' if sample else '')
        raise NativeError('no_match', detail + '; be more specific.')
    path = resolve_candidate(matches[0]['candidate_id'], grants)
    if ctx.get('connected') and path.suffix.lower() not in ('.txt','.md','.pdf','.docx','.xlsx','.pptx','.csv','.png','.jpg'):
        raise NativeError('permission_denied','Only document and image types can be opened in this workflow.')
    (ctx.get('open_file') or default_open_file)(str(path))
    return ({'name': path.name[:120],
             'candidate_id': matches[0]['candidate_id']},
            {'candidate_id': matches[0]['candidate_id']})


def fetch_upload_handler(args, ctx):
    """Save one phone upload (B07): fetch by artifact digest, verify the
    bytes hash to the artifact id, then atomic-write into the workspace.
    A resumed upload over identical bytes succeeds without duplicating;
    different bytes under the same name fail instead of overwriting."""
    import hashlib
    import re
    artifact_id = args['artifact_id']
    if not re.fullmatch(r'[0-9a-f]{64}', artifact_id or ''):
        raise ToolError('invalid_args', 'Invalid artifact reference.')
    fetch = ctx.get('fetch_artifact')
    if fetch is None:
        raise ToolError('device_offline', 'Upload fetch is not connected.')
    raw = fetch(artifact_id)
    if not isinstance(raw, (bytes, bytearray)) or not raw:
        raise ToolError('invalid_message', 'Upload arrived empty.')
    if hashlib.sha256(bytes(raw)).hexdigest() != artifact_id:
        raise ToolError('candidate_changed', 'Upload changed in transit.')
    workspace = _workspace(ctx, 'write')
    try:
        manifest = workspace.write_bytes(args['path'], bytes(raw))
    except NativeError as error:
        if error.code != 'candidate_changed':
            raise
        existing = workspace.read(args['path'])
        if existing['digest'] != artifact_id:
            raise
        manifest = dict(existing, duplicate=True)
    return (manifest, {'digest': manifest['digest']})


def process_run_handler(args, ctx):
    try:
        argv = json.loads(args['argv_json'])
    except ValueError:
        raise ToolError('invalid_args', 'argv_json must be a JSON list.') from None
    if not isinstance(argv, list) or not argv or any(
            not isinstance(a, str) or not a for a in argv):
        raise ToolError('invalid_args', 'argv_json must be a non-empty string list.')
    # Processes run as the user and can write, so they need write access.
    workspace = _workspace(ctx, 'write')
    cwd = str(workspace.resolve(args.get('cwd') or '.'))
    timeout = args.get('timeout_s')
    if 'register_cancel' in ctx:
        from runner import start as start_process
        handle = start_process(argv, cwd=cwd, timeout=timeout)
        ctx['register_cancel'](handle.cancel)
        try:
            return (handle.wait(timeout=handle.timeout), {})
        finally:
            ctx['unregister_cancel']()
    result = run_process(argv, cwd=cwd, timeout=timeout)
    return (result, {})


def register_running(running, cancelled, task_id, fn):
    """Track a live cancel hook; run it at once if already cancelled."""
    if task_id in cancelled:
        fn()
    running[task_id] = fn


def unregister_running(running, task_id):
    running.pop(task_id, None)


def note_cancelled(cancelled, running, task_id):
    """Record a cancel signal; return the live hook, if the work is running."""
    if task_id not in cancelled:
        cancelled.append(task_id)
    del cancelled[:-200]
    return running.pop(task_id, None)


HANDLERS = {
    'search_documents': search_documents_handler,
    'transfer_selected_file': transfer_selected_file_handler,
    'read_back_file': read_back_file_handler,
    'open_website': open_website_handler,
    'open_app': open_app_handler,
    'manage_permissions': manage_permissions_handler,
    'fs_list': fs_list_handler,
    'fs_read': fs_read_handler,
    'fs_write': fs_write_handler,
    'process_run': process_run_handler,
    'fetch_upload': fetch_upload_handler,
    'organize_photos': organize_photos_handler,
    'open_document': open_document_handler,
}


def dispatch(tool, args, ctx):
    handler = HANDLERS.get(tool)
    if handler is None:
        raise ToolError('unsupported_tool', f'Unsupported tool: {tool}.')
    return handler(args, ctx)
