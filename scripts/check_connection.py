"""Real integration check against the configured project. Creates and removes only its own test account."""
import argparse
import json
import secrets
import sys
import tempfile
import threading
import urllib.error
import urllib.request
import uuid
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from relay.app import load_env, make_handler
from relay.service import Supabase, PicoService, ApiError
from relay.state import RelayState
import os


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--env-file',required=True);parser.add_argument('--report');parser.add_argument('--relay-url');parser.add_argument('--native-overlay', action='store_true')
    args=parser.parse_args();load_env(args.env_file)
    db=Supabase(os.environ['SUPABASE_URL'],os.environ['SUPABASE_SERVICE_ROLE_KEY'])
    checks=[];owner=None;server=None
    with tempfile.TemporaryDirectory(prefix='pico-connection-') as directory:
        state=RelayState(Path(directory)/'state.sqlite');service=PicoService(db,state)
        try:
            email='pico-test-'+uuid.uuid4().hex+'@example.com';password=secrets.token_urlsafe(32)
            result=db.request('/auth/v1/admin/users',{'email':email,'password':password,'email_confirm':True},'POST');owner=result['id']
            auth=db.request('/auth/v1/token?grant_type=password',{'email':email,'password':password},'POST')
            token=auth['access_token'];checks.append('Real phone account sign-in')
            if args.relay_url:
                base=args.relay_url.rstrip('/')
            else:
                server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(service));threading.Thread(target=server.serve_forever,daemon=True).start()
                base=f'http://127.0.0.1:{server.server_port}'
            def request(path,body=None,authorization=None):
                data=None if body is None else json.dumps(body).encode()
                req=urllib.request.Request(base+path,data=data,headers={'Content-Type':'application/json',**({'Authorization':'Bearer '+authorization} if authorization else {})})
                with urllib.request.urlopen(req,timeout=25) as response:return json.load(response)
            assert request('/health')['supabase_connected'];checks.append('Existing Supabase project reachable')
            pairing=request('/pairing',{},token);assert len(pairing['code'])==6 and pairing['code'].isdigit();checks.append('6-digit, 5-minute pairing code')
            device=request('/claim',{'code':pairing['code'],'os':'macos','name':'Pico integration test'})
            device_token=device['token'];id=device['device_id'];checks.append('Real desktop device-token claim')
            try:request('/claim',{'code':pairing['code'],'os':'macos'});raise AssertionError('Code reused')
            except urllib.error.HTTPError as error:assert error.code==400
            checks.append('Pairing code cannot be reused')
            assert request('/devices',authorization=token)['devices'][0]['id']==id;checks.append('Paired computer visible to phone')
            companion=request('/mail',{'device_id':id,'kind':'companion','id':str(uuid.uuid4()),'payload':{'character':'mica','size':'small'}},token)
            if args.native_overlay:
                import subprocess, queue, time
                sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'agents'))
                from companion import Companion
                root=Path(__file__).resolve().parents[1]
                overlay=subprocess.Popen([str(root/'.local/Pico Overlay.app/Contents/MacOS/PicoOverlay'),str(root/'assets/characters'),'--verify'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,bufsize=1)
                rendered=queue.Queue()
                def read_proofs():
                    for line in overlay.stdout:
                        try:rendered.put(json.loads(line))
                        except ValueError:pass
                threading.Thread(target=read_proofs,daemon=True).start()
                consumer=Companion.__new__(Companion)
                consumer.mood='idle';consumer.mood_until=0;consumer.overlay=overlay;consumer.lock=threading.RLock();consumer.state={'handled':[],'character':'tuck','size':'medium'};consumer.acks=[]
                consumer.state_file=Path(directory)/'places.json'
                try:
                    for agent in ('mica','tuck'):
                        request('/mail',{'device_id':id,'kind':'companion','payload':{'character':agent,'size':'small'}},token)
                        pending=request('/agent/poll',{},device_token)['mail']
                        for message in pending:consumer.consume(message)
                        deadline=time.monotonic()+12
                        while True:
                            proof=rendered.get(timeout=max(.1,deadline-time.monotonic()))
                            if proof.get('rendered_character')==agent and proof.get('size')=='small':break
                            assert time.monotonic()<deadline
                        assert json.loads(consumer.state_file.read_text())['character']==agent
                        request('/agent/ack',{'ids':consumer.acks},device_token);consumer.acks.clear()
                    checks.append('Both mobile selections reach Companion.consume, persist, and render in the real AppKit overlay')
                    for mood in ('idle','listening','talking','working'):
                        request('/mail',{'device_id':id,'kind':'companion','payload':{'character':'tuck','size':'medium','mood':mood,'mood_until':str(int(time.time()*1000)+60000)}},token)
                        pending=request('/agent/poll',{},device_token)['mail']
                        for message in pending:consumer.consume(message)
                        deadline=time.monotonic()+12
                        while True:
                            proof=rendered.get(timeout=max(.1,deadline-time.monotonic()))
                            if proof.get('rendered_character')=='tuck' and proof.get('mood')==mood:break
                            assert time.monotonic()<deadline
                        request('/agent/ack',{'ids':consumer.acks},device_token);consumer.acks.clear()
                    consumer.present('talking','Your next step is ready.','test-place')
                    deadline=time.monotonic()+12
                    while True:
                        proof=rendered.get(timeout=max(.1,deadline-time.monotonic()))
                        if proof.get('reply_visible') and proof.get('mood')=='talking':
                            assert proof.get('reply_above') and proof.get('reply_centered')
                            break
                    checks.append('Tuck idle, listening, talking and working render from live relay state; actual reply appears in native companion bubble')
                finally:
                    overlay.stdin.close();overlay.wait(timeout=10)
                companion=request('/mail',{'device_id':id,'kind':'companion','payload':{'character':'mica','size':'small'}},token)
            place_id=str(uuid.uuid4());mail=request('/mail',{'device_id':id,'kind':'place','id':place_id,'payload':{'place_id':place_id,'sentence':'Resume the test note'}},token)
            repeat=request('/mail',{'device_id':id,'kind':'place','id':place_id,'payload':{'place_id':place_id,'sentence':'Resume the test note'}},token);assert repeat['id']==mail['id']
            checks.append('Phone sends durable text while computer is offline; duplicate retry stays single')
            polled=request('/agent/poll',{},device_token)['mail'];assert any(m['payload'].get('character')=='mica' and m['payload'].get('size')=='small' for m in polled)
            assert any(m['payload'].get('sentence')=='Resume the test note' for m in polled);checks.append('Computer receives companion choice, size and Place')
            request('/agent/ack',{'ids':[m['id'] for m in polled]},device_token)
            assert request('/agent/poll',{},device_token)['mail']==[];assert mail['id'] in request('/receipts',{'ids':[mail['id']]},token)['delivered'];checks.append('Acknowledged messages deleted; delivery receipt reaches phone')
            note=request('/agent/mail',{'id':str(uuid.uuid4()),'kind':'idle','payload':{'place_id':place_id,'app':'Test editor'}},device_token)
            incoming=request('/phone/mail',authorization=token)['mail'];assert incoming[0]['payload']['app']=='Test editor'
            request('/phone/ack',{'device_id':id,'ids':[note['id']]},token);checks.append('Computer idle prompt reaches phone without a screenshot')
            try:request('/mail',{'device_id':id,'kind':'place','payload':{'snapshot':'not-allowed'}},token);raise AssertionError('Snapshot accepted')
            except urllib.error.HTTPError as error:assert error.code==400
            checks.append('Mailbox rejects screenshot payloads')
            request('/unpair',{'device_id':id},token)
            try:request('/agent/poll',{},device_token);raise AssertionError('Revoked token accepted')
            except urllib.error.HTTPError as error:assert error.code==401
            checks.append('Phone unpair immediately revokes device access')
            for _ in range(5):
                try:service.claim({'code':'not-a-code','os':'macos'},'lockout-test')
                except ApiError:pass
            try:service.claim({'code':'123456','os':'macos'},'lockout-test');raise AssertionError('Lockout not enforced')
            except ApiError as error:assert error.status==429
            checks.append('Five invalid codes trigger a 10-minute lockout')
            report={'project':'melngaeuytjuvfolwabd','passed':checks,'temporary_test_account_removed':False,'screenshots_uploaded':False}
        finally:
            if server:server.shutdown();server.server_close()
            if owner:db.request('/auth/v1/admin/users/'+owner,method='DELETE')
        report['temporary_test_account_removed']=True
        print(json.dumps(report,indent=2))
        if args.report:Path(args.report).write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
