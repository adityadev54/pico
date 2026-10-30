"""Connect registered tools to persistent tasks and explicitly reviewed actions."""
import json,re,uuid,urllib.error
from .service import ApiError,identifier,clean_note_name
from .task_records import view
TOOLS={'find_document':'search_documents','send_file':'transfer_selected_file','open_website':'open_website','open_app':'open_app','manage_permissions':'manage_permissions','summarize_document':'read_back_file','read_document':'read_back_file','create_note':'fs_write','receive_upload':'fetch_upload','organize_photos':'organize_photos','open_document':'open_document','list_files':'fs_list','read_file':'fs_read','edit_file':'fs_write','run_command':'process_run'}
REVIEW={'create_note','edit_file','organize_photos','receive_upload','run_command','open_website','open_document'}
def text(value,limit=2000):
 if not isinstance(value,str) or len(value)>limit:raise ApiError(400,'Use a shorter text value.')
 return value

def prepare(service,owner,device,kind,source):
 if kind not in TOOLS or not isinstance(source,dict):raise ApiError(400,'Unsupported request.')
 src=dict(source);src.pop('_pico_kind',None);src.pop('_pico_phone_approved',None);payload={'task_id':str(uuid.uuid4()),'call_id':str(uuid.uuid4()),'tool':TOOLS[kind]}
 if src.get('grant_id'):payload['grant_id']=text(src['grant_id'],128)
 if kind=='find_document':payload['query']=text(src.get('query',''),500)
 elif kind=='open_app':payload['app']=text(src.get('app',''),64)
 elif kind=='open_website':
  from urllib.parse import urlsplit
  value=text(src.get('url',''));u=urlsplit(value)
  if u.scheme!='https' or not u.hostname or u.username or u.password:raise ApiError(400,'Use a public HTTPS address.')
  payload['url']=value
 elif kind in ('read_document','summarize_document','send_file'):
  try:parent_id=identifier(src.get('search_task_id'))
  except (ValueError,TypeError):raise ApiError(400,'Find and select the exact file first.') from None
  parents=service.db.db('tasks',{'id':'eq.'+parent_id,'user_id':'eq.'+owner,'device_id':'eq.'+device['id']})
  if parents:parents[0]=view(parents[0])
  if not parents or parents[0].get('kind')!='find_document' or parents[0].get('status') not in ('awaiting_approval','completed'):raise ApiError(400,'Find and select the exact file first.')
  candidate=next((c for c in (parents[0].get('result') or {}).get('candidates',[]) if c.get('candidate_id')==src.get('candidate_id')),None)
  if not candidate:raise ApiError(400,'Select a file from this search.')
  payload['candidate_id']=identifier(candidate['candidate_id']);src['candidate']=candidate
  if kind=='send_file':
   if not candidate.get('digest') or not 0<int(candidate.get('size_bytes',0))<=1048576:raise ApiError(400,'Choose a file between 1 byte and 1 MB.')
   src['approval_id']=str(uuid.uuid4());payload.update(approval_id=src['approval_id'],expected_digest=candidate['digest'],expected_size=str(candidate['size_bytes']))
 elif kind in ('create_note','edit_file'):
  payload.update(path=clean_note_name(src.get('name',src.get('path'))),content=text(src.get('text',src.get('content',''))))
  if kind=='edit_file':
   revision=src.get('base_revision','')
   if not re.fullmatch('[0-9a-f]{64}',revision):raise ApiError(400,'Read the current file revision before editing.')
   payload['base_revision']=revision
 elif kind=='receive_upload':
  if not re.fullmatch('[0-9a-f]{64}',str(src.get('artifact_id',''))):raise ApiError(400,'Invalid upload.')
  payload.update(artifact_id=src['artifact_id'],path=clean_note_name(src.get('name')))
 elif kind=='organize_photos':payload['folder']=clean_note_name(src.get('folder'))
 elif kind=='open_document':payload['query']=text(src.get('query',''),500)
 elif kind in ('list_files','read_file'):
  path=src.get('path','.')
  if not isinstance(path,str) or len(path)>512 or path.startswith(('/', '\\')) or '..' in path.split('/') or any(s.startswith('.') and s!='.' for s in path.split('/')):raise ApiError(400,'Use a visible file inside an approved folder.')
  payload['path']=path
 elif kind=='run_command':
  argv=src.get('argv');argv=json.loads(src['argv_json']) if argv is None and 'argv_json' in src else argv
  if not isinstance(argv,list) or not 1<=len(argv)<=30 or any(not isinstance(a,str) or not a or len(a)>300 for a in argv):raise ApiError(400,'Use a short argument list, without a shell.')
  payload.update(argv_json=text(json.dumps(argv)),cwd=text(src.get('cwd','.'),512),timeout_s=str(min(30,max(1,int(src.get('timeout_s',15))))))
 if kind in ('find_document','open_app','open_document') and not next((payload.get(k) for k in ('query','app') if payload.get(k) and payload[k].strip()),None):raise ApiError(400,'Name what you need.')
 if len(json.dumps(payload).encode())>12000:raise ApiError(400,'Shorten this request so it fits the secure task mailbox.')
 return payload,src

def dispatch(service,owner,device,payload):
 service.jobs.put(owner,device,payload)
 try:
  service.enqueue(owner,device,'tool_call',payload,payload['call_id']);service.jobs.sent(payload['task_id'])
 except (ApiError,OSError):pass

def create(service,owner,device_id,session_id,kind,input,proposal=False):
 device=service.owned(owner,identifier(device_id));payload,source=prepare(service,owner,device,kind,input)
 if kind in REVIEW and not proposal:source['_pico_phone_approved']=True
 result={'proposal':{'kind':kind,'input':source}} if proposal else {}
 record={'user_id':owner,'device_id':device['id'],'session_id':service.task_session(owner,session_id),'kind':kind,'input':source,'status':'awaiting_approval' if proposal else 'queued','result':result}
 try:rows=service.db.db('tasks',body=record,method='POST')
 except urllib.error.HTTPError as error:
  try:details=json.load(error)
  except Exception:raise error
  if error.code!=400 or details.get('code')!='23514' or 'tasks_kind_check' not in details.get('message','') or kind=='open_app':raise
  # Only a failed atomic INSERT is retried, before any tool is dispatched.
  # Preserve the real workflow in owned task metadata; shared schema stays intact.
  record={**record,'kind':'open_app','input':{**source,'_pico_kind':kind}}
  rows=service.db.db('tasks',body=record,method='POST')
 task=view(rows[0]);payload['task_id']=task['id']
 if not proposal:dispatch(service,owner,device['id'],payload)
 return task

def approve(service,owner,identity,grant_id=None):
 with service.lock:
  rows=service.db.db('tasks',{'id':'eq.'+identifier(identity),'user_id':'eq.'+owner})
  if not rows:raise ApiError(404,'Request not found.')
  stored_kind=rows[0]['kind'];task=view(rows[0])
  if task['status']!='awaiting_approval' or not (task.get('result') or {}).get('proposal'):raise ApiError(409,'This request was already decided.')
  if grant_id:task['input']={**task['input'],'grant_id':text(grant_id,128)}
  device=service.owned(owner,task['device_id']);payload,source=prepare(service,owner,device,task['kind'],task['input']);payload['task_id']=task['id']
  source['_pico_phone_approved']=True
  if stored_kind!=task['kind']:source['_pico_kind']=task['kind']
  service.db.db('tasks',{'id':'eq.'+task['id']},{'status':'queued','input':source,'result':{}},'PATCH')
  dispatch(service,owner,device['id'],payload)
 return {'ok':True}
