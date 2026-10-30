"""Bounded app-selection messages; executable paths never cross the relay."""
import json
import time
import uuid

APP_KINDS = {'apps_request', 'open_app', 'app_catalog', 'app_result'}


def app_payload(kind, payload):
    if not isinstance(payload, dict) or any(not isinstance(v, str) for v in payload.values()):
        raise ValueError('Expected short app message fields.')
    def ids(*keys):
        for key in keys:
            uuid.UUID(payload[key])
    if kind == 'apps_request':
        if payload: raise ValueError('App-list requests have no arguments.')
    elif kind == 'open_app':
        if set(payload) != {'app_id', 'request_id'}: raise ValueError('Choose an approved app.')
        ids('app_id', 'request_id')
        payload = {**payload, 'expires_at': str(int(time.time() * 1000) + 60000)}
    elif kind == 'app_catalog':
        if set(payload) != {'catalog'} or len(payload['catalog']) > 6000: raise ValueError('Invalid app list.')
        apps = json.loads(payload['catalog'])
        if not isinstance(apps, list) or len(apps) > 20: raise ValueError('Choose up to 20 apps.')
        seen = set()
        for app in apps:
            if not isinstance(app, dict) or set(app) != {'id', 'name'}: raise ValueError('App paths are private.')
            if not isinstance(app['id'], str): raise ValueError('Invalid app ID.')
            uuid.UUID(app['id'])
            if app['id'] in seen or not isinstance(app['name'], str) or not 1 <= len(app['name']) <= 40: raise ValueError('Invalid app entry.')
            seen.add(app['id'])
    elif kind == 'app_result':
        if set(payload) != {'app_id', 'request_id', 'result', 'message'}: raise ValueError('Invalid app result.')
        ids('app_id', 'request_id')
        if payload['result'] not in ('opened', 'failed') or len(payload['message']) > 200: raise ValueError('Invalid app result.')
    return payload
