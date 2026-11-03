"""Selected conversion/PDF tools adapted from Santosh's 27bca20.
Originals remain unchanged. No PDF password transport or external rasterizer.
All writes recheck current grants and cancellation immediately before creation.
"""
from pathlib import Path
from native_search import NativeError, granted_roots
from workspace import Workspace
from tools import ToolError
CONVERT_TARGETS = ('pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg', 'webp')
CONVERT_IMAGES = ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tif', '.tiff')
CONVERT_LIMIT = 1024 * 1024
MAX_PAGES = 100

def _workspace(ctx, access='write'):
    if not ctx.get('grants'):raise NativeError('permission_denied','Choose an approved workspace first.')
    roots = granted_roots(ctx['grants'], access=access)
    if len(roots) != 1:
        raise NativeError('permission_denied', 'Select one approved write folder.')
    class GuardedWorkspace(Workspace):
        def __init__(self, root):
            super().__init__(root)
            self.inputs = {}
        def resolve(self, relative):
            path = super().resolve(relative)
            if path.is_file() and path not in self.inputs:
                stat = path.stat()
                self.inputs[path] = (stat.st_ino, stat.st_size, stat.st_mtime_ns)
            return path
        def write_bytes(self, path, raw, base_revision=None):
            if ctx.get('cancelled', lambda: False)():
                raise NativeError('cancelled', 'Cancelled before saving; no result written.')
            refresh = ctx.get('refresh_grants')
            current = refresh() if refresh else ctx.get('current_grants', lambda: ctx['grants'])()
            if not any(Path(g['path']).resolve() == self.root and g.get('access') in ('write','delete') for g in current):
                raise NativeError('permission_denied', 'Folder access changed; no result written.')
            import hashlib, os, tempfile
            if not isinstance(raw, bytes) or len(raw) > CONVERT_LIMIT:
                raise NativeError('permission_denied', 'Result exceeds the 1 MB transfer limit; originals are unchanged.')
            for source, signature in self.inputs.items():
                stat = source.stat()
                if signature != (stat.st_ino, stat.st_size, stat.st_mtime_ns):
                    raise NativeError('candidate_changed', 'A source changed during conversion; no result saved.')
            target = super().resolve(path)
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.pico-document-', delete=False) as stream:
                    temporary = Path(stream.name)
                    stream.write(raw);stream.flush();os.fsync(stream.fileno())
                os.link(temporary, target)  # Atomic create; a concurrent new file is never replaced.
            except FileExistsError:
                raise NativeError('candidate_changed', 'The output now exists. Original files are unchanged.') from None
            finally:
                if temporary:temporary.unlink(missing_ok=True)
            return {'path': str(path), 'size_bytes': len(raw), 'digest': hashlib.sha256(raw).hexdigest()}
    return GuardedWorkspace(roots[0])

def _need_module(name, setup):
    import importlib
    try:
        return importlib.import_module(name)
    except ImportError:
        raise ToolError('unsupported_tool', setup) from None

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
            raise ToolError('invalid_args', 'File is larger than 1 MB.')
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
    return (manifest, {'digest': manifest['digest'], 'size_bytes': manifest['size_bytes']})

def _convert_bytes(raw, from_ext, to, stem):
    import io
    if from_ext in CONVERT_IMAGES and to in ('pdf', 'png', 'jpg', 'webp'):
        pil = _need_module('PIL.Image', 'pip install pillow')
        try:
            image = pil.open(io.BytesIO(raw))
            if image.width * image.height > 16_000_000:
                raise ToolError('invalid_args', 'Use a photo below 16 megapixels.')
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
            if reader.is_encrypted or len(reader.pages) > MAX_PAGES:
                raise ToolError('invalid_args', 'Use an unlocked PDF with at most 100 pages.')
            text = '\n'.join((page.extract_text() or '') for page in reader.pages)
            if not text.strip():
                raise ToolError('invalid_args', 'This scanned PDF needs OCR; no empty result was saved.')
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
        import os
        executable = shutil.which('soffice')
        if not executable and os.name == 'nt':
            for folder in (os.environ.get('ProgramFiles', r'C:\Program Files'), os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')):
                candidate = _Path(folder) / 'LibreOffice/program/soffice.exe'
                if candidate.is_file():
                    executable = str(candidate)
                    break
        if not executable:
            raise ToolError(
                'unsupported_tool',
                'install LibreOffice (soffice on PATH) for Word to PDF')
        with tempfile.TemporaryDirectory(prefix='pico-docx2pdf-') as tmp:
            src = _Path(tmp) / (stem[:60] + '.docx')
            src.write_bytes(raw)
            try:
                proc = subprocess.run(
                    [executable, '--headless', '--convert-to', 'pdf',
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
    if action not in ('merge', 'split', 'rotate', 'watermark'):
        raise ToolError('unsupported_tool', 'Use merge, split, rotate or watermark.')
    try:
        raw_paths = _json.loads(args['paths_json'])
    except (ValueError, TypeError):
        raise ToolError('invalid_args', 'Name the PDF files to use.') from None
    if not isinstance(raw_paths, list) or not raw_paths or len(raw_paths) > 10:
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
        if path.stat().st_size > CONVERT_LIMIT:
            raise ToolError('invalid_args', 'Use PDF files below 1 MB.')
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
            if sum(len(r.pages) for r in readers) + len(reader.pages) > MAX_PAGES:
                raise ToolError('invalid_args', 'Use at most 100 PDF pages in total.')
            readers.append(reader)
        if action == 'merge':
            writer = pypdf.PdfWriter()
            for reader in readers:
                for page in reader.pages:
                    writer.add_page(page)
            name = args.get('output') or f'{resolved[0].stem}_merged'
            return _write_pdf_result(writer, workspace, resolved[0], None, name)
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
    return ({**manifest, 'output': dest.name, 'pages': len(writer.pages)},
            {'digest': manifest['digest'], 'size_bytes': manifest['size_bytes']})
