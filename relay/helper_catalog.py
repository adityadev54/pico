"""Public helper capability facts, with local paths deliberately excluded."""
def clean(value):
 workspaces=[]
 for g in value.get('workspaces',[])[:20]:
  if isinstance(g,dict) and isinstance(g.get('id'),str) and len(g['id'])<=128 and isinstance(g.get('name'),str):
   workspaces.append({'id':g['id'],'name':g['name'][:80],'access':'write' if g.get('access')=='write' else 'read'})
 return {'workflow_version':2 if value.get('workflow_version')==2 else 0,'workspaces':workspaces}
