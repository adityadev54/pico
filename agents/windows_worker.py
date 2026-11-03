"""Private stdio worker for Windows. Shares the tested file and teaching engines.
No listening port, credentials, desktop recording, or automatic model retries.
"""
import json,sys
from pathlib import Path
from tools import TOOL_REGISTRY
from handlers import dispatch
from skills.engine import SkillEngine

def send(value):
    print(json.dumps(value),flush=True)
def callback(kind,body=None):
    send({'callback':kind,'body':body or {}})
    line=sys.stdin.readline()
    if not line:raise EOFError('Companion disconnected')
    reply=json.loads(line)
    if reply.get('error'):raise ValueError(reply['error'])
    return reply.get('result')
def grants():return callback('grants')
def main():
    engine=None;directory=None
    for line in sys.stdin:
        try:
            request=json.loads(line);op=request['operation']
            if op=='tool':
                p=request['payload'];selected=[g for g in grants() if g['id']==p.get('grant_id')]
                if len(selected)!=1:raise ValueError('Choose one approved workspace.')
                ctx={'grants':selected,'refresh_grants':grants,'cancelled':lambda:callback('cancelled') is True}
                data,evidence=dispatch(p['tool'],TOOL_REGISTRY.validate(p['tool'],p),ctx)
                result={'data':data,'evidence':evidence}
            else:
                if engine is None or directory!=request['directory']:
                    directory=request['directory'];engine=SkillEngine(directory,grants,lambda body:callback('model',body))
                if op=='start':result=engine.start(request['root'],request['sources'],request['output'])
                elif op=='finish':result=engine.finish(request['session'],request['name'],True)
                elif op=='run':result=engine.run(request['id'],True,request.get('request_id'))
                elif op=='sources':engine.replace_sources(request['id'],request['sources']);result={}
                elif op=='latest':result={'path':str(engine.latest(request['id']))}
                elif op=='cancel':engine.sessions.clear();result={}
                elif op=='catalog':
                    result=engine.list()
                    for row in result:
                        recipe=json.loads((engine.directory/(row['id']+'.json')).read_text(encoding='utf-8'));row['sources']=recipe['sources']
                else:raise ValueError('Unsupported worker operation')
            send({'result':result})
        except Exception as error:
            send({'error':str(error)[:500],'code':getattr(error,'code','request_failed')})
if __name__=='__main__':main()
