"""One learned file workflow: observe an example, save its recipe, repeat on new notes."""
import hashlib,json,os,threading,time,uuid
from pathlib import Path
from .documents import scoped,read_document


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).is_file() else None


class SkillEngine:
    def __init__(self,directory,grants,model):
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.grants=grants;self.model=model;self.sessions={};self.lock=threading.RLock()
    def permitted(self,root):
        root=Path(root).resolve()
        if not any(g.get('access') in ('write','delete') and root.is_relative_to(Path(g['path']).resolve()) for g in self.grants()):
            raise ValueError('This workspace needs write access in Permissions. Revoked access stops runs.')
        return root
    def _save(self,path,data):
        tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8");tmp.chmod(0o600);tmp.replace(path)
    def sources(self,root,paths):
        if not isinstance(paths,list) or not 1<=len(paths)<=4 or any(not isinstance(p,str) or len(p)>240 for p in paths) or len(set(paths))!=len(paths):raise ValueError('Select one to four different input files.')
        rows=[{'id':f'S{i+1}','name':p,'text':read_document(scoped(root,p))} for i,p in enumerate(paths)]
        if sum(len(r['text']) for r in rows)>6000:raise ValueError('Use at most 6,000 characters of selected files for this bounded workflow.')
        return rows
    def start(self,root,sources,output):
        root=self.permitted(root);self.sources(root,sources)
        dest=scoped(root,output)
        if dest.suffix.lower()!='.md' or output in sources:raise ValueError('Choose a separate Markdown example destination.')
        if not dest.parent.is_dir():raise ValueError('Choose an existing destination folder.')
        if not dest.exists():
            with dest.open('x',encoding='utf-8') as f:f.write('# My example\n\nShow Pico the result you want from your selected files.\n')
        sid=str(uuid.uuid4());record={'id':sid,'root':str(root),'sources':sources,'output':output,'started':time.time(),'baseline':digest(dest),'last':digest(dest),'events':[]}
        self.sessions[sid]=record
        return record
    def observe(self,sid):
        with self.lock:
            r=self.sessions[sid];self.permitted(r['root'])
            if time.time()-r['started']>1800:raise ValueError('Teaching expired after 30 minutes. Start again.')
            current=digest(scoped(r['root'],r['output']))
            if current!=r['last']:
                r['events'].append({'kind':'example_changed','at':time.time(),'digest':current});r['last']=current
            return len(r['events'])
    def finish(self,sid,name,confirmed=False):
        if confirmed is not True:raise ValueError('Approve sending the selected files and example to Muse.')
        with self.lock:
            self.observe(sid);r=self.sessions[sid]
            if r['last']==r['baseline'] or not r['events']:raise ValueError('No changed example was observed. Edit and save the example before finishing.')
            rows=self.sources(r['root'],r['sources']);example=read_document(scoped(r['root'],r['output']))
            if len(example)>2000:raise ValueError('Keep the example below 2,000 characters.')
            body={'operation':'learn','request_id':str(uuid.uuid4()),'sources':rows,'example':example}
            learned=self.model(body)
            self.permitted(r['root'])
            if digest(scoped(r['root'],r['output']))!=r['last']:raise ValueError('The example changed during learning. Review and finish again.')
            if not isinstance(learned.get('instructions'),str) or not learned['instructions'].strip() or len(learned['instructions'])>1000:raise ValueError('Muse returned no usable recipe.')
            identity=str(uuid.uuid4());recipe={'id':identity,'name':str(name).strip()[:80] or 'My routine','root':r['root'],'sources':r['sources'],'example_file':r['output'],'example_digest':r['last'],'events':r['events'],'instructions':learned['instructions'],'created':time.time(),'runs':[]}
            self._save(self.directory/(identity+'.json'),recipe);del self.sessions[sid]
            return recipe
    def list(self):
        rows=[]
        for p in self.directory.glob('*.json'):
            try:
                r=json.loads(p.read_text(encoding='utf-8'));rows.append({'id':r['id'],'name':r['name'],'runs':len(r['runs']),'root':r['root']})
            except (ValueError,KeyError):continue
        return rows
    def run(self,identity,confirmed=False,request_id=None):
        if confirmed is not True:raise ValueError('Approve this run and its selected files first.')
        identity=str(uuid.UUID(identity));path=self.directory/(identity+'.json')
        with self.lock:
            recipe=json.loads(path.read_text(encoding='utf-8'));root=self.permitted(recipe['root'])
            rid=str(uuid.UUID(request_id)) if request_id else str(uuid.uuid4())
            if any(r['id']==rid for r in recipe['runs']):raise ValueError('This run was already attempted. No automatic retry.')
            hashes={p:digest(scoped(root,p)) for p in recipe['sources']};rows=self.sources(root,recipe['sources'])
            if any(digest(scoped(root,p))!=h for p,h in hashes.items()):raise ValueError('Inputs changed while reading. Nothing was sent.')
            attempt={'id':rid,'at':time.time(),'status':'running','input_hashes':hashes};recipe['runs'].append(attempt);self._save(path,recipe)
            try:
                result=self.model({'operation':'run','request_id':rid,'sources':rows,'instructions':recipe['instructions']})
                from .contracts import validate_pack,render_pack
                validate_pack(result,rows)
                self.permitted(root)
                if any(digest(scoped(root,p))!=h for p,h in hashes.items()):raise ValueError('Inputs changed during the run. The result was not written; review fresh inputs.')
                output=scoped(root,str(Path(recipe['example_file']).parent/('prepared-'+time.strftime('%Y%m%d-%H%M%S')+'-'+rid[:8]+'.md')))
                content=render_pack(result,rows,output,root)
                with output.open('x',encoding='utf-8') as f:f.write(content)
                if output.read_text(encoding='utf-8')!=content:raise ValueError('Output verification failed.')
                attempt.update(status='completed',output=str(output.relative_to(root)),digest=digest(output),bytes=output.stat().st_size)
            except Exception as error:
                attempt.update(status='failed',error=str(error)[:300]);self._save(path,recipe);raise
            self._save(path,recipe)
            return {**attempt,'name':recipe['name'],'root':str(root)}

    def latest(self,identity):
        identity=str(uuid.UUID(identity));recipe=json.loads((self.directory/(identity+'.json')).read_text(encoding='utf-8'));root=self.permitted(recipe['root'])
        for run in reversed(recipe['runs']):
            if run['status']=='completed':
                output=scoped(root,run['output'])
                if not output.is_file() or digest(output)!=run['digest']:raise ValueError('This pack has changed or moved. Open it directly in Finder.')
                return output
        raise ValueError('This routine has no completed pack yet.')

    def replace_sources(self,identity,paths):
        with self.lock:
            identity=str(uuid.UUID(identity));file=self.directory/(identity+'.json');recipe=json.loads(file.read_text(encoding='utf-8'));root=self.permitted(recipe['root'])
            self.sources(root,paths)
            if recipe['example_file'] in paths:raise ValueError('The example cannot be an input note.')
            recipe['sources']=paths;self._save(file,recipe)
