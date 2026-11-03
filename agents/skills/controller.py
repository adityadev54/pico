"""Companion integration for local, explicitly taught file routines."""
import json,threading,time,uuid
from pathlib import Path
from .engine import SkillEngine

class SkillsController:
    def __init__(self,companion):
        self.c=companion;self.engines={};self.session=None;self.busy=False
    def engine(self):
        c=self.c
        if not c.client:raise ValueError('Connect your phone first; Muse runs through your paired account.')
        identity=c.client.device_id
        if identity not in self.engines:
            client=c.client
            def model(body):
                if c.client is not client:raise ValueError('The paired account changed. Start again.')
                result=client.post('/agent/skills/model',body)
                if c.client is not client:raise ValueError('The paired account changed. Result discarded.')
                return result
            self.engines[identity]=SkillEngine(c.directory/'routines'/identity,lambda:c.state['grants'] if c.client is client else [],model)
        return self.engines[identity]
    def show(self,message=''):
        try:
            engine=self.engine();rows=engine.list()
            for row in rows:
                recipe=json.loads((engine.directory/(row['id']+'.json')).read_text());row['sources']=recipe['sources'];row['has_output']=any(r['status']=='completed' for r in recipe['runs'])
            payload={'routines':rows,'grants':[g for g in self.c.state['grants'] if g['access'] in ('write','delete')],'recording':bool(self.session),'busy':self.busy,'message':message}
            self.c.overlay_message({'command':'teach','payload':json.dumps(payload)})
        except Exception as e:self.c.events.put(('notice',str(e)))
    def publish(self,request='',status='catalog',message=''):
        rows=self.engine().list()[:12]
        # Only selected-file names, never contents, are announced to the paired phone.
        for row in rows:
            recipe=json.loads((self.engine().directory/(row['id']+'.json')).read_text());row['sources']=recipe['sources'];row.pop('root',None)
        while len(json.dumps(rows))>5900:rows.pop()
        payload={'request_id':request,'status':status,'message':message[:1200],'catalog':json.dumps(rows)}
        with self.c.lock:self.c.state['outgoing'].append({'id':str(uuid.uuid4()),'kind':'skill_result','payload':payload})
        self.c.save()
    def action(self,value):
        choice=value.get('choice')
        try:
            if choice=='start':
                if self.busy or self.session:raise ValueError('Finish or cancel the current teaching run first.')
                record=self.engine().start(value['root'],value['sources'],value['output']);self.session=record['id']
                self.show('Watching only your selected example file. Edit it, save, then finish teaching.')
                import subprocess
                subprocess.Popen(['/usr/bin/open','-e',str(Path(record['root'])/record['output'])])
            elif choice=='sources':
                if self.busy:raise ValueError('Wait for the current run to finish.')
                self.engine().replace_sources(value['id'],value['sources']);self.show('Inputs updated. Your learned format is unchanged.')
            elif choice=='open':
                import subprocess
                subprocess.Popen(['/usr/bin/open','-e',str(self.engine().latest(value['id']))])
            elif choice=='cancel':
                if self.session:self.engine().sessions.pop(self.session,None)
                self.session=None;self.show('Teaching stopped. Nothing was sent to Muse.')
            elif choice in ('finish','run'):
                if value.get('confirmed') is not True:raise ValueError('Review the selected files and approve this Muse request.')
                if self.busy:raise ValueError('A routine is already working.')
                engine=self.engine();sid=self.session;self.busy=True;self.show('Muse is working…');self.c.present('curious' if choice=='finish' else 'working','Preparing your result…',seconds=60)
                def work():
                    try:
                        if choice=='finish':
                            recipe=engine.finish(sid,value.get('name','My routine'),True);self.session=None;message='Learned “'+recipe['name']+'”. Change the notes, then run it again.'
                        else:
                            result=engine.run(value['id'],True,value.get('request_id'));message='Saved and verified: '+result['output']
                        self.publish(value.get('request_id',''),'completed',message);self.c.events.put(('presentation',('happy',message,'',4)))
                    except Exception as e:
                        message=str(e);self.publish(value.get('request_id',''),'failed',message);self.c.events.put(('presentation',('angry',message,'',4)))
                    finally:self.busy=False;self.c.events.put(('skills_show',message))
                threading.Thread(target=work,daemon=True).start()
        except Exception as e:self.show(str(e))
    def receive(self,message):
        p=message['payload'];rid=p['request_id']
        if message['id'] in self.c.state['handled']:
            self.c.acks.append(message['id']);return
        self.c.state['handled']=(self.c.state['handled']+[message['id']])[-200:];self.c.acks.append(message['id']);self.c.save()
        if int(p.get('expires_at','0')) < int(time.time()*1000):self.publish(rid,'failed','Request expired; nothing was run.');return
        if p['query']=='teach':self.c.events.put(('skills_show','Choose files and show Pico your example result here.'));self.publish(rid,'ready','Continue on your Mac: choose files and show Pico your example result.');return
        if p['query']=='catalog':self.publish(rid);return
        if self.busy:self.publish(rid,'failed','Another routine is already working.');return
        self.action({'choice':'run','id':p['query'][4:],'request_id':rid,'confirmed':True})
