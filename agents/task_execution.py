"""Connected desktop tools: local grants, per-action confirmation, exact transfer evidence."""
import base64,hashlib,json,time
from pathlib import Path
from app_access import approved_apps,open_selected
from native_search import NativeError,transfer_evidence
from tools import TOOL_REGISTRY,ToolError
from handlers import dispatch,bounded_json
SAFE_TOOLS={'search_documents','read_back_file','fs_list','fs_read','fs_write','process_run','fetch_upload','organize_photos','open_document','open_website','open_app','manage_permissions','transfer_selected_file','convert_file','delete_files','restore_deleted','pdf_pages','rename_file','duplicate_file','archive','recent_files','search_contents','find_duplicates','largest_files','undo_edit','empty_trash','disk_usage'}
WRITE_TOOLS={'fs_write','process_run','fetch_upload','organize_photos','convert_file','restore_deleted','pdf_pages','rename_file','duplicate_file','archive','undo_edit'}
DELETE_TOOLS={'delete_files','empty_trash'}
REVIEW_TOOLS=WRITE_TOOLS|DELETE_TOOLS|{'open_document','open_website'}
ACCESS_RANK={'read':0,'write':1,'delete':2}
GRANT_ONCE_TOOLS={'search_documents','open_document'}
DEFAULT_GRANT_DIR=None
def _default_grant_dir():
 d=Path(DEFAULT_GRANT_DIR).expanduser() if DEFAULT_GRANT_DIR else Path.home()/'Documents'
 try:return d.resolve() if d.is_dir() else None
 except OSError:return None
APP_ALIASES={'browser':{'safari','google chrome','mozilla firefox','microsoft edge','brave','arc','browser','chrome','firefox','edge'},'chrome':{'google chrome','chrome','chromium'},'safari':{'safari'},'firefox':{'mozilla firefox','firefox'},'edge':{'microsoft edge','edge'},'files':{'finder','file explorer','files','explorer','file manager'},'terminal':{'terminal','command prompt','powershell','windows terminal'},'calculator':{'calculator'},'calendar':{'calendar'},'notes':{'notes','sticky notes','stickies'},'vscode':{'visual studio code','vscode','code'},'mail':{'mail','microsoft outlook','outlook'},'photos':{'photos','apple photos'},'music':{'music','apple music','spotify'},'messages':{'messages'},'facetime':{'facetime'},'maps':{'maps','apple maps'},'settings':{'settings','system settings','system preferences'},'appstore':{'app store','microsoft store'},'word':{'microsoft word','word'},'excel':{'microsoft excel','excel'},'powerpoint':{'microsoft powerpoint','powerpoint'}}
def grant_id(path):return hashlib.sha256(str(Path(path).resolve()).encode()).hexdigest()[:32]
def capabilities(state):
 return {'workflow_version':2,'workspaces':[{'id':grant_id(g['path']),'name':Path(g['path']).name,'access':g.get('access','read')} for g in state.get('grants',[]) if isinstance(g,dict) and g.get('path') and Path(g['path']).is_dir() and Path(g['path']).resolve()==Path(g['path']).absolute()]}
