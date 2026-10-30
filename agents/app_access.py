"""Local app grants. Remote callers supply an opaque ID, never a path or command."""
import json
import re
import time
import uuid


def approved_apps(values):
    apps = []
    seen = set()
    for app in values if isinstance(values, list) else []:
        if not isinstance(app, dict): continue
        try: identity = str(uuid.UUID(app.get('id', '')))
        except (ValueError, TypeError, AttributeError): continue
        bundle = str(app.get('bundle', ''))
        if identity in seen or not re.fullmatch(r'[A-Za-z0-9_.-]+', bundle): continue
        name = str(app.get('name', '')).strip()[:40]
        if not name: continue
        apps.append({'id': identity, 'name': name, 'bundle': bundle}); seen.add(identity)
        if len(apps) == 20: break
    return apps


def catalog(state):
    return {'catalog': json.dumps([{'id': a['id'], 'name': a['name']} for a in approved_apps(state.get('allowed_apps', []))], ensure_ascii=False, separators=(',', ':'))}


def open_selected(state, identity, platform, expires_at=None):
    if expires_at is not None:
        try: expired = int(expires_at) < int(time.time() * 1000)
        except (ValueError, TypeError): expired = True
        if expired: return False, 'This request expired. Tap the app again.'
    app = next((a for a in approved_apps(state.get('allowed_apps', [])) if a['id'] == identity), None)
    if app is None: return False, 'Approve this app on your computer first.'
    try:
        if platform.open_app(app['bundle']): return True, 'Opened ' + app['name'] + '.'
    except Exception: pass
    return False, 'Couldn’t open this app. Check that it is still installed.'
