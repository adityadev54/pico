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
               'notes': 'com.apple.Notes', 'chrome': 'com.google.Chrome',
               'safari': 'com.apple.Safari', 'firefox': 'org.mozilla.firefox',
               'edge': 'com.microsoft.Edge', 'files': 'com.apple.finder',
               'terminal': 'com.apple.Terminal', 'mail': 'com.apple.mail',
               'photos': 'com.apple.Photos', 'music': 'com.apple.Music',
               'messages': 'com.apple.iChat', 'facetime': 'com.apple.FaceTime',
               'maps': 'com.apple.Maps', 'settings': 'com.apple.systempreferences',
               'appstore': 'com.apple.AppStore', 'word': 'com.microsoft.Word',
               'excel': 'com.microsoft.Excel', 'powerpoint': 'com.microsoft.Powerpoint'}

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
        level = {'write': 'write', 'delete': 'delete'}.get(access, 'folder')
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
    scan_roots = granted_roots(ctx.get('grants') or []) or [workspace.root]
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
    for scan_root in scan_roots:
        for dirpath, dirnames, filenames in os.walk(scan_root):
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
    ('video', ('.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v')),
    ('movie', ('.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v')),
    ('audio', ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac')),
    ('song', ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac')),
    ('archive', ('.zip', '.tar', '.gz', '.tgz', '.rar', '.7z', '.dmg')),
    ('zip', ('.zip',)),
    ('ebook', ('.epub', '.mobi', '.azw3', '.pdf')),
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


CONVERT_TARGETS = ('pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg', 'webp')
CONVERT_IMAGES = ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp',
                  '.tif', '.tiff')
CONVERT_LIMIT = 64 * 1024 * 1024


def _need_module(name, setup):
    import importlib
    try:
        return importlib.import_module(name)
    except ImportError:
        raise ToolError('unsupported_tool', setup) from None


def delete_files_handler(args, ctx):
    """Trash one file (recoverable): needs a delete grant on the root
    plus an explicit DELETE confirmation. Nothing is ever removed
    permanently; see restore_deleted."""
    if args.get('confirm') != 'DELETE':
        raise ToolError('invalid_args', 'Deletion needs an explicit DELETE confirmation.')
    manifest = _workspace(ctx, 'delete').trash(args['path'])
    data = {'trashed_count': 1, 'trashed': [manifest['original']],
            'digest': manifest['digest']}
    return (data, {'count': 1})


def restore_deleted_handler(args, ctx):
    manifest = _workspace(ctx, 'write').restore(args['name'])
    data = {'restored': manifest['path'], 'size_bytes': manifest['size_bytes'],
            'digest': manifest['digest']}
    return (data, {'digest': manifest['digest'] or ''})


def convert_file_handler(args, ctx):
    """Convert one file between supported forms (D03-D07 slice): images
    to PDF or another image form, PDF text to TXT/DOCX (text only),
    DOCX to PDF via LibreOffice. Missing engines fail with the exact
    setup line; outputs never overwrite (numeric suffix instead)."""
    to = str(args['to'] or '').lower().lstrip('.')
    if to == 'jpeg':
        to = 'jpg'
    if to not in CONVERT_TARGETS:
        raise ToolError(
            'invalid_args',
            'Supported conversions: images to pdf/png/jpg/webp, '
            'pdf to txt/docx (text only), docx to pdf.')
    workspace = _workspace(ctx, 'write')
    try:
        src = workspace.resolve(args['path'])
    except NativeError:
        raise NativeError('no_match', 'Nothing to convert.') from None
    if not src.is_file() or src.is_symlink():
        raise NativeError('no_match', 'Nothing to convert.')
    from_ext = src.suffix.lower()
    if from_ext == '.' + to or (from_ext in ('.jpg', '.jpeg') and to == 'jpg'):
        raise ToolError('invalid_args', 'That file is already .' + to + '.')
    try:
        if src.stat().st_size > CONVERT_LIMIT:
            raise ToolError('invalid_args', 'File is larger than 64 MB.')
        raw = src.read_bytes()
    except OSError:
        raise NativeError('no_match', 'Could not read that file.') from None
    out = _convert_bytes(raw, from_ext, to, src.stem)
    dest = src.parent / (src.stem[:100] + '.' + to)
    if dest.exists():
        for n in range(2, 102):
            candidate = src.parent / f'{src.stem[:100]}_{n}.{to}'
            if not candidate.exists():
                dest = candidate
                break
        else:
            raise ToolError('invalid_args', 'Too many converted copies here.')
    rel = dest.relative_to(workspace.root)
    manifest = workspace.write_bytes(str(rel), out)
    return (manifest, {'digest': manifest['digest']})


def _convert_bytes(raw, from_ext, to, stem):
    import io
    if from_ext in CONVERT_IMAGES and to in ('pdf', 'png', 'jpg', 'webp'):
        pil = _need_module('PIL.Image', 'pip install pillow')
        try:
            image = pil.open(io.BytesIO(raw))
            image.load()
        except Exception:
            raise ToolError('invalid_args', 'That image is unreadable.') from None
        buf = io.BytesIO()
        if to == 'pdf':
            image.convert('RGB').save(buf, 'PDF')
        else:
            fmt = 'JPEG' if to == 'jpg' else to.upper()
            converted = image.convert('RGB') if fmt == 'JPEG' else image
            converted.save(buf, fmt)
        return buf.getvalue()
    if from_ext == '.pdf' and to in ('txt', 'docx'):
        pypdf = _need_module('pypdf', 'pip install pypdf')
        try:
            reader = pypdf.PdfReader(io.BytesIO(raw))
            text = '\n'.join((page.extract_text() or '') for page in reader.pages)
        except Exception:
            raise ToolError('invalid_args', 'That PDF is unreadable.') from None
        if to == 'txt':
            return text.encode('utf-8')
        docx = _need_module('docx', 'pip install python-docx')
        document = docx.Document()
        for para in text.split('\n'):
            document.add_paragraph(para)
        buf = io.BytesIO()
        document.save(buf)
        return buf.getvalue()
    if from_ext == '.docx' and to == 'pdf':
        import shutil
        import subprocess
        import tempfile
        from pathlib import Path as _Path
        if not shutil.which('soffice'):
            raise ToolError(
                'unsupported_tool',
                'install LibreOffice (soffice on PATH) for Word to PDF')
        with tempfile.TemporaryDirectory(prefix='pico-docx2pdf-') as tmp:
            src = _Path(tmp) / (stem[:60] + '.docx')
            src.write_bytes(raw)
            try:
                proc = subprocess.run(
                    ['soffice', '--headless', '--convert-to', 'pdf',
                     '--outdir', tmp, str(src)],
                    capture_output=True, timeout=120)
            except (OSError, subprocess.TimeoutExpired):
                raise ToolError('timeout', 'Word to PDF took too long.') from None
            made = list(_Path(tmp).glob('*.pdf'))
            if proc.returncode != 0 or not made:
                raise ToolError('invalid_args', 'Word to PDF failed.')
            return made[0].read_bytes()
    raise ToolError(
        'invalid_args',
        'Supported conversions: images to pdf/png/jpg/webp, '
        'pdf to txt/docx (text only), docx to pdf.')


PDF_IMAGES_LIMIT = 50


def _parse_page_spec(spec, count):
    """'1-3,5' -> sorted unique 0-based indices against a page count."""
    picked = set()
    for chunk in (spec or '').split(','):
        chunk = chunk.strip()
        if not chunk:
            continue
        if '-' in chunk:
            start_s, end_s = chunk.split('-', 1)
            try:
                start, end = int(start_s.strip()), int(end_s.strip())
            except ValueError:
                raise ToolError('invalid_args', 'Pages look like "1-3,5".') from None
            if start < 1 or end < start:
                raise ToolError('invalid_args', 'Pages look like "1-3,5".')
            picked.update(range(start - 1, end))
        else:
            try:
                num = int(chunk)
            except ValueError:
                raise ToolError('invalid_args', 'Pages look like "1-3,5".') from None
            if num < 1:
                raise ToolError('invalid_args', 'Pages look like "1-3,5".')
            picked.add(num - 1)
    if not picked:
        raise ToolError('invalid_args', 'Name at least one page.')
    if max(picked) >= count:
        raise ToolError('invalid_args',
                        f'That PDF has {count} pages; page {max(picked) + 1} is out of range.')
    return sorted(picked)


def _watermark_overlay_pdf(text, width, height):
    """One-page PDF with diagonal gray text, correct xref, no dependencies."""
    safe = ''.join(c for c in text if 32 <= ord(c) < 127).strip()[:64]
    if not safe:
        raise ToolError('invalid_args', 'Watermark text cannot be empty.')
    safe = safe.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    content = (f'BT /F1 48 Tf 0.72 g 33.9 33.9 -33.9 33.9 '
               f'{width / 2 - 120:.1f} {height / 2:.1f} Tm ({safe}) Tj ET')
    content_bytes = content.encode('ascii')
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        (f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width:.1f} {height:.1f}] '
         '/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>').encode('ascii'),
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>',
        b'<< /Length %d >>\nstream\n' % len(content_bytes) + content_bytes + b'\nendstream',
    ]
    out, offsets = bytearray(b'%PDF-1.4\n'), []
    for num, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b'%d 0 obj\n' % num + body + b'\nendobj\n'
    xref_at = len(out)
    out += b'xref\n0 6\n0000000000 65535 f \n'
    for offset in offsets:
        out += b'%010d 00000 n \n' % offset
    out += (b'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % xref_at)
    return bytes(out)


def _numbered_dest(parent, stem, suffix):
    dest = parent / f'{stem[:100]}.{suffix}'
    if not dest.exists():
        return dest
    for n in range(2, 102):
        candidate = parent / f'{stem[:100]}_{n}.{suffix}'
        if not candidate.exists():
            return candidate
    raise ToolError('invalid_args', 'Too many copies here already.')


def pdf_pages_handler(args, ctx):
    """Edit PDF pages (D06 + extras): merge, split, rotate, delete,
    watermark, unlock or rasterize. Locked inputs are refused except by
    unlock; outputs never overwrite; originals are never modified."""
    import io
    import json as _json
    pypdf = _need_module('pypdf', 'pip install pypdf')
    action = args['action']
    try:
        raw_paths = _json.loads(args['paths_json'])
    except (ValueError, TypeError):
        raise ToolError('invalid_args', 'Name the PDF files to use.') from None
    if not isinstance(raw_paths, list) or not raw_paths:
        raise ToolError('invalid_args', 'Name the PDF files to use.')
    if action in ('split', 'rotate', 'delete', 'watermark', 'unlock', 'images'):
        if len(raw_paths) != 1:
            raise ToolError('invalid_args', f'{action} takes one PDF.')
    if action == 'merge' and len(raw_paths) < 2:
        raise ToolError('invalid_args', 'Merging needs at least two PDFs.')
    workspace = _workspace(ctx, 'write')
    resolved = []
    for entry in raw_paths:
        if not isinstance(entry, str) or not entry.strip():
            raise ToolError('invalid_args', 'Name the PDF files to use.')
        try:
            path = workspace.resolve(entry.strip())
        except NativeError:
            raise ToolError('invalid_args', f'No file named {entry}.') from None
        if not path.is_file() or path.is_symlink():
            raise ToolError('invalid_args', f'No file named {entry}.')
        if path.suffix.lower() != '.pdf':
            raise ToolError('invalid_args', f'{entry} is not a PDF.')
        resolved.append(path)
    try:
        readers = []
        streams = []
        for path in resolved:
            stream = path.open('rb')
            streams.append(stream)
            reader = pypdf.PdfReader(stream)
            if reader.is_encrypted and action != 'unlock':
                raise ToolError('invalid_args', f'{path.name} is locked. Unlock it first.')
            readers.append(reader)
        if action == 'unlock':
            reader = readers[0]
            if not reader.is_encrypted:
                raise ToolError('invalid_args', 'That PDF is not locked.')
            if not args.get('password') or reader.decrypt(args['password']) == 0:
                raise ToolError('invalid_args', 'Wrong password for that PDF.')
            writer = pypdf.PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            return _write_pdf_result(writer, workspace, resolved[0], 'unlocked')
        if action == 'merge':
            writer = pypdf.PdfWriter()
            for reader in readers:
                for page in reader.pages:
                    writer.add_page(page)
            name = args.get('output') or f'{resolved[0].stem}_merged'
            return _write_pdf_result(writer, workspace, resolved[0], None, name)
        if action == 'images':
            return _pdf_to_images(resolved[0], workspace)
        reader = readers[0]
        count = len(reader.pages)
        if action == 'split':
            picked = _parse_page_spec(args.get('pages'), count)
            writer = pypdf.PdfWriter()
            for index in picked:
                writer.add_page(reader.pages[index])
            return _write_pdf_result(writer, workspace, resolved[0], 'extract')
        if action == 'rotate':
            if args.get('angle') not in (90, 180, 270):
                raise ToolError('invalid_args', 'Rotation must be 90, 180 or 270 degrees.')
            writer = pypdf.PdfWriter()
            for page in reader.pages:
                page.rotate(args['angle'])
                writer.add_page(page)
            return _write_pdf_result(writer, workspace, resolved[0], 'rotated')
        if action == 'delete':
            picked = set(_parse_page_spec(args.get('pages'), count))
            if len(picked) >= count:
                raise ToolError('invalid_args', 'That would delete every page.')
            writer = pypdf.PdfWriter()
            for index, page in enumerate(reader.pages):
                if index not in picked:
                    writer.add_page(page)
            return _write_pdf_result(writer, workspace, resolved[0], 'edited')
        if action == 'watermark':
            if not (args.get('text') or '').strip():
                raise ToolError('invalid_args', 'Watermark text cannot be empty.')
            writer = pypdf.PdfWriter()
            overlays = {}
            for page in reader.pages:
                box = page.mediabox
                key = (round(float(box.width), 1), round(float(box.height), 1))
                if key not in overlays:
                    stamp = _watermark_overlay_pdf(args['text'], key[0], key[1])
                    overlays[key] = pypdf.PdfReader(io.BytesIO(stamp)).pages[0]
                page.merge_page(overlays[key])
                writer.add_page(page)
            return _write_pdf_result(writer, workspace, resolved[0], 'watermarked')
        raise ToolError('invalid_args', f'Unknown PDF action: {action}.')
    finally:
        for stream in streams:
            stream.close()


def _write_pdf_result(writer, workspace, first, tag, name=None):
    import io
    buf = io.BytesIO()
    writer.write(buf)
    stem = (name or f'{first.stem}_{tag}')[:100]
    if stem.lower().endswith('.pdf'):
        stem = stem[:-4]
    dest = _numbered_dest(first.parent, stem, 'pdf')
    try:
        rel = dest.resolve().relative_to(workspace.root.resolve())
    except ValueError:
        raise ToolError('invalid_args', 'Output stays inside the workspace.') from None
    manifest = workspace.write_bytes(str(rel), buf.getvalue())
    return ({'output': dest.name, 'pages': len(writer.pages)},
            {'digest': manifest['digest']})


def _pdf_to_images(first, workspace):
    import shutil
    import subprocess
    if not shutil.which('pdftoppm'):
        raise ToolError('unsupported_tool',
                        'PDF to images needs poppler: brew install poppler')
    from pypdf import PdfReader
    with first.open('rb') as stream:
        count = len(PdfReader(stream).pages)
    if count > PDF_IMAGES_LIMIT:
        raise ToolError('invalid_args',
                        f'That PDF has {count} pages; image export covers up to {PDF_IMAGES_LIMIT}. Split it first.')
    prefix = first.parent / f'{first.stem[:80]}-page'
    prior = set(first.parent.glob(f'{prefix.name}-*.png'))
    try:
        proc = subprocess.run(['pdftoppm', '-png', '-r', '150', str(first), str(prefix)],
                              capture_output=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        raise ToolError('timeout', 'Image export took too long.') from None
    made = sorted(set(first.parent.glob(f'{prefix.name}-*.png')) - prior)
    if proc.returncode != 0 or not made:
        raise ToolError('invalid_args', 'Image export failed.')
    names = []
    for path in made:
        path.relative_to(workspace.root)
        names.append(path.name)
    return ({'outputs': names, 'pages': len(names)}, {})


def open_document_handler(args, ctx):
    """Open one file or folder by name ('quarterly report', 'syllabus pdf',
    'a video', 'the trip photos folder'). Any file type opens with its
    default app. Opens only on a unique match; zero or several matches
    fail honestly instead of guessing."""
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
    folder_query = re.sub(r'\s+(?:folders?|directory|directories)$', '',
                          remainder).strip()
    matches = []
    for root in roots:
        try:
            for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
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
                if extensions is None and folder_query:
                    for name in dirnames:
                        if name.startswith('.'):
                            continue
                        if folder_query not in name.lower():
                            continue
                        full = _Path(dirpath) / name
                        matches.append({'candidate_id': candidate_id_for(full),
                                        'name': name[:120], 'size_bytes': 0})
        except OSError:
            continue
    matches.sort(key=lambda c: c['name'].lower())
    if len(matches) > 1:
        sample = ', '.join(m['name'] for m in matches[:5])
        raise NativeError('no_match',
                          f'Which one? I found {len(matches)}: {sample}. Reply with the exact file name.')
    if not matches:
        raise NativeError('no_match',
                          f'I could not find anything matching "{args["query"][:80]}". Check the name and try again.')
    path = resolve_candidate(matches[0]['candidate_id'], grants)
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


def _clean_rel_list(raw_json, limit=50):
    """Parse a JSON list of workspace-relative paths.

    Refuses absolute paths, escapes, hidden parts, and empties so opaque
    JSON arguments cannot reach Pico-managed folders either.
    """
    from pathlib import Path as _Path
    try:
        entries = json.loads(raw_json)
    except (ValueError, TypeError):
        raise ToolError('invalid_args', 'Name the files to use.') from None
    if not isinstance(entries, list) or not entries or len(entries) > limit:
        raise ToolError('invalid_args', 'Name one or more files to use.')
    cleaned = []
    for entry in entries:
        if not isinstance(entry, str) or not entry.strip() or len(entry) > 512:
            raise ToolError('invalid_args', 'Name the files to use.')
        text = entry.strip()
        if '\x00' in text or _Path(text).is_absolute():
            raise ToolError('invalid_args', f'{text[:60]} stays inside the workspace.')
        if any(part in ('.', '..') or part.startswith('.')
               for part in _Path(text).parts):
            raise ToolError('invalid_args', 'Hidden files are outside this workflow.')
        cleaned.append(text)
    return cleaned


def _refuse_managed(workspace, path):
    """Pico's own trash and history are never renamed, copied, or zipped."""
    parts = path.relative_to(workspace.root).parts
    if parts and parts[0] in ('.pico-trash', '.pico-history'):
        raise ToolError('invalid_args', 'That file is managed by Pico.')


SCAN_CAP = 20000


def _walk_granted_files(roots):
    """Yield visible regular files under granted roots (no links)."""
    from pathlib import Path as _Path
    for root in roots:
        try:
            for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
                if '/.' in dirpath.replace(str(root), ''):
                    continue
                dirnames[:] = [d for d in dirnames if not d.startswith('.')]
                for filename in filenames:
                    if filename.startswith('.'):
                        continue
                    full = _Path(dirpath) / filename
                    if full.is_symlink():
                        continue
                    yield full
        except OSError:
            continue


def rename_file_handler(args, ctx):
    """Rename one file within its folder: same-directory move, never
    overwrites, folders and hidden names refused."""
    name = (args.get('new_name') or '').strip()
    if not name or '/' in name or '\\' in name or name in ('.', '..'):
        raise ToolError('invalid_args', 'Give the file a simple new name.')
    if name.startswith('.') or len(name) > 128:
        raise ToolError('invalid_args', 'Give the file a simple new name.')
    workspace = _workspace(ctx, 'write')
    try:
        src = workspace.resolve(args['path'])
    except NativeError:
        raise NativeError('no_match', 'Nothing to rename.') from None
    if not src.exists():
        raise NativeError('no_match', 'Nothing to rename.')
    if not src.is_file():
        raise ToolError('invalid_args', 'Only files can be renamed.')
    _refuse_managed(workspace, src)
    dest = src.parent / name
    if dest.exists():
        raise ToolError('invalid_args', f'{name[:60]} already exists here.')
    try:
        os.replace(src, dest)
        size = dest.stat().st_size
    except OSError:
        raise NativeError('permission_denied', 'Could not rename that file.') from None
    manifest = {'path': str(dest.relative_to(workspace.root)),
                'size_bytes': size, 'digest': digest_of(dest),
                'previous': args['path']}
    return (manifest, {'digest': manifest['digest']})


def duplicate_file_handler(args, ctx):
    """Copy one file next to itself: `name_copy.ext`, numbered when
    taken. Files up to 1 MB; originals are never touched."""
    workspace = _workspace(ctx, 'write')
    try:
        src = workspace.resolve(args['path'])
    except NativeError:
        raise NativeError('no_match', 'Nothing to duplicate.') from None
    if not src.exists():
        raise NativeError('no_match', 'Nothing to duplicate.')
    if not src.is_file():
        raise ToolError('invalid_args', 'Only files can be duplicated.')
    _refuse_managed(workspace, src)
    try:
        if src.stat().st_size > 1024 * 1024:
            raise ToolError('invalid_args', 'Files up to 1 MB can be duplicated.')
        raw = src.read_bytes()
    except OSError:
        raise NativeError('no_match', 'Could not read that file.') from None
    for n in range(102):
        label = '_copy' if n == 0 else f'_copy_{n + 1}'
        dest = src.parent / f'{src.stem[:100]}{label}{src.suffix}'
        if not dest.exists():
            break
    else:
        raise ToolError('invalid_args', 'Too many copies here already.')
    manifest = workspace.write_bytes(str(dest.relative_to(workspace.root)), raw)
    manifest['source'] = args['path']
    return (manifest, {'digest': manifest['digest']})


ARCHIVE_FILES_CAP = 5000
ARCHIVE_BYTES_CAP = 100 * 1024 * 1024


def archive_handler(args, ctx):
    if args['action'] == 'create':
        return _archive_create(args, ctx)
    return _archive_extract(args, ctx)


def _archive_create(args, ctx):
    """Zip files and folders (B06 slice): bounded entries and bytes,
    hidden files skipped, outputs numbered instead of overwritten."""
    import io
    import zipfile
    from pathlib import Path as _Path
    workspace = _workspace(ctx, 'write')
    entries = _clean_rel_list(args['paths_json'])
    collected, total = [], 0
    for entry in entries:
        try:
            disk = workspace.resolve(entry)
        except NativeError:
            raise ToolError('invalid_args', f'No file named {entry[:60]}.') from None
        if disk.is_symlink():
            raise ToolError('invalid_args', f'{entry[:60]} is a link, not a file.')
        if disk.is_file():
            _refuse_managed(workspace, disk)
            try:
                total += disk.stat().st_size
            except OSError:
                raise NativeError('no_match', f'Could not read {entry[:60]}.') from None
            collected.append((disk, disk.name))
        elif disk.is_dir():
            base = entry.strip().rstrip('/')
            for dirpath, dirnames, filenames in os.walk(disk, followlinks=False):
                dirnames[:] = [d for d in dirnames if not d.startswith('.')]
                here = _Path(dirpath)
                for filename in filenames:
                    if filename.startswith('.'):
                        continue
                    full = here / filename
                    if full.is_symlink():
                        continue
                    try:
                        total += full.stat().st_size
                    except OSError:
                        continue
                    collected.append((full, str((_Path(base) / full.relative_to(disk)).as_posix())))
        else:
            raise ToolError('invalid_args', f'{entry[:60]} is not usable.')
    if not collected:
        raise NativeError('no_match', 'Nothing to zip.')
    if len(collected) > ARCHIVE_FILES_CAP or total > ARCHIVE_BYTES_CAP:
        raise ToolError('invalid_args', 'That selection is larger than 5000 files or 100 MB.')
    out_name = (args.get('output') or '').strip() or f'{_Path(entries[0]).stem}.zip'
    if not out_name.lower().endswith('.zip'):
        out_name += '.zip'
    if any(part.startswith('.') for part in _Path(out_name).parts):
        raise ToolError('invalid_args', 'Hidden files are outside this workflow.')
    try:
        tentative = workspace.resolve(out_name)
    except NativeError:
        raise ToolError('invalid_args', 'Output stays inside the workspace.') from None
    if not tentative.parent.is_dir():
        raise NativeError('no_match', 'Parent folder not found.')
    dest = _numbered_dest(tentative.parent, tentative.stem[:100], 'zip')
    buf = io.BytesIO()
    try:
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for disk, arc in collected:
                zf.write(disk, arc)
    except OSError:
        raise NativeError('no_match', 'Could not read those files.') from None
    raw = buf.getvalue()
    tmp = dest.with_name(f'.{dest.name}.{os.getpid()}.tmp')
    try:
        tmp.write_bytes(raw)
        os.replace(tmp, dest)
    except OSError:
        raise NativeError('permission_denied', 'Could not save the archive.') from None
    finally:
        tmp.unlink(missing_ok=True)
    try:
        workspace.note_created(str(dest.relative_to(workspace.root)),
                               digest_of(dest))
    except OSError:
        pass
    manifest = {'path': str(dest.relative_to(workspace.root)),
                'size_bytes': len(raw), 'digest': digest_of(dest),
                'count': len(collected)}
    return (manifest, {'digest': manifest['digest']})


def _archive_extract(args, ctx):
    """Extract one zip into a folder: zip-slip guarded, bounded, and
    never overwrites (collisions gain a numeric suffix)."""
    import zipfile
    from pathlib import Path as _Path
    workspace = _workspace(ctx, 'write')
    entries = _clean_rel_list(args['paths_json'])
    if len(entries) != 1:
        raise ToolError('invalid_args', 'Extracting takes one zip file.')
    try:
        src = workspace.resolve(entries[0])
    except NativeError:
        raise ToolError('invalid_args', f'No file named {entries[0][:60]}.') from None
    if not src.is_file() or src.is_symlink() or src.suffix.lower() != '.zip':
        raise ToolError('invalid_args', f'{entries[0][:60]} is not a zip file.')
    out_dir = (args.get('output') or '').strip() or src.stem
    if any(part.startswith('.') for part in _Path(out_dir).parts):
        raise ToolError('invalid_args', 'Hidden files are outside this workflow.')
    try:
        target = workspace.resolve(out_dir)
    except NativeError:
        raise ToolError('invalid_args', 'Output stays inside the workspace.') from None
    if target.exists() and not target.is_dir():
        raise ToolError('invalid_args', 'A file blocks that folder name.')
    try:
        with zipfile.ZipFile(src) as zf:
            members = [m for m in zf.infolist() if not m.is_dir()]
            if len(members) > ARCHIVE_FILES_CAP:
                raise ToolError('invalid_args', 'That zip holds more than 5000 files.')
            if sum(m.file_size for m in members) > ARCHIVE_BYTES_CAP:
                raise ToolError('invalid_args', 'That zip holds more than 100 MB.')
            for member in members:
                parts = _Path(member.filename).parts
                if not parts or _Path(member.filename).is_absolute() or '..' in parts:
                    raise ToolError('invalid_args', 'That zip tries to escape its folder.')
            target.mkdir(parents=True, exist_ok=True)
            names = []
            for member in members:
                dest = target / member.filename
                if dest.exists():
                    for n in range(2, 102):
                        candidate = dest.parent / f'{dest.stem}_{n}{dest.suffix}'
                        if not candidate.exists():
                            dest = candidate
                            break
                    else:
                        raise ToolError('invalid_args', 'Too many copies here already.')
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(zf.read(member.filename))
                try:
                    workspace.note_created(
                        str(dest.relative_to(workspace.root)), digest_of(dest))
                except OSError:
                    pass
                names.append({'name': dest.name[:120],
                              'path': str(dest.relative_to(workspace.root))[:128]})
    except zipfile.BadZipFile:
        raise ToolError('invalid_args', 'That zip is unreadable.') from None
    data = {'output': str(target.relative_to(workspace.root)),
            'count': len(names), 'files': names[:50]}
    return (data, {'count': len(names)})


RECENT_CAP = 20


def recent_files_handler(args, ctx):
    """Newest-first files under granted folders: bounded, empty when
    nothing changed, never leaks paths (ids and names only)."""
    import time
    from pathlib import Path as _Path
    days = args.get('days') or 7
    cutoff = time.time() - days * 86400
    roots = granted_roots(ctx.get('grants') or [])
    if not roots:
        raise NativeError('permission_denied', 'No folder access granted.')
    found, scanned = [], 0
    for full in _walk_granted_files(roots):
        scanned += 1
        if scanned > SCAN_CAP:
            break
        try:
            stat = full.stat()
        except OSError:
            continue
        if stat.st_mtime < cutoff:
            continue
        found.append((stat.st_mtime, full, stat.st_size))
    found.sort(key=lambda item: item[0], reverse=True)
    files = [{'candidate_id': candidate_id_for(path), 'name': path.name[:120],
              'size_bytes': size, 'modified': int(mtime)}
             for mtime, path, size in found[:RECENT_CAP]]
    data = {'files': files, 'found': len(found),
            'truncated': len(found) > RECENT_CAP or scanned > SCAN_CAP,
            'days': days}
    return (data, {'count': len(files)})


CONTENT_SCAN_BYTES = 1024 * 1024
CONTENT_MATCHES_CAP = 20


def search_contents_handler(args, ctx):
    """Grep granted folders (B01 slice): case-insensitive substring over
    text files, one snippet per file, binaries and big files skipped.
    Empty when nothing matches; never an error."""
    query = (args.get('query') or '').strip().lower()
    if not query:
        raise ToolError('invalid_args', 'Missing query.')
    roots = granted_roots(ctx.get('grants') or [])
    if not roots:
        raise NativeError('permission_denied', 'No folder access granted.')
    matches, scanned, skipped = [], 0, 0
    for full in _walk_granted_files(roots):
        scanned += 1
        if scanned > SCAN_CAP or len(matches) > CONTENT_MATCHES_CAP:
            break
        try:
            if full.stat().st_size > CONTENT_SCAN_BYTES:
                skipped += 1
                continue
            raw = full.read_bytes()
        except OSError:
            continue
        if b'\x00' in raw[:8192]:
            skipped += 1
            continue
        try:
            text = raw.decode('utf-8')
        except UnicodeError:
            skipped += 1
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            at = line.lower().find(query)
            if at < 0:
                continue
            start = max(0, at - 40)
            matches.append({'candidate_id': candidate_id_for(full),
                            'name': full.name[:120], 'line': lineno,
                            'excerpt': line[start:start + 120].strip()[:120]})
            break  # One match per file keeps the list scannable.
    data = {'matches': matches[:CONTENT_MATCHES_CAP],
            'found': len(matches), 'scanned': scanned, 'skipped': skipped,
            'truncated': len(matches) > CONTENT_MATCHES_CAP
            or scanned > SCAN_CAP}
    return (data, {'count': len(data['matches'])})


DUPLICATE_GROUPS_CAP = 20
DUPLICATE_FILE_BYTES = 20 * 1024 * 1024


def find_duplicates_handler(args, ctx):
    """Group byte-identical files by content hash (B02 slice): sizes
    prefilter so only same-size files are hashed. Empty when all unique."""
    roots = granted_roots(ctx.get('grants') or [])
    if not roots:
        raise NativeError('permission_denied', 'No folder access granted.')
    by_size: dict[int, list] = {}
    scanned = 0
    for full in _walk_granted_files(roots):
        scanned += 1
        if scanned > SCAN_CAP:
            break
        try:
            size = full.stat().st_size
        except OSError:
            continue
        if size == 0 or size > DUPLICATE_FILE_BYTES:
            continue
        by_size.setdefault(size, []).append(full)
    groups = []
    for size in sorted(by_size):
        if len(groups) > DUPLICATE_GROUPS_CAP:
            break
        paths = by_size[size]
        if len(paths) < 2:
            continue
        by_digest: dict[str, list] = {}
        for full in paths:
            try:
                by_digest.setdefault(digest_of(full), []).append(full)
            except OSError:
                continue
        for digest, same in sorted(by_digest.items()):
            if len(same) < 2:
                continue
            ordered = sorted(same, key=lambda p: p.name.lower())
            groups.append({'digest': digest, 'size_bytes': size,
                           'files': [{'candidate_id': candidate_id_for(p),
                                      'name': p.name[:120]}
                                     for p in ordered[:20]],
                           'count': len(same)})
    data = {'groups': groups[:DUPLICATE_GROUPS_CAP],
            'found': len(groups), 'scanned': scanned,
            'truncated': len(groups) > DUPLICATE_GROUPS_CAP
            or scanned > SCAN_CAP}
    return (data, {'count': len(data['groups'])})


def largest_files_handler(args, ctx):
    """Largest-first files under granted folders: bounded list, trimmed
    scan keeps memory flat on big trees."""
    limit = args.get('limit') or 10
    roots = granted_roots(ctx.get('grants') or [])
    if not roots:
        raise NativeError('permission_denied', 'No folder access granted.')
    biggest, scanned = [], 0
    for full in _walk_granted_files(roots):
        scanned += 1
        if scanned > SCAN_CAP:
            break
        try:
            size = full.stat().st_size
        except OSError:
            continue
        biggest.append((size, full))
        if len(biggest) > limit * 4:
            biggest.sort(key=lambda item: item[0], reverse=True)
            del biggest[limit:]
    biggest.sort(key=lambda item: item[0], reverse=True)
    files = [{'candidate_id': candidate_id_for(path), 'name': path.name[:120],
              'size_bytes': size} for size, path in biggest[:limit]]
    data = {'files': files, 'limit': limit, 'scanned': scanned,
            'truncated': scanned > SCAN_CAP}
    return (data, {'count': len(files)})


def undo_edit_handler(args, ctx):
    """Undo one Pico write (B04 slice): revisions restore the saved
    version, untouched creates move to trash. Consumes one entry, so
    repeating undo walks back through versions. Refuses when the file
    changed outside Pico since that edit."""
    workspace = _workspace(ctx, 'write')
    try:
        path = workspace.resolve(args['path'])
    except NativeError:
        raise NativeError('no_match', 'Nothing to undo.') from None
    _refuse_managed(workspace, path)
    rel = str(path.relative_to(workspace.root))
    match = None
    for index, entry in reversed(workspace.journal_entries()):
        if entry.get('path') == rel and entry.get('op') in ('create', 'revise'):
            match = (index, entry)
            break
    if match is None:
        raise NativeError('no_match', 'Pico has no saved version of that file.')
    index, entry = match
    if entry.get('op') == 'create':
        if not path.is_file():
            try:
                workspace.forget_entry(index)
            except OSError:
                pass
            raise NativeError('no_match', 'Nothing to undo; that file is already gone.')
        try:
            current = digest_of(path)
        except OSError:
            raise NativeError('no_match', 'Could not read that file.') from None
        if current != entry.get('digest'):
            raise NativeError('candidate_changed',
                              'That file changed since Pico created it.')
        trashed = workspace.trash(rel)
        try:
            workspace.forget_entry(index)
        except OSError:
            pass
        return ({'path': rel, 'undone': 'create', 'trashed': trashed['trashed'],
                 'size_bytes': trashed['size_bytes'], 'digest': current},
                {'digest': current})
    if not path.is_file():
        raise NativeError('no_match', 'That file is gone; restore it from trash first.')
    try:
        current = digest_of(path)
    except OSError:
        raise NativeError('no_match', 'Could not read that file.') from None
    if current != entry.get('digest'):
        raise NativeError('candidate_changed',
                          'That file changed since that edit.')
    backup_rel = entry.get('backup')
    if not backup_rel:
        raise NativeError('no_match', 'Pico kept no version of that edit.')
    try:
        backup = (workspace.root / backup_rel).resolve()
        backup.relative_to(workspace.root)
        previous = backup.read_bytes()
    except (OSError, ValueError):
        raise NativeError('candidate_changed', 'That saved version is gone.') from None
    tmp = path.with_name(f'.{path.name}.{os.getpid()}.tmp')
    try:
        tmp.write_bytes(previous)
        os.replace(tmp, path)
    except OSError:
        raise NativeError('permission_denied', 'Could not restore that file.') from None
    finally:
        tmp.unlink(missing_ok=True)
    try:
        workspace.forget_entry(index)
    except OSError:
        pass
    manifest = {'path': rel, 'undone': 'revise',
                'size_bytes': len(previous), 'digest': digest_of(path)}
    return (manifest, {'digest': manifest['digest']})


def empty_trash_handler(args, ctx):
    """Permanently clear Pico trash: needs a delete grant plus an
    explicit EMPTY confirmation. This one cannot be undone."""
    if args.get('confirm') != 'EMPTY':
        raise ToolError('invalid_args',
                        'Clearing trash needs an explicit EMPTY confirmation.')
    workspace = _workspace(ctx, 'delete')
    trash_dir = workspace.root / '.pico-trash'
    emptied, freed = 0, 0
    if trash_dir.is_dir():
        import json as _json
        for sidecar in sorted(trash_dir.glob('*.json')):
            try:
                trashed = _json.loads(sidecar.read_text()).get('trashed', '')
            except (OSError, ValueError):
                continue
            if not trashed or '/' in trashed or '\\' in trashed:
                continue
            target = trash_dir / trashed
            try:
                if target.is_file() and not target.is_symlink():
                    freed += target.stat().st_size
                    target.unlink()
                freed += sidecar.stat().st_size
                sidecar.unlink()
                emptied += 1
            except OSError:
                continue
        for child in sorted(trash_dir.iterdir()):
            if child.is_symlink() or not child.is_file():
                continue
            try:
                freed += child.stat().st_size
                child.unlink()
            except OSError:
                continue
    data = {'emptied_count': emptied, 'freed_bytes': freed}
    return (data, {'count': emptied})


def disk_usage_handler(args, ctx):
    """Space summary over granted folders: totals plus the largest
    top-level folders. Bounded scan, empty-valid."""
    roots = granted_roots(ctx.get('grants') or [])
    if not roots:
        raise NativeError('permission_denied', 'No folder access granted.')
    total, count, scanned = 0, 0, 0
    per_root, top_dirs = [], []
    for root in roots:
        rtotal, rcount = 0, 0
        first_level: dict[str, int] = {}
        for full in _walk_granted_files([root]):
            scanned += 1
            if scanned > SCAN_CAP:
                break
            try:
                size = full.stat().st_size
            except OSError:
                continue
            total += size
            count += 1
            rtotal += size
            rcount += 1
            try:
                parts = full.relative_to(root).parts
            except ValueError:
                continue
            bucket = parts[0] if len(parts) > 1 else '.'
            first_level[bucket] = first_level.get(bucket, 0) + size
        per_root.append({'name': root.name[:60] or str(root)[-60:],
                         'size_bytes': rtotal, 'files': rcount})
        for dirname, size in first_level.items():
            top_dirs.append((size, f'{root.name[:40]}/{dirname[:60]}'))
        if scanned > SCAN_CAP:
            break
    top_dirs.sort(reverse=True)
    data = {'total_bytes': total, 'file_count': count, 'scanned': scanned,
            'truncated': scanned > SCAN_CAP, 'roots': per_root,
            'largest_folders': [{'path': label, 'size_bytes': size}
                                for size, label in top_dirs[:10]]}
    return (data, {'total_bytes': total})


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
    'convert_file': convert_file_handler,
    'delete_files': delete_files_handler,
    'restore_deleted': restore_deleted_handler,
    'pdf_pages': pdf_pages_handler,
    'rename_file': rename_file_handler,
    'duplicate_file': duplicate_file_handler,
    'archive': archive_handler,
    'recent_files': recent_files_handler,
    'search_contents': search_contents_handler,
    'find_duplicates': find_duplicates_handler,
    'largest_files': largest_files_handler,
    'undo_edit': undo_edit_handler,
    'empty_trash': empty_trash_handler,
    'disk_usage': disk_usage_handler,
}


def dispatch(tool, args, ctx):
    handler = HANDLERS.get(tool)
    if handler is None:
        raise ToolError('unsupported_tool', f'Unsupported tool: {tool}.')
    return handler(args, ctx)
