"""Durable dispatch outbox. Reuse call IDs; never automatically retry model calls."""
import json,time
class JobState:
 def __init__(self,state):
  self.state=state
  with state.connect() as db:
   db.execute('create table if not exists task_dispatch (id text primary key,owner text,device text,payload text,sent integer default 0,terminal integer default 0)')
   db.execute('create table if not exists helper_catalog (device text primary key,owner text,data text,at real)')
 def put(self,owner,device,payload):
  with self.state.connect() as db:db.execute('insert or ignore into task_dispatch(id,owner,device,payload) values(?,?,?,?)',(payload['task_id'],owner,device,json.dumps(payload)))
 def pending(self,owner,device):
  with self.state.connect() as db:return [json.loads(row[0]) for row in db.execute('select payload from task_dispatch where owner=? and device=? and sent=0 and terminal=0',(owner,device))]
 def sent(self,id):
  with self.state.connect() as db:db.execute('update task_dispatch set sent=1 where id=?',(id,))
 def stop(self,id):
  with self.state.connect() as db:db.execute('update task_dispatch set terminal=1 where id=?',(id,))
 def catalog(self,owner,device,value=None):
  with self.state.connect() as db:
   if value is not None:db.execute('insert or replace into helper_catalog values(?,?,?,?)',(device,owner,json.dumps(value),time.time()))
   row=db.execute('select data from helper_catalog where device=? and owner=?',(device,owner)).fetchone()
   return json.loads(row[0]) if row else {'workspaces':[],'workflow_version':0}
