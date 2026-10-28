"""One bounded model request per Place, directly from the computer.
A Muse endpoint and key must be configured locally; there is no simulated fallback.
"""
import base64
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

from paths import resource_root
PROMPTS = resource_root()/'agents/prompts'

def prepare(sentence, character='tuck', snapshot=None):
    endpoint = os.environ.get('MUSE_API_URL', '')
    key = os.environ.get('MUSE_API_KEY', '')
    if not endpoint or not key:
        return None
    if urllib.parse.urlparse(endpoint).scheme != 'https':
        raise ValueError('The direct Muse endpoint must use HTTPS.')
    if character not in ('tuck','mica'):
        character = 'tuck'
    prompt = (PROMPTS/'common.md').read_text()+'\n'+(PROMPTS/f'{character}.md').read_text()
    content = [{'type':'text','text':sentence[:2000]}]
    if snapshot:
        file = Path(snapshot)
        if file.stat().st_size > 4_000_000:
            raise ValueError('Snapshot is too large.')
        content.append({'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(file.read_bytes()).decode()}})
    # This adapter targets an OpenAI-compatible Meta endpoint. Configure only
    # after the team's actual Muse API contract and image limits are confirmed.
    body = {'model':os.environ.get('MUSE_MODEL','muse-spark-1.3'), 'max_tokens':300,
            'messages':[{'role':'system','content':prompt},{'role':'user','content':content}]}
    request = urllib.request.Request(endpoint,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+key})
    with urllib.request.urlopen(request,timeout=35) as response:
        return str(json.load(response)['choices'][0]['message']['content']).strip()[:2000]