def execute(payload,state,platform,notify=lambda:None,client=None,approve=None,cancelled=lambda:False,register_cancel=None,unregister_cancel=None):
 tool=payload.get('tool','');result={'task_id':str(payload.get('task_id','')),'call_id':str(payload.get('call_id',''))}
 try:
  if int(payload.get('expires_at','0'))<int(time.time()*1000):raise NativeError('timeout','This request expired. Send it again.')
  if cancelled():raise NativeError('cancelled','Cancelled before execution.')
  start=client.post('/agent/start',{'task_id':payload['task_id']}) if client is not None and hasattr(client,'post') else {}
  if start.get('cancelled'):raise NativeError('cancelled','This request was cancelled.')
  if tool not in SAFE_TOOLS:raise NativeError('unsupported_tool','This tool is not enabled in the desktop companion.')
  if tool=='open_app':
   query=payload.get('app_id') or payload.get('app','');apps=approved_apps(state.get('allowed_apps',[]))
   names=APP_ALIASES.get(str(query).casefold(),{str(query).casefold()})
   match=next((a for a in apps if a['id']==query or a['name'].casefold() in names),None)
   if match is None:raise NativeError('permission_denied','Choose this app in the computer’s Open apps menu first.')
   ok,message=open_selected(state,match['id'],platform,payload.get('expires_at','0'))
   if not ok:raise NativeError('permission_denied',message)
   data,evidence={'app':match['name']},{}
  else:
   grants=[dict(g) for g in state.get('grants',[]) if isinstance(g,dict) and isinstance(g.get('path'),str) and g['path'].strip() and Path(g['path']).is_dir() and Path(g['path']).resolve()==Path(g['path']).absolute()]
   if payload.get('grant_id'):grants=[g for g in grants if grant_id(g['path'])==payload['grant_id']]
   if tool not in ('manage_permissions','open_website') and not grants:
    folder=_default_grant_dir()
    asked=False
    if tool in GRANT_ONCE_TOOLS and folder is not None and approve is not None:
     from grants import record as _record
     asked=True
     if approve({'tool':'grant_folder','folder':str(folder),'arguments':{'path':str(folder),'access':'read','why':tool+' needs a folder to search'},'task_id':payload.get('task_id','')}):
      entry=_record(folder,'read','approval');state.setdefault('grants',[]).append(entry);grants=[entry];result['grant_added']=True
    if not grants:raise NativeError('permission_denied','Approve the folder request on your computer, then ask again.' if asked else 'Choose a folder in the computer permissions first.')
   if tool in WRITE_TOOLS:
    grants=[g for g in grants if ACCESS_RANK.get(g.get('access','read'),0)>=1]
    if not grants:raise NativeError('permission_denied','Choose a folder with write access on this computer first.')
   if tool in DELETE_TOOLS:
    grants=[g for g in grants if g.get('access')=='delete']
    if not grants:raise NativeError('permission_denied','Choose a folder with delete access on this computer first.')
   args=TOOL_REGISTRY.validate(tool,payload)
   if tool=='process_run':
    argv=json.loads(args['argv_json'])
    if not isinstance(argv,list) or not argv or Path(argv[0]).name.lower() in ('sh','bash','zsh','cmd','cmd.exe','powershell','powershell.exe','pwsh'):raise NativeError('permission_denied','Shell commands are disabled. Use an executable with explicit arguments.')
   if tool=='fs_read':
    from workspace import Workspace
    file=Workspace(grants[0]['path']).resolve(args['path'])
    if file.is_file() and file.stat().st_size>1048576:raise NativeError('permission_denied','Read files up to 1 MB in this preview.')
   for key in ('path','cwd'):
    if key in args and any(p.startswith('.') and p not in ('.','..') for p in Path(args[key]).parts):raise NativeError('permission_denied','Hidden files are outside this workflow.')
   if tool in REVIEW_TOOLS:
    review={'tool':tool,'arguments':args,'folder':str(Path(grants[0]['path']).resolve()) if grants else '', 'task_id':payload.get('task_id','')}
    phone_approved=start.get('phone_approved') is True and tool!='process_run'
    if not phone_approved and (approve is None or not approve(review)):raise NativeError('permission_denied','Not approved on this computer.')
    if client is not None and hasattr(client,'post') and client.post('/agent/start',{'task_id':payload['task_id']}).get('cancelled'):raise NativeError('cancelled','This request was cancelled.')
    need='delete' if tool in DELETE_TOOLS else ('write' if tool in WRITE_TOOLS else None)
    if grants and not all(any(current.get('path')==g['path'] and (need is None or ACCESS_RANK.get(current.get('access','read'),0)>=ACCESS_RANK[need]) for current in state.get('grants',[])) for g in grants):raise NativeError('permission_denied','Folder permission changed before approval.')
    if cancelled() or int(payload['expires_at'])<int(time.time()*1000):raise NativeError('timeout','This request expired or was cancelled before approval.')
   def transfer(raw,ev):
    if client is None:raise NativeError('device_offline','Transfer connection unavailable.')
    if ev.get('digest')!=payload.get('expected_digest') or str(ev.get('size_bytes'))!=payload.get('expected_size'):raise NativeError('candidate_changed','The selected file changed. Search again before sending.')
    if cancelled():raise NativeError('cancelled','Transfer cancelled.')
    client.post('/agent/transfer',{'task_id':payload['task_id'],'approval_id':payload['approval_id'],'content_base64':base64.b64encode(raw).decode(),**ev})
   def fetch(identity):
    if client is None:raise NativeError('device_offline','Upload connection unavailable.')
    return base64.b64decode(client.post('/agent/artifact',{'id':identity})['content_base64'],validate=True)
   ctx={'grants':grants,'notify':notify,'transfer':transfer,'fetch_artifact':fetch,'cancelled':cancelled}
   if register_cancel:ctx.update(register_cancel=register_cancel,unregister_cancel=unregister_cancel or (lambda:None))
   data,evidence=dispatch(tool,args,ctx)
   if tool=='process_run' and (data.get('timed_out') or data.get('cancelled') or data.get('exit_code')!=0):raise NativeError('timeout' if data.get('timed_out') else 'process_failed','The command did not finish successfully. '+str(data.get('stderr',''))[:100])
  result.update(status='succeeded',data_json=bounded_json(data),evidence_json=bounded_json(evidence),message='Opened '+data['app']+'.' if tool=='open_app' else 'Request finished.')
 except (NativeError,ToolError) as error:result.update(status='failed',error_code=error.code,message=str(error.message)[:200])
 except Exception:result.update(status='failed',error_code='timeout',message='Couldn’t complete this request.')
 return result
