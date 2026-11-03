"""Public helper capability facts, with local paths deliberately excluded."""
def clean(value):
 workspaces=[]
 for g in value.get('workspaces',[])[:20]:
  if isinstance(g,dict) and isinstance(g.get('id'),str) and len(g['id'])<=128 and isinstance(g.get('name'),str):
   workspaces.append({'id':g['id'],'name':g['name'][:80],'access':g.get('access') if g.get('access') in ('read','write','delete') else 'read'})
 result = {'workflow_version':2 if value.get('workflow_version')==2 else 0,'workspaces':workspaces}
 tools = value.get('document_tools',[])
 if isinstance(tools,list) and tools:result['document_tools']=[t for t in tools[:2] if t in ('convert_file','pdf_pages')]
 file_tools=value.get('file_tools',[])
 if isinstance(file_tools,list) and file_tools:result['file_tools']=[t for t in file_tools[:4] if t in ('delete_files','restore_deleted','archive','empty_trash')]
 return result
