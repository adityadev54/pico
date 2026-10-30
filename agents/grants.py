"""Folder grant store for the Pico helper (A10).

Grants live in the companion state file (`~/.pico/places.json`, key
"grants") as records {id, path, access, granted_at, source}. Access is
read or write; write implies read. Legacy {path}-only entries are
treated as read-only. Enforcement happens in native_search (root
selection by level) and handlers (per-tool level); this module owns
request/grant/revoke bookkeeping plus a small CLI:

  python3 agents/grants.py list [--state PATH]
  python3 agents/grants.py grant ~/Documents [--access read|write] [--state PATH]
  python3 agents/grants.py revoke <id-or-path> [--state PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

LEVELS = ('read', 'write')
DEFAULT_STATE = Path.home() / '.pico' / 'places.json'


def normalize(grants):
    """Legacy {path} entries become read-only; records pass through."""
    out = []
    for grant in grants or []:
        if 'access' not in grant:
            grant = {**grant, 'access': 'read', 'id': grant.get('id', 'legacy'),
                     'granted_at': grant.get('granted_at', ''), 'source': 'legacy'}
        out.append(grant)
    return out


def load_state(path):
    path = Path(path)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except ValueError:
        raise SystemExit(f'error: {path} is not valid JSON')
    return data if isinstance(data, dict) else {}


def save_state(path, state):
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = path.with_name(f'.{path.name}.{uuid.uuid4().hex[:8]}.tmp')
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(path)


def list_grants(state_path=DEFAULT_STATE):
    return normalize(load_state(state_path).get('grants', []))


def grant(path, access='read', source='cli', state_path=DEFAULT_STATE):
    if access not in LEVELS:
        raise SystemExit('error: access must be read or write')
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir():
        raise SystemExit(f'error: {path} is not a directory')
    state = load_state(state_path)
    grants = normalize(state.get('grants', []))
    for grant in grants:
        if grant.get('path') == str(resolved):
            grant['access'] = access
            grant['granted_at'] = stamp()
            grant['source'] = source
            break
    else:
        grants.append({'id': uuid.uuid4().hex[:8], 'path': str(resolved),
                       'access': access, 'granted_at': stamp(), 'source': source})
    state['grants'] = grants
    save_state(state_path, state)
    return grants


def revoke(ref, state_path=DEFAULT_STATE):
    state = load_state(state_path)
    grants = normalize(state.get('grants', []))
    try:
        resolved = str(Path(ref).expanduser().resolve())
    except (OSError, RuntimeError):
        resolved = ref
    kept = [g for g in grants if g.get('id') != ref and g.get('path') != resolved]
    if len(kept) == len(grants):
        raise SystemExit(f'error: no grant matches {ref!r}')
    state['grants'] = kept
    save_state(state_path, state)
    return kept


def stamp():
    return datetime.now(timezone.utc).isoformat()


def main(argv=None):
    parser = argparse.ArgumentParser(description='Manage Pico folder grants')
    parser.add_argument('--state', default=str(DEFAULT_STATE))
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list')
    g = sub.add_parser('grant')
    g.add_argument('path')
    g.add_argument('--access', default='read')
    g.add_argument('--source', default='cli')
    r = sub.add_parser('revoke')
    r.add_argument('ref')
    args = parser.parse_args(argv)
    if args.command == 'list':
        grants = list_grants(args.state)
        if not grants:
            print('no folder grants')
        for entry in grants:
            print(f"{entry.get('id')}  {entry.get('access'):5}  {entry.get('path')}")
        return 0
    if args.command == 'grant':
        grant(args.path, args.access, args.source, args.state)
        print(f"granted {args.access} on {args.path}")
        return 0
    revoke(args.ref, args.state)
    print(f'revoked {args.ref}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
