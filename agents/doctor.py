"""Environment doctor for the Pico helper (A03).

Usage: python3 agents/doctor.py [--relay URL] [--json]

Runs one honest pass over helper dependencies: heartbeat, workspace
folders, interpreter, OS screen permission (macOS), relay reachability
and model configuration. Every probe reports pass/fail/skip with a
detail string; nothing raises past the reporter. Exit 0 means no probe
failed. Network/model probes fail honestly offline or unconfigured.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_search import granted_roots  # noqa: E402
import deps as dep_probes  # noqa: E402

DEFAULT_RELAY = 'https://pico-companion.fly.dev'


def probe_heartbeat(_):
    return {'name': 'heartbeat', 'status': 'pass',
            'detail': f'pid={os.getpid()} time={int(time.time())} '
                      f'python={platform.python_version()} {sys.platform}'}


def probe_folders(ctx):
    grants = ctx.get('grants')
    if grants is None:
        grants = [{'path': p} for p in
                  os.environ.get('PICO_SEARCH_ROOTS', '').split(os.pathsep) if p.strip()]
    roots = granted_roots(grants)
    if not roots:
        return {'name': 'folders', 'status': 'fail',
                'detail': 'no granted folders resolve'}
    return {'name': 'folders', 'status': 'pass',
            'detail': f'{len(roots)} root(s): {roots[0]}'}


def probe_interpreter(_):
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 10):
        return {'name': 'interpreter', 'status': 'fail',
                'detail': f'python {major}.{minor} < 3.10'}
    return {'name': 'interpreter', 'status': 'pass',
            'detail': platform.python_version()}


def probe_screen_permission(_):
    if sys.platform != 'darwin':
        return {'name': 'screen_permission', 'status': 'skip',
                'detail': f'not applicable on {sys.platform}'}
    binary = Path(__file__).resolve().parent / 'native' / 'macos_context'
    if not binary.is_file():
        return {'name': 'screen_permission', 'status': 'skip',
                'detail': 'macos_context not built (run_companion builds it)'}
    try:
        raw = subprocess.run([str(binary)], capture_output=True, timeout=10)
        access = json.loads(raw.stdout or b'{}').get('screen_access')
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        return {'name': 'screen_permission', 'status': 'fail',
                'detail': f'probe error: {type(error).__name__}'}
    if access:
        return {'name': 'screen_permission', 'status': 'pass',
                'detail': 'screen recording granted'}
    return {'name': 'screen_permission', 'status': 'fail',
            'detail': 'screen recording not granted (snapshots will skip)'}


def probe_relay(ctx):
    base = ctx.get('relay') or os.environ.get('PICO_RELAY_URL', DEFAULT_RELAY)
    try:
        request = urllib.request.Request(base.rstrip('/') + '/health')
        with urllib.request.urlopen(request, timeout=10) as response:
            health = json.load(response)
    except Exception as error:
        return {'name': 'relay', 'status': 'fail',
                'detail': f'{base}: {type(error).__name__}'}
    if health.get('supabase_connected'):
        return {'name': 'relay', 'status': 'pass', 'detail': base}
    return {'name': 'relay', 'status': 'fail',
            'detail': f'{base}: backend reports unhealthy'}


def probe_model(_):
    url = os.environ.get('MUSE_API_URL', '')
    key = os.environ.get('MUSE_API_KEY', '')
    if not url or not key:
        return {'name': 'model', 'status': 'fail',
                'detail': 'MUSE_API_URL/MUSE_API_KEY not configured (no calls attempted)'}
    return {'name': 'model', 'status': 'pass',
            'detail': 'endpoint + key present (no calls attempted)'}


def probe_p1_deps(_):
    results = dep_probes.check_all()
    missing = [r for r in results if r['status'] != 'ok']
    if not missing:
        return {'name': 'p1_deps', 'status': 'pass',
                'detail': 'all P1 dependencies ready'}
    return {'name': 'p1_deps', 'status': 'skip',
            'detail': f"{len(results) - len(missing)}/{len(results)} ready;"
                      ' run agents/deps.py for the unlock list'}


DEFAULT_PROBES = (probe_heartbeat, probe_folders, probe_interpreter,
                  probe_screen_permission, probe_relay, probe_model,
                  probe_p1_deps)


def run_checks(ctx=None, probes=DEFAULT_PROBES):
    ctx = ctx or {}
    results = []
    for probe in probes:
        try:
            result = probe(ctx)
        except Exception as error:  # Probes must never crash the report.
            result = {'name': getattr(probe, '__name__', 'probe'),
                      'status': 'fail', 'detail': f'crashed: {type(error).__name__}'}
        results.append(result)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description='Pico helper dependency doctor')
    parser.add_argument('--relay', default=None)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    results = run_checks({'relay': args.relay})
    if args.json:
        print(json.dumps({'results': results}, indent=2))
    else:
        for result in results:
            print(f"[{result['status'].upper():4}] {result['name']}: {result['detail']}")
    return 0 if all(r['status'] != 'fail' for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
