"""The character is the desktop UI. Pairing, resume cards and permissions are small windows."""
import argparse
import json
import os
import queue
import re
import socket
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageSequence
from client import DeviceClient,DeviceError
from head_start import prepare
from app_access import approved_apps, catalog, open_selected

from paths import resource_root
ROOT=resource_root()

class Companion:
    def __init__(self, platform, base, directory):
        self.platform=platform;self.base=base;self.directory=Path(directory)
        self.directory.mkdir(mode=0o700,parents=True,exist_ok=True)
        self.config=self.directory/'connection.json';self.state_file=self.directory/'places.json'
        self.lock=threading.RLock();self.events=queue.Queue();self.stopped=threading.Event();self.acks=[]
        self.state={'places':{},'allowed_apps':[],'grants':[],'task_journal':{},'handled':[],'outgoing':[],'character':'tuck','size':'medium','idle_minutes':2,'snapshots':False,'excluded_apps':[],'notice_idle':True,'prepare':False,'share_snapshot':False,'reopen':True,'retention_days':7,'paused_until':0}
        if self.state_file.exists():
            self.state.update(json.loads(self.state_file.read_text()))
        if self.state.get('character') not in ('tuck','mica'):
            self.state['character']='tuck'
            self.save()
        if 'never' in self.state:
            self.state.pop('never')
            self.state['snapshots']=False
            self.save()  # Old free-text exclusions need review in the new app picker.
        self.state['allowed_apps']=approved_apps(self.state.get('allowed_apps', []))
        self.state.setdefault('grants',[])
        self.running_tasks={};self.cancelled_tasks=set();self.approvals={}
        self.recover_tasks()
        self.root=tk.Tk();self.root.withdraw();self.root.title('Pico')
        if hasattr(platform, 'configure_background_app'):platform.configure_background_app()
        self.mood='idle';self.mood_until=0;self.frames=[];self.frame=0;self.card=None;self.native_card_id=None
        self.client=DeviceClient.load(self.config) if self.config.exists() else None
        if self.client:self.bind_device(self.client)
        self.overlay = platform.start_overlay(self.events) if hasattr(platform, 'start_overlay') else None
        self.background=platform.configure_window(self.root)
        self.root.overrideredirect(True);self.root.attributes('-topmost',True)
        self.label=tk.Label(self.root,bg=self.background,borderwidth=0,highlightthickness=0);self.label.pack()
        self.root.bind('<ButtonPress-1>',self.drag_start);self.root.bind('<B1-Motion>',self.drag)
        self.menu=tk.Menu(self.root,tearoff=0)
        self.menu.add_command(label='Pico permissions',command=self.permissions)
        self.menu.add_command(label='Parked Places',command=self.show_parked)
        self.menu.add_command(label='Unpair',command=self.unpair)
        self.menu.add_command(label='Quit Pico',command=self.quit)
        for binding in ('<Button-3>','<Control-Button-1>'):
            self.root.bind(binding,lambda event:self.menu.tk_popup(event.x_root,event.y_root))
        self.load_character();self.root.geometry(f'+{self.root.winfo_screenwidth()-240}+{self.root.winfo_screenheight()-260}')
        if not self.overlay:
            self.root.deiconify();self.root.after(100,self.animate)
        self.root.after(150,self.process_events)
        if self.client:self.start_worker()
        else:self.root.after(200,self.pairing)
        self.root.mainloop()

    def save(self):
        with self.lock:
            temporary=self.state_file.with_suffix('.tmp');temporary.write_text(json.dumps(self.state));os.chmod(temporary,0o600);temporary.replace(self.state_file)

    def load_character(self):
        if self.overlay:
            self.overlay.stdin.write(json.dumps({'character':self.state['character'],'size':self.state['size'],'mood':self.mood})+'\n')
            self.overlay.stdin.flush()
            return
        size={'small':138,'medium':184,'large':224}.get(self.state['size'],184)
        file=ROOT/'assets/characters'/self.state['character']/(self.mood+'.gif')
        frames=[]
        with Image.open(file) as image:
            for frame in ImageSequence.Iterator(image):
                frames.append(ImageTk.PhotoImage(frame.convert('RGBA').resize((size,size),Image.Resampling.LANCZOS)))
                if len(frames)>=100:break
        self.frames=frames;self.frame=0
        self.label.configure(width=size,height=size)

    def present(self, mood='idle', text='', place_id='', seconds=12):
        self.mood=mood;self.mood_until=time.time()+seconds if mood!='idle' else 0
        self.load_character()
        if self.overlay and text:
            self.overlay_message({'command':'reply','text':text,'place_id':place_id,'mood':mood})

    def animate(self):
        if self.frames:
            self.label.configure(image=self.frames[self.frame%len(self.frames)]);self.frame+=1
        self.root.after(90,self.animate)

    def overlay_message(self, value):
        self.overlay.stdin.write(json.dumps(value)+'\n');self.overlay.stdin.flush()

    def native_pair(self, code):
        def work():
            try:
                client=DeviceClient(self.base);client.claim(code,self.platform.OS,socket.gethostname());client.save(self.config)
                self.events.put(('native_paired',client))
            except Exception:
                self.events.put(('native_pair_error','Could not connect. Get a fresh code and try again.'))
        threading.Thread(target=work,daemon=True).start()

    def pairing(self):
        if self.overlay:
            self.overlay_message({'command':'pairing'});return
        window=tk.Toplevel(self.root);window.title('Connect Pico');window.configure(bg='#F5F1EE');window.resizable(False,False)
        frame=tk.Frame(window,bg='#F5F1EE',padx=12,pady=12);frame.pack()
        tk.Label(frame,text='Connect your phone',font=('Helvetica',20),bg='#F5F1EE',fg='#2B2220').pack(pady=12)
        tk.Label(frame,text='Enter the 6-digit code from Pico on your phone.',bg='#F5F1EE',fg='#746763').pack(pady=12)
        code=tk.StringVar();field=tk.Entry(frame,textvariable=code,font=('Helvetica',22),justify='center',width=12);field.pack(pady=12);field.focus_set()
        status=tk.StringVar();tk.Label(frame,textvariable=status,wraplength=320,bg='#F5F1EE',fg='#962C30').pack(pady=12)
        def connect():
            button.configure(state='disabled');status.set('Connecting…')
            def work():
                try:
                    client=DeviceClient(self.base);client.claim(code.get().strip(),self.platform.OS,socket.gethostname());client.save(self.config)
                    self.events.put(('paired',(client,window)))
                except Exception as error:self.events.put(('pair_error',(button,status,str(error))))
            threading.Thread(target=work,daemon=True).start()
        button=tk.Button(frame,text='Connect',command=connect,bg='#B83835',fg='#FFFFFF',padx=24,pady=12);button.pack(fill='x',pady=12)
        field.bind('<Return>',lambda _:connect())

    def start_worker(self):
        threading.Thread(target=self.poll,daemon=True).start()

    def poll(self):
        away=False
        while not self.stopped.is_set() and self.client:
            try:
                client=self.client
                result=client.post('/agent/poll',{'capabilities':__import__('task_execution').capabilities(self.state)})
                for message in result['mail']:self.events.put(('mail',message))
                with self.lock:
                    acks=list(self.acks);outgoing=list(self.state['outgoing'])
                if acks:
                    client.post('/agent/ack',{'ids':acks})
                    with self.lock:self.acks=[id for id in self.acks if id not in acks]
                for message in outgoing:
                    self.deliver_message(client,message)
                    with self.lock:self.state['outgoing']=[m for m in self.state['outgoing'] if m['id']!=message['id']]
                    self.save()
                info=self.platform.context()
                if self.state['notice_idle'] and time.time()>self.state['paused_until']:
                    idle=info.get('idle',0)>=self.state['idle_minutes']*60
                    if idle and not away:self.hold_context(info)
                    if away and not idle:self.events.put(('return',None))
                    away=idle
                self.purge_snapshots()
            except PermissionError:
                self.events.put(('revoked',None));return
            except Exception:
                pass  # Local Places remain available through a network outage.
            self.stopped.wait(1)

    def deliver_message(self,client,message):
        try:client.post('/agent/mail',message)
        except DeviceError as error:
            # Clearing phone history deletes the task row. Its late result must
            # not permanently block later valid results in the durable outbox.
            if error.status!=404 or message.get('kind')!='tool_result':raise

    def hold_context(self, info):
        id=str(uuid.uuid4());snapshot=None
        blocked=any(app.get('bundle')==info.get('bundle') for app in self.state['excluded_apps']) or any(word in info.get('title','').lower() for word in ['incognito','private browsing'])
        if self.state['snapshots'] and info.get('screen_access') and not blocked:
            folder=Path.home()/'Pictures/PICO Places';folder.mkdir(parents=True,exist_ok=True)
            snapshot=folder/(datetime.now().strftime('%Y-%m-%d_%H%M%S')+'_'+id[:8]+'.png')
            try:
                capture=self.platform.context(snapshot, [a.get('bundle','') for a in self.state['excluded_apps']])
                if not capture.get('snapshot_saved'):snapshot=None
                else:info={**info,**capture}
            except Exception:snapshot=None
        with self.lock:
            self.state['places'][id]={'id':id,'app':info.get('app',''),'bundle':info.get('bundle',''),'snapshot':str(snapshot) if snapshot else None,'sentence':'','status':'waiting','created':time.time()}
            self.state['outgoing'].append({'id':str(uuid.uuid4()),'kind':'idle','payload':{'place_id':id,'app':str(info.get('app',''))[:120]}})
        self.save()

    def consume(self, message):
        if message['kind']=='tool_call':
            self.consume_task(message);return
        if message['kind']=='cancel':
            task=message['payload'].get('task_id','');self.cancelled_tasks.add(task)
            callback=self.running_tasks.get(task)
            if callback:callback()
        id=message['id']
        with self.lock:
            if id in self.state['handled']:
                if id not in self.acks:self.acks.append(id)
                return
            data=message['payload']
            if message['kind']=='tool_call':
                self.execute_safe_task(data)
            elif message['kind']=='apps_request':self.queue_app_catalog()
            elif message['kind']=='open_app':
                if self.client and message.get('device_id')==self.client.device_id:
                    threading.Thread(target=self.open_application,args=(data.get('app_id',''),data.get('request_id'),data.get('expires_at','0')),daemon=True).start()
            elif message['kind']=='companion':
                if data.get('character') in ('tuck','mica'):self.state['character']=data['character']
                if data.get('size') in ('small','medium','large'):self.state['size']=data['size']
                mood=data.get('mood','idle')
                fresh=int(data.get('mood_until','0'))/1000>time.time()
                self.present(mood if fresh else 'idle', 'Listening on your phone…' if fresh and mood=='listening' else '', seconds=max(0,min(60,int(data.get('mood_until','0'))/1000-time.time())))
            elif message['kind']=='parked':
                place_id=data['place_id'];status=data.get('status','parked')
                if status not in ('parked','ready','finished'):return
                place=self.state['places'].setdefault(place_id,{'id':place_id,'created':time.time(),'sentence':'','bundle':'','snapshot':None})
                if place.get('status')=='finished':status='finished'
                place['status']=status
                if status=='finished':place['finished']=time.time()
                if status in ('finished','parked') and getattr(self,'native_card_id',None)==place_id:
                    if self.overlay:self.overlay_message({'command':'dismiss_reply'})
                elif status=='ready':self.show_card(place_id)
            elif message['kind']=='place':
                place_id=data['place_id'];place=self.state['places'].get(place_id,{'id':place_id,'created':time.time(),'bundle':'','snapshot':None})
                place.update(sentence=data['sentence'],status=place.get('status') if place.get('status') in ('parked','finished') else 'ready');self.state['places'][place_id]=place
                if place.get('snapshot'):
                    old=Path(place['snapshot']);slug=re.sub(r'[^a-z0-9]+','-',place['sentence'].lower()).strip('-')[:50] or 'place'
                    renamed=old.with_name(old.stem+'_'+slug+'.png')
                    if old.exists():old.rename(renamed);place['snapshot']=str(renamed)
                if place['status']=='ready':
                    threading.Thread(target=self.draft,args=(place_id,),daemon=True).start()
                    self.show_card(place_id)
            self.state['handled']=(self.state['handled']+[id])[-200:]
            self.acks.append(id)
        self.save()  # Durable local receipt before the server deletes the message.

    def bind_device(self,client,fresh=False):
        previous=self.state.get('paired_device')
        if previous!=client.device_id and (previous or fresh):
            archive=self.directory/'account-history';archive.mkdir(mode=0o700,exist_ok=True)
            file=archive/(str(uuid.uuid4())+'.json');file.write_text(json.dumps(self.state));os.chmod(file,0o600)
            for key,empty in [('places',{}),('outgoing',[]),('handled',[]),('task_journal',{}),('grants',[]),('allowed_apps',[])]:self.state[key]=empty
            self.acks=[]
        self.state['paired_device']=client.device_id;self.save()

    def recover_tasks(self):
        for mail,entry in self.state.setdefault('task_journal',{}).items():
            if entry.get('status')=='running':
                payload=entry['payload'];entry['status']='interrupted'
                self.state['outgoing'].append({'id':str(uuid.uuid4()),'kind':'tool_result','payload':{'task_id':payload['task_id'],'call_id':payload['call_id'],'status':'failed','error_code':'interrupted','message':'Pico restarted during this action. Check the computer before retrying; no automatic repeat.'}})
                self.state['handled']=(self.state['handled']+[mail])[-200:]
        self.save()

    def consume_task(self,message):
        mail=message['id'];payload=message['payload'];task=payload['task_id']
        with self.lock:
            journal=self.state.setdefault('task_journal',{})
            if mail in self.state['handled']:
                if mail not in self.acks:self.acks.append(mail)
                return
            if journal.get(mail,{}).get('status')=='running':return
            journal[mail]={'status':'running','payload':payload};self.save()
        result=self.execute_safe_task(payload)
        with self.lock:
            journal[mail]={'status':'finished'}
            self.state['handled']=(self.state['handled']+[mail])[-200:]
            self.state['outgoing'].append({'id':str(uuid.uuid4()),'kind':'tool_result','payload':result})
            self.save()
            self.acks.append(mail)
            for old in list(journal)[:-200]:journal.pop(old,None)

    def approve_task(self,review):
        identity=str(uuid.uuid4());event=threading.Event();answer={'event':event,'allowed':False}
        self.approvals[identity]=answer
        self.events.put(('task_approval',{'id':identity,**review}))
        event.wait(45);self.approvals.pop(identity,None)
        return answer['allowed']

    def execute_safe_task(self, payload):
        from task_execution import execute
        task=payload['task_id']
        if not hasattr(self,'running_tasks'):self.running_tasks={}
        if not hasattr(self,'cancelled_tasks'):self.cancelled_tasks=set()
        cancelled=lambda:task in self.cancelled_tasks
        def register(fn):
            self.running_tasks[task]=fn
            if cancelled():fn()
        result=execute(payload,self.state,self.platform,lambda:self.events.put(('show_permissions',None)),client=self.client,approve=self.approve_task,cancelled=cancelled,register_cancel=register,unregister_cancel=lambda:self.running_tasks.pop(task,None))
        self.events.put(('presentation',('done' if result['status']=='succeeded' else 'stuck',result.get('message','Request finished.'),None)))
        return result

    def queue_app_catalog(self):
        with self.lock:
            self.state['outgoing']=[m for m in self.state['outgoing'] if m.get('kind')!='app_catalog']
            self.state['outgoing'].append({'id':str(uuid.uuid4()),'kind':'app_catalog','payload':catalog(self.state)})
        self.save()

    def open_application(self, identity, request_id=None, expires_at=None):
        success,message=open_selected(self.state,identity,self.platform,expires_at)
        if request_id:
            with self.lock:
                self.state['outgoing'].append({'id':str(uuid.uuid4()),'kind':'app_result','payload':{'app_id':identity,'request_id':request_id,'result':'opened' if success else 'failed','message':message}})
            self.save()
        self.events.put(('presentation',('done' if success else 'stuck',message,'')))

    def reopen_approved(self, bundle):
        app=next((a for a in self.state['allowed_apps'] if a['bundle']==bundle),None)
        if app:threading.Thread(target=self.open_application,args=(app['id'],),daemon=True).start()

    def applications(self):
        if self.overlay:
            self.overlay_message({'command':'applications','payload':json.dumps(self.state)})

    def draft(self, id):
        with self.lock:place=dict(self.state['places'][id])
        enabled=self.state['prepare'] and bool(os.environ.get('MUSE_API_URL') and os.environ.get('MUSE_API_KEY'))
        if enabled:self.events.put(('presentation',('working','Preparing your next step…',id)))
        try:result=prepare(place['sentence'],self.state['character'],place.get('snapshot') if self.state['share_snapshot'] and not any(a.get('bundle')==place.get('bundle') for a in self.state['excluded_apps']) else None) if self.state['prepare'] else None
        except Exception:result=None
        if result:
            with self.lock:
                self.state['places'][id]['head_start']=result
                self.state['outgoing'].append({'id':str(uuid.uuid4()),'kind':'head_start','payload':{'place_id':id,'head_start':result}})
            self.save();self.events.put(('draft',id))
        elif enabled:self.events.put(('presentation',('idle','Your place is saved.',id)))

    def show_card(self, id, details=False):
        place=self.state['places'][id]
        if not place.get('sentence') or place.get('status')=='finished':return
        if self.overlay:
            self.native_card_id=id
            if not details:
                self.present('talking' if place.get('head_start') else 'idle', place.get('head_start') or place['sentence'], id)
                return
            self.overlay_message({'command':'welcome','payload':json.dumps({'id':id,'sentence':place['sentence'],**({'head_start':place['head_start']} if place.get('head_start') else {})})});return
        if self.card and self.card.winfo_exists():self.card.destroy()
        card=tk.Toplevel(self.root);self.card=card;card.title('Welcome back');card.configure(bg='#F5F1EE');card.attributes('-topmost',True)
        frame=tk.Frame(card,bg='#F5F1EE',padx=12,pady=12);frame.pack()
        tk.Label(frame,text='Welcome back',font=('Helvetica',20),bg='#F5F1EE',fg='#2B2220').pack(pady=12)
        tk.Label(frame,text=place['sentence'],wraplength=340,justify='left',bg='#F5F1EE',fg='#2B2220').pack(fill='x',pady=12)
        tk.Label(frame,text=place.get('head_start') or 'Your place is saved. Head Start is not connected.',wraplength=340,justify='left',bg='#F5F1EE',fg='#746763').pack(fill='x',pady=12)
        actions=tk.Frame(frame,bg='#F5F1EE');actions.pack(fill='x',pady=12);actions.columnconfigure((0,1),weight=1,uniform='actions')
        def resume():
            self.root.clipboard_clear();self.root.clipboard_append(place.get('head_start') or place['sentence']);self.root.update()
            if self.state['reopen']:self.reopen_approved(place.get('bundle'))
            place.update(status='finished',finished=time.time());self.save();card.destroy()
        def park():
            place['status']='parked'
            with self.lock:self.state['outgoing'].append({'id':str(uuid.uuid4()),'kind':'parked','payload':{'place_id':id,'sentence':place['sentence']}})
            self.save();card.destroy()
        tk.Button(actions,text='Continue',command=resume,padx=12,pady=12).grid(row=0,column=0,sticky='ew',padx=(0,6))
        tk.Button(actions,text='Park it',command=park,padx=12,pady=12).grid(row=0,column=1,sticky='ew',padx=(6,0))

    def show_parked(self):
        for id,place in reversed(list(self.state['places'].items())):
            if place.get('status')=='parked':self.show_card(id);return
        if self.overlay:self.overlay_message({'command':'notice','payload':json.dumps({'message':'No parked Places.'})})
        else:messagebox.showinfo('Pico','No parked Places.',parent=self.root)

    def permissions(self):
        if self.overlay:
            self.overlay_message({'command':'permissions','payload':json.dumps({key:self.state[key] for key in ['notice_idle','idle_minutes','snapshots','prepare','share_snapshot','reopen','excluded_apps','retention_days','allowed_apps','grants']} | {'model_configured':bool(os.environ.get('MUSE_API_URL') and os.environ.get('MUSE_API_KEY')),'paired':self.client is not None})});return
        window=tk.Toplevel(self.root);window.title('Pico permissions');window.configure(bg='#F5F1EE')
        frame=tk.Frame(window,bg='#F5F1EE',padx=12,pady=12);frame.pack(fill='both',expand=True)
        tk.Label(frame,text='Hold my place',font=('Helvetica',18),bg='#F5F1EE').pack(anchor='w',pady=12)
        minutes=tk.IntVar(value=self.state['idle_minutes'])
        for value in (1,2,5):tk.Radiobutton(frame,text=f'After {value} minutes',variable=minutes,value=value,bg='#F5F1EE').pack(anchor='w')
        snapshots=tk.TuckleanVar(value=self.state['snapshots'])
        tk.Checkbutton(frame,text='Snapshot the active window (requires screen access)',variable=snapshots,bg='#F5F1EE').pack(anchor='w',pady=12)
        tk.Label(frame,text='Never snapshot apps containing these names (one per line)',bg='#F5F1EE').pack(anchor='w',pady=12)
        excluded=tk.Text(frame,width=42,height=5);excluded.insert('1.0','\n'.join([app['name'] for app in self.state['excluded_apps']]));excluded.pack(fill='x')
        tk.Label(frame,text='Pictures/PICO Places · Finished snapshots kept 7 days\nPico always asks first.',bg='#F5F1EE',justify='left').pack(anchor='w',pady=12)
        def done():
            self.state.update(idle_minutes=minutes.get(),snapshots=snapshots.get(),excluded_apps=[{'name':s.strip(),'bundle':s.strip()} for s in excluded.get('1.0','end').splitlines() if s.strip()]);self.save();window.destroy()
        def pause():self.state['paused_until']=time.time()+3600;self.save();window.destroy()
        tk.Button(frame,text='Pause Pico for 1 hour',command=pause).pack(fill='x',pady=12)
        tk.Button(frame,text='Done',command=done).pack(fill='x',pady=12)

    def native_panel(self, value):
        action=value.get('action')
        if action=='task_approval':
            answer=self.approvals.get(value.get('id'))
            if answer:
                answer['allowed']=value.get('allowed') is True;answer['event'].set()
        elif action=='preferences':
            settings=value.get('values',{})
            for key in ['notice_idle','snapshots','prepare','share_snapshot','reopen']:
                if isinstance(settings.get(key),bool):self.state[key]=settings[key]
            for key,choices in [('idle_minutes',(1,2,5)),('retention_days',(1,7,30))]:
                if settings.get(key) in choices:self.state[key]=settings[key]
            apps=settings.get('excluded_apps',[])
            if isinstance(apps,list):self.state['excluded_apps']=[{'name':str(app['name'])[:120],'bundle':str(app['bundle'])[:200]} for app in apps[:100] if isinstance(app,dict) and app.get('name') and app.get('bundle')]
            self.state['allowed_apps']=approved_apps(settings.get('allowed_apps',self.state['allowed_apps']))
            self.state['grants']=[{'path':str(Path(g['path']).resolve()),'access':'write' if g.get('access')=='write' else 'read'} for g in settings.get('grants',self.state['grants']) if isinstance(g,dict) and isinstance(g.get('path'),str) and g['path'] and Path(g['path']).is_dir()][:20]
            self.save();self.queue_app_catalog()
        elif action=='permissions':self.permissions()
        elif action=='open_app':
            threading.Thread(target=self.open_application,args=(value.get('id',''),),daemon=True).start()
        elif action=='open_place':
            if value.get('id') in self.state['places']:self.show_card(value['id'],details=True)
        elif action=='place_action':
            self.native_card_id=None
            place=self.state['places'].get(value.get('id'))
            if not place:return
            if value.get('choice')=='continue':
                place.update(status='finished',finished=time.time())
                if self.state['reopen']:self.reopen_approved(place.get('bundle'))
            elif value.get('choice')=='park':
                place['status']='parked'
                self.state['outgoing'].append({'id':str(uuid.uuid4()),'kind':'parked','payload':{'place_id':value['id'],'sentence':place['sentence']}})
            self.save();self.present()
            self.overlay_message({'command':'dismiss_reply'})
        elif action=='pause':self.state['paused_until']=time.time()+3600;self.save()
        elif action=='unpair':self.unpair()
        elif action=='clear_snapshots':
            folder=(Path.home()/'Pictures/PICO Places').resolve()
            for place in self.state['places'].values():
                if place.get('snapshot'):
                    file=Path(place['snapshot']).resolve()
                    if file.is_relative_to(folder):file.unlink(missing_ok=True);place['snapshot']=None
            self.save()

    def purge_snapshots(self):
        folder=(Path.home()/'Pictures/PICO Places').resolve()
        for place in self.state['places'].values():
            if place.get('finished') and time.time()-place['finished']>self.state['retention_days']*86400 and place.get('snapshot'):
                file=Path(place['snapshot']).resolve()
                if file.is_relative_to(folder):file.unlink(missing_ok=True)

    def unpair(self):
        if not self.client:return
        if not self.overlay and not messagebox.askyesno('Unpair Pico','Disconnect this computer from your phone?',parent=self.root):return
        client=self.client
        def work():
            try:client.post('/agent/revoke',{});self.events.put(('revoked',None))
            except Exception:self.events.put(('notice','Could not unpair. Check your connection.'))
        threading.Thread(target=work,daemon=True).start()

    def process_events(self):
        try:
            if self.mood_until and time.time()>self.mood_until:self.present()
            while True:
                kind,value=self.events.get_nowait()
                if kind=='overlay_action':
                    {'permissions':self.permissions,'applications':self.applications,'parked':self.show_parked,'unpair':self.unpair,'quit':self.quit}[value]()
                    if value=='quit':return
                elif kind=='native_panel':self.native_panel(value)
                elif kind=='native_pair':self.native_pair(value)
                elif kind=='native_paired':
                    self.bind_device(value,fresh=True);self.client=value;self.overlay_message({'command':'paired'});self.start_worker()
                elif kind=='native_pair_error':self.overlay_message({'command':'pair_status','message':value,'busy':'false'})
                elif kind=='paired':
                    client,window=value;self.bind_device(client,fresh=True);self.client=client;window.destroy();self.start_worker()
                elif kind=='pair_error':button,status,message=value;button.configure(state='normal');status.set(message)
                elif kind=='presentation':self.present(*value)
                elif kind=='mail':
                    if value.get('kind')=='tool_call':threading.Thread(target=self.consume,args=(value,),daemon=True).start()
                    else:self.consume(value)
                elif kind=='task_approval':
                    if self.overlay:self.overlay_message({'command':'approval','payload':json.dumps(value)})
                    else:
                        answer=self.approvals.get(value['id'])
                        if answer:
                            answer['allowed']=messagebox.askyesno('Approve Pico action',json.dumps(value,indent=2),parent=self.root);answer['event'].set()
                elif kind=='show_permissions':self.permissions()
                elif kind=='return':
                    for id,place in reversed(list(self.state['places'].items())):
                        if place.get('status') in ('ready','parked'):self.show_card(id);break
                elif kind=='draft':
                    if self.overlay and self.native_card_id==value:self.show_card(value)
                    if self.card and self.card.winfo_exists():self.show_card(value)
                elif kind=='revoked':
                    self.client=None;self.config.unlink(missing_ok=True)
                    if self.card and self.card.winfo_exists():self.card.destroy()
                    self.pairing()
                elif kind=='notice':
                    if self.overlay:self.overlay_message({'command':'notice','payload':json.dumps({'message':value})})
                    else:messagebox.showinfo('Pico',value,parent=self.root)
        except queue.Empty:pass
        except Exception as error:
            # A failed panel must not stop future character and mailbox updates.
            import logging
            logging.getLogger(__name__).error('Companion presentation failed: %s', type(error).__name__)
        finally:
            if not self.stopped.is_set():self.root.after(150,self.process_events)

    def drag_start(self,event):self._drag=(event.x_root-self.root.winfo_x(),event.y_root-self.root.winfo_y())
    def drag(self,event):self.root.geometry(f'+{event.x_root-self._drag[0]}+{event.y_root-self._drag[1]}')
    def quit(self):
        self.stopped.set()
        if self.overlay:
            self.overlay.stdin.close();self.overlay.terminate()
        self.root.destroy()


def bundled_relay():
    config=ROOT/'config/companion.json'
    return json.loads(config.read_text())['relay'] if config.exists() else 'http://127.0.0.1:8765'

def run(platform):
    parser=argparse.ArgumentParser(description='Pico character companion')
    parser.add_argument('--relay',default=os.environ.get('PICO_RELAY_URL', bundled_relay()))
    parser.add_argument('--state',default=str(Path.home()/'.pico'))
    args=parser.parse_args();Companion(platform,args.relay,args.state)
