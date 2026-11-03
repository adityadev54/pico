"""Local, durable result cards. Never stores execution authority or model secrets."""
import uuid

def hold_result(state, text, identity=''):
    key = str(uuid.uuid5(uuid.NAMESPACE_URL, 'pico-result:' + (identity or text)))
    places = state.setdefault('places', {})
    if key not in places:
        places[key] = {'id': key, 'sentence': text, 'status': 'ready',
                       'local_result': True, 'bundle': '', 'snapshot': None}
    return key

def may_run_focused(kind, payload):
    if kind == 'open_app': return False
    if kind == 'tool_call':
        return payload.get('tool') in {'search_documents', 'fs_read', 'fs_list', 'read_back_file', 'transfer_selected_file'}
    return not (kind == 'skill_request' and payload.get('query') == 'teach')
