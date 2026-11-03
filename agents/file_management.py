"""Scoped, reviewed trash/restore and bounded ZIP tools adapted from 27bca20.
No home-directory default, symlink traversal, automatic grants or overwrites.
"""
import hashlib,io,json,os,shutil,stat,tempfile,uuid,zipfile
from pathlib import Path,PurePosixPath
from native_search import NativeError
from tools import ToolError
from workspace import Workspace

MAX_FILES=200
MAX_BYTES=10*1024*1024
RANK={'read':0,'write':1,'delete':2}

def guard(ctx,level):
    if ctx.get('cancelled',lambda:False)():raise NativeError('cancelled','Stopped before changing files.')
    grants=ctx.get('grants',[])
    if len(grants)!=1:raise NativeError('permission_denied','Select one approved folder.')
    root=Path(grants[0]['path']).resolve()
    current=ctx['refresh_grants']() if ctx.get('refresh_grants') else ctx.get('current_grants',lambda:grants)()
    if not any(Path(g['path']).resolve()==root and RANK.get(g.get('access','read'),-1)>=RANK[level] for g in current):
        raise NativeError('permission_denied',f'This folder needs {level} access in Permissions.')
    return Workspace(root)

def visible(workspace,name):
    if not isinstance(name,str) or not name or '\\' in name or ':' in name or any(p.startswith('.') for p in name.split('/')):
        raise ToolError('invalid_args','Choose visible files inside the approved folder.')
    relative=Path(name)
    if relative.is_absolute():raise ToolError('invalid_args','Use a relative filename.')
    current=workspace.root
    for part in relative.parts:
        current=current/part
        if current.is_symlink():raise ToolError('invalid_args','Links are outside this workflow.')
    return workspace.resolve(name)

def trash_root(workspace):
    root=workspace.root/'.pico-trash'
    if root.is_symlink():raise NativeError('permission_denied','Pico trash cannot be a link.')
    root.mkdir(exist_ok=True,mode=0o700)
    return root

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def delete_files_handler(args,ctx):
    if args.get('confirm')!='DELETE':raise ToolError('invalid_args','Review the exact file before moving it to trash.')
    w=guard(ctx,'delete');source=visible(w,args['path'])
    if not source.is_file():raise NativeError('no_match','That file was not found.')
    if source.stat().st_size>1024*1024:raise ToolError('invalid_args','Trash files up to 1 MB in this preview.')
    signature=source.stat();original_digest=digest(source);root=trash_root(w)
    identity=uuid.uuid4().hex;target=root/(identity+'.data');sidecar=root/(identity+'.json')
    record={'original':str(source.relative_to(w.root)),'trashed':target.name,'size_bytes':signature.st_size,'digest':original_digest}
    guard(ctx,'delete')
    with sidecar.open('x') as f:json.dump(record,f)
    try:
        os.link(source,target)
        latest=source.stat()
        if (latest.st_ino,latest.st_size,latest.st_mtime_ns)!=(signature.st_ino,signature.st_size,signature.st_mtime_ns) or digest(source)!=original_digest:
            raise NativeError('candidate_changed','That file changed before deletion. Nothing was removed.')
        guard(ctx,'delete');source.unlink()
    except Exception:
        target.unlink(missing_ok=True);sidecar.unlink(missing_ok=True);raise
    return ({'message':f'Moved {source.name} to Pico trash. You can restore it by name.','trashed_count':1,'trashed':[record['original']],'restore_name':source.name,'digest':original_digest},{'count':1,'digest':original_digest})

def entries(workspace):
    root=trash_root(workspace)
    rows=[]
    for sidecar in sorted(root.glob('*.json'),key=lambda p:p.stat().st_mtime_ns):
        if sidecar.is_symlink():continue
        try:
            data=json.loads(sidecar.read_text());name=data.get('trashed','')
            if not isinstance(name,str) or Path(name).name!=name or not name.endswith('.data'):continue
            target=root/name
            if not target.is_file() or target.is_symlink():continue
            visible(workspace,data.get('original',''))
            rows.append((sidecar,target,data))
        except (OSError,ValueError,ToolError,NativeError):continue
    return rows

def restore_deleted_handler(args,ctx):
    w=guard(ctx,'write');matches=[row for row in entries(w) if args['name'] in (row[2]['original'],Path(row[2]['original']).name)]
    if not matches:raise NativeError('no_match','No trashed file matches that name.')
    sidecar,target,data=matches[-1]
    if target.stat().st_size>1024*1024:raise ToolError('invalid_args','Restore files up to 1 MB in this preview.')
    home=visible(w,data['original'])
    if digest(target)!=data['digest']:raise NativeError('candidate_changed','The trashed file changed; restore stopped.')
    for n in range(1,102):
        dest=home if n==1 else home.with_name(f'{home.stem}_{n}{home.suffix}')
        guard(ctx,'write')
        try:os.link(target,dest);break
        except FileExistsError:continue
    else:raise ToolError('invalid_args','Too many restored copies.')
    target.unlink();sidecar.unlink()
    result={'message':f'Restored {dest.name}.','path':str(dest.relative_to(w.root)),'size_bytes':dest.stat().st_size,'digest':digest(dest)}
    return result,{'digest':result['digest'],'size_bytes':result['size_bytes']}

