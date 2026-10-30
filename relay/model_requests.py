"""One explicit phone request -> one bounded model plan -> existing device mailbox."""
import os
import uuid
from datetime import datetime,timezone
from .service import ApiError
from .model_access import require_model_owner
from .model_budget import BudgetDenied


def create(service,owner,body):
    try:require_model_owner(owner)
    except BudgetDenied as error:raise ApiError(403,str(error)) from None
    device=service.owned(owner,str(uuid.UUID(str(body.get('device_id','')))))
    text=body.get('text','')
    if not isinstance(text,str) or not 1<=len(text.strip())<=1000:raise ApiError(400,'Use a request below 1,000 characters.')
    if os.environ.get('PICO_MODEL_ENABLED')!='1':raise ApiError(503,'AI planning is off. Basic commands still work.')
    try:
        seen=datetime.fromisoformat(device['last_seen'].replace('Z','+00:00'))
        if (datetime.now(timezone.utc)-seen).total_seconds()>30:raise ValueError()
    except (KeyError,ValueError,TypeError):raise ApiError(409,'Your computer must be online before an AI request.') from None
    request_id=str(uuid.UUID(str(body.get('request_id',''))))
    from server.agent.planner import plan
    from server.config import muse_config
    tools=[{'name':'open_app','description':'Open an app by its exact name. Desktop approval is required.','args':{'app':{'required':True}},'available':True}]
    if device.get('os')=='macos':tools.append({'name':'search_documents','description':'Search file names in explicitly granted read-only folders.','args':{'query':{'required':True}},'available':True})
    modern=service.jobs.catalog(owner,device['id']).get('workflow_version')==2
    extra=[
        ('fs_write','Draft a short text file. Generate its content. Human review and write access are required.',{'path':{'required':True},'content':{'required':True},'base_revision':{'required':False}}),
        ('fs_read','Read a relative file in an approved folder.',{'path':{'required':True}}),
        ('fs_list','List an approved folder.',{'path':{'required':False}}),
        ('organize_photos','Copy unique photos to a folder, preserving originals. Requires human review.',{'folder':{'required':True}}),
        ('open_document','Open a uniquely matched document. Requires human review.',{'query':{'required':True}}),
        ('open_website','Open an HTTPS website. Requires human review.',{'url':{'required':True}}),
        ('process_run','Run an executable with explicit arguments encoded as a JSON string array. No shell. Requires exact local approval.',{'argv_json':{'required':True},'cwd':{'required':False},'timeout_s':{'required':False}})]
    if modern:
        if not any(t['name']=='search_documents' for t in tools):tools.append({'name':'search_documents','description':'Search approved folders by filename.','args':{'query':{'required':True}},'available':True})
        tools.extend({'name':n,'description':d,'args':a,'available':True} for n,d,a in extra)
    output=plan({'id':request_id,'owner':owner,'input':text},tools,muse_config())
    if 'error' in output:raise ApiError(503,output['error'])
    if 'question' in output:return {'question':output['question']}
    call=output.get('tool_call',{});tool=call.get('tool');args=call.get('arguments',{})
    spec=next((t for t in tools if t['name']==tool),None)
    if not spec or not isinstance(args,dict) or set(args)-set(spec['args']):raise ApiError(400,'Pico could not create an enabled action.')
    kinds={'open_app':'open_app','search_documents':'find_document','fs_read':'read_file','fs_list':'list_files','fs_write':'create_note','organize_photos':'organize_photos','open_document':'open_document','open_website':'open_website','process_run':'run_command'}
    kind=kinds[tool]
    if tool=='fs_write':
        kind='edit_file' if args.get('base_revision') else 'create_note'
        args={'name':args.get('path'),'text':args.get('content',''),**({'base_revision':args['base_revision']} if args.get('base_revision') else {})}
    if body.get('grant_id'):args['grant_id']=body['grant_id']
    from .workflows import create as create_task,REVIEW
    return {'task':create_task(service,owner,device['id'],body.get('session_id'),kind,args,proposal=kind in REVIEW)}
