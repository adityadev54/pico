"""P1 dependency probes (A14).

Every P1 capability from the backlog declares its external needs here;
each probe reports ok/missing/unconfigured with the exact account,
approval, package or binary that unlocks it. Nothing here spends money
or calls paid APIs: API-kind probes check configuration presence only.

Usage: python3 agents/deps.py [--json]
       python3 agents/deps.py install NAME --allow-install [--json]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# kind: pip (importable package), binary (PATH executable),
# env (configuration present, never called), decision (undecided).
DEPENDENCIES = (
    # Labels match docs/Pico_Real_Work_Backlog.md (B01-B08, C01-C08, D01-D10).
    # pip rows use the import name in 'name' and the PyPI name in 'package'.
    # B01 search filenames and contents
    {'capability': 'B01', 'name': 'local-search', 'kind': 'local',
     'detail': 'no external dependency; needs folders:read grant'},
    # B02 organize files with a preview
    {'capability': 'B02', 'name': 'local-fs', 'kind': 'local',
     'detail': 'no external dependency; needs folders:write grant'},
    # B03 edit files
    {'capability': 'B03', 'name': 'local-edit', 'kind': 'local',
     'detail': 'no external dependency; needs folders:write grant'},
    # B04 undo eligible modifications
    {'capability': 'B04', 'name': 'local-snapshots', 'kind': 'local',
     'detail': 'no external dependency; task-scoped snapshots on disk'},
    # B05 text extraction and OCR
    {'capability': 'B05', 'name': 'tesseract', 'kind': 'binary',
     'detail': 'install tesseract-ocr for scanned pages'},
    {'capability': 'B05', 'name': 'PIL', 'kind': 'pip', 'package': 'pillow',
     'detail': 'pip install pillow (image prep for OCR)'},
    {'capability': 'B05', 'name': 'pypdf', 'kind': 'pip',
     'detail': 'pip install pypdf (selectable-text pages)'},
    # B06 archives
    {'capability': 'B06', 'name': 'local-archives', 'kind': 'local',
     'detail': 'no external dependency; stdlib zipfile/tarfile'},
    # B07 phone uploads as task inputs
    {'capability': 'B07', 'name': 'local-transfer', 'kind': 'local',
     'detail': 'no external dependency; relay transfer path'},
    # B08 file identity across versions
    {'capability': 'B08', 'name': 'local-identity', 'kind': 'local',
     'detail': 'no external dependency; hash + revision tracking'},
    # C01 understand a repository
    {'capability': 'C01', 'name': 'local-inspect', 'kind': 'local',
     'detail': 'no external dependency for structural inspection'},
    {'capability': 'C01', 'name': 'model-provider', 'kind': 'decision',
     'detail': 'A05: model provider + keys for plans and summaries'},
    # C02 focused code patch
    {'capability': 'C02', 'name': 'local-patch', 'kind': 'local',
     'detail': 'no external dependency; scoped writes built in'},
    # C03 run tests
    {'capability': 'C03', 'name': 'local-tests', 'kind': 'local',
     'detail': "no Pico dependency; uses the project's own toolchain"},
    # C04 local app previews
    {'capability': 'C04', 'name': 'local-preview', 'kind': 'local',
     'detail': "no Pico dependency; uses the project's own environment"},
    {'capability': 'C04', 'name': 'node', 'kind': 'binary',
     'detail': 'optional: install Node.js for JS/TS project previews'},
    # C05 git without destroying work
    {'capability': 'C05', 'name': 'git', 'kind': 'binary',
     'detail': 'install git'},
    {'capability': 'C05', 'name': 'gh', 'kind': 'binary',
     'detail': 'optional: install GitHub CLI + gh auth login (draft PRs)'},
    # C06 scripts and local data
    {'capability': 'C06', 'name': 'local-scripts', 'kind': 'local',
     'detail': 'no external dependency; stdlib python'},
    # C07 debug UI with browser evidence
    {'capability': 'C07', 'name': 'playwright', 'kind': 'pip',
     'detail': 'pip install playwright, then: playwright install chromium'},
    # C08 review prep
    {'capability': 'C08', 'name': 'git', 'kind': 'binary',
     'detail': 'install git (shared with C05)'},
    {'capability': 'C08', 'name': 'model-provider', 'kind': 'decision',
     'detail': 'A05: model provider + keys for behavior summaries'},
    # D01 essay/report into a real document
    {'capability': 'D01', 'name': 'docx', 'kind': 'pip', 'package': 'python-docx',
     'detail': 'pip install python-docx (DOCX output)'},
    # D02 revise a section
    {'capability': 'D02', 'name': 'D01', 'kind': 'local',
     'detail': 'no new dependency beyond D01'},
    # D03 Word documents to PDF
    {'capability': 'D03', 'name': 'libreoffice', 'kind': 'binary',
     'detail': 'install LibreOffice (soffice on PATH)'},
    # D04 JPG/PNG images into a PDF
    {'capability': 'D04', 'name': 'PIL', 'kind': 'pip', 'package': 'pillow',
     'detail': 'pip install pillow (shared with B05)'},
    # D05 PDF into editable Word
    {'capability': 'D05', 'name': 'pypdf', 'kind': 'pip',
     'detail': 'pip install pypdf (text-PDF path; shared with B05)'},
    {'capability': 'D05', 'name': 'tesseract', 'kind': 'binary',
     'detail': 'install tesseract-ocr (scanned-PDF path; shared with B05)'},
    # D06 PDF page operations
    {'capability': 'D06', 'name': 'pypdf', 'kind': 'pip',
     'detail': 'pip install pypdf (shared with B05)'},
    # D07 image transformations
    {'capability': 'D07', 'name': 'PIL', 'kind': 'pip', 'package': 'pillow',
     'detail': 'pip install pillow (shared with B05)'},
    # D08 spreadsheet cleanup and export
    {'capability': 'D08', 'name': 'openpyxl', 'kind': 'pip',
     'detail': 'pip install openpyxl'},
    # D09 formulas and charts
    {'capability': 'D09', 'name': 'openpyxl', 'kind': 'pip',
     'detail': 'pip install openpyxl (shared with D08)'},
    {'capability': 'D09', 'name': 'libreoffice', 'kind': 'binary',
     'detail': 'install LibreOffice for recalculation (shared with D03)'},
    # D10 slide deck
    {'capability': 'D10', 'name': 'pptx', 'kind': 'pip', 'package': 'python-pptx',
     'detail': 'pip install python-pptx'},
    {'capability': 'D10', 'name': 'libreoffice', 'kind': 'binary',
     'detail': 'install LibreOffice for slide PDF export (shared with D03)'},
)


def check(spec):
    kind, name = spec['kind'], spec['name']
    if kind == 'pip':
        ok = importlib.util.find_spec(name) is not None
        return status(spec, 'ok' if ok else 'missing')
    if kind == 'binary':
        ok = shutil.which(name) is not None
        return status(spec, 'ok' if ok else 'missing')
    if kind == 'env':
        ok = bool(os.environ.get(name))
        return status(spec, 'ok' if ok else 'unconfigured')
    if kind == 'local':
        return status(spec, 'ok')
    return status(spec, 'unconfigured')


def status(spec, state):
    return {'capability': spec['capability'], 'name': spec['name'],
            'status': state, 'detail': spec['detail']}


def check_all(specs=DEPENDENCIES):
    return [check(spec) for spec in specs]


def find_spec(name, specs=DEPENDENCIES):
    for spec in specs:
        if name in (spec['name'], spec.get('package')):
            return spec
    return None


def install(name, *, allow=False, specs=DEPENDENCIES, runner=None):
    """Install one pip-kind dependency when explicitly authorized.

    Only names declared in the table with kind 'pip' are installable;
    anything else fails closed with its unlock detail. The install is
    claimed complete only when the probe passes afterwards.
    """
    if not allow:
        return {'name': name, 'installed': False,
                'error': 'refused: pass --allow-install to authorize this install'}
    spec = find_spec(name, specs)
    if spec is None:
        return {'name': name, 'installed': False,
                'error': f'unknown dependency: {name}'}
    if spec['kind'] != 'pip':
        return {'name': name, 'installed': False,
                'error': f"not installable by Pico ({spec['kind']}): {spec['detail']}"}
    package = spec.get('package', spec['name'])
    try:
        proc = (runner or subprocess.run)(
            [sys.executable, '-m', 'pip', 'install', package],
            capture_output=True, timeout=300)
    except Exception as error:
        return {'name': name, 'installed': False, 'error': str(error)}
    if proc.returncode != 0:
        tail = (proc.stderr or b'').decode('utf-8', 'replace')[-500:]
        return {'name': name, 'installed': False,
                'error': f'pip install {package} failed: {tail.strip()}'}
    probe = check(spec)
    result = {'name': name, 'installed': probe['status'] == 'ok',
              'status': probe['status']}
    if probe['status'] != 'ok':
        result['error'] = (f'installed {package} but probe still '
                           f'{probe["status"]}')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='Pico P1 dependency probes')
    parser.add_argument('action', nargs='?', default='check',
                        choices=('check', 'install'))
    parser.add_argument('name', nargs='?', default=None)
    parser.add_argument('--allow-install', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    if args.action == 'install':
        if not args.name:
            parser.error('install needs a dependency name')
        result = install(args.name, allow=args.allow_install)
        if args.json:
            print(json.dumps(result, indent=2))
        elif result['installed']:
            print(f"installed {result['name']} (probe: {result['status']})")
        else:
            print(f"not installed: {result['error']}")
        return 0 if result['installed'] else 1
    results = check_all()
    if args.json:
        print(json.dumps({'results': results}, indent=2))
    else:
        for result in results:
            print(f"[{result['status'].upper():12}] {result['capability']} "
                  f"{result['name']}: {result['detail']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