def empty_trash_handler(args,ctx):
    if args.get('confirm')!='EMPTY':raise ToolError('invalid_args','Type EMPTY and approve permanently clearing Pico trash.')
    w=guard(ctx,'delete');removed=0
    for sidecar,target,data in entries(w):
        guard(ctx,'delete');target.unlink();sidecar.unlink();removed+=1
    return {'message':f'Permanently cleared {removed} item(s) from Pico trash.','removed_count':removed},{'count':removed}

def archive_handler(args,ctx):
    w=guard(ctx,'write')
    try:names=json.loads(args['paths_json'])
    except ValueError:raise ToolError('invalid_args','Choose files to archive.') from None
    if not isinstance(names,list) or not 1<=len(names)<=MAX_FILES:raise ToolError('invalid_args','Choose up to 200 files.')
    sources=[visible(w,name) for name in names]
    if args['action']=='create':
        collected=[]
        for source in sources:
            if source.is_file():collected.append(source)
            elif source.is_dir():
                for directory,dirs,files in os.walk(source,followlinks=False):
                    dirs[:]=[d for d in dirs if not d.startswith('.') and not (Path(directory)/d).is_symlink()]
                    collected.extend(Path(directory)/f for f in files if not f.startswith('.') and not (Path(directory)/f).is_symlink())
                    if len(collected)>MAX_FILES:raise ToolError('invalid_args','Zip at most 200 files.')
            else:raise NativeError('no_match','An archive source was not found.')
        collected=list(dict.fromkeys(collected))
        if not collected or len(collected)>MAX_FILES or sum(p.stat().st_size for p in collected)>MAX_BYTES:
            raise ToolError('invalid_args','Zip up to 200 files and 10 MB of source data.')
        signatures={p:(p.stat().st_size,p.stat().st_mtime_ns) for p in collected}
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
            for p in collected:guard(ctx,'write');z.write(p,p.relative_to(w.root).as_posix())
        for p,sig in signatures.items():
            if (p.stat().st_size,p.stat().st_mtime_ns)!=sig:raise NativeError('candidate_changed','A source changed. Archive not saved.')
        name=args.get('output') or sources[0].stem+'.zip'
        if not name.lower().endswith('.zip'):name+='.zip'
        target=visible(w,name);raw=output.getvalue()
        if len(raw)>1024*1024:raise ToolError('invalid_args','The ZIP exceeds the current 1 MB transfer limit.')
        guard(ctx,'write')
        for n in range(1,102):
            dest=target if n==1 else target.with_name(f'{target.stem}_{n}.zip')
            try:
                with dest.open('xb') as f:f.write(raw)
                break
            except FileExistsError:continue
        else:raise ToolError('invalid_args','Too many archive copies.')
        data={'message':f'Created {dest.name} with {len(collected)} file(s).','path':str(dest.relative_to(w.root)),'size_bytes':len(raw),'digest':hashlib.sha256(raw).hexdigest(),'count':len(collected)}
        return data,{'digest':data['digest'],'size_bytes':len(raw)}
    if args['action']!='extract' or len(sources)!=1:raise ToolError('invalid_args','Extract one ZIP at a time.')
    source=sources[0]
    if not source.is_file() or source.stat().st_size>1024*1024:raise ToolError('invalid_args','Choose a ZIP below 1 MB.')
    try:
        with zipfile.ZipFile(source) as z:
            members=z.infolist()
            if len(members)>MAX_FILES or sum(m.file_size for m in members)>MAX_BYTES:raise ToolError('invalid_args','ZIP expands beyond the preview limit.')
            for m in members:
                name=m.filename;parts=PurePosixPath(name).parts
                if not parts or name.startswith('/') or '\\' in name or ':' in name or any(p.startswith('.') for p in parts) or stat.S_ISLNK(m.external_attr>>16) or m.flag_bits&1:
                    raise ToolError('invalid_args','This ZIP contains unsafe paths, links or encrypted files.')
            target=visible(w,args.get('output') or source.stem+'-extracted')
            if target.exists():target=target.with_name(target.name+'-'+uuid.uuid4().hex[:8])
            guard(ctx,'write');target.mkdir()
            created=[]
            try:
                for m in members:
                    guard(ctx,'write');dest=target/m.filename
                    if target.is_symlink() or not dest.resolve().is_relative_to(target):raise ToolError('invalid_args','ZIP path escaped its folder.')
                    if m.is_dir():dest.mkdir(parents=True,exist_ok=True);continue
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    with dest.open('xb') as out,z.open(m) as incoming:shutil.copyfileobj(incoming,out,64*1024)
                    created.append({'name':dest.name,'path':str(dest.relative_to(w.root))})
            except Exception:
                shutil.rmtree(target);raise
    except zipfile.BadZipFile:raise ToolError('invalid_args','That ZIP is unreadable.') from None
    return {'message':f'Extracted {len(created)} file(s) into {target.name}.','output':str(target.relative_to(w.root)),'count':len(created),'files':created[:30]},{'count':len(created)}
