"""Bundle official embedded CPython and Windows wheels; users install no runtime."""
import hashlib,io,json,shutil,subprocess,sys,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def prepare():
    target=ROOT/'build/windows-runtime';target.mkdir(parents=True,exist_ok=True)
    url='https://www.python.org/ftp/python/3.12.8/python-3.12.8-embed-amd64.zip'
    cache=ROOT/'.local/windows-python.zip'
    cache.parent.mkdir(parents=True,exist_ok=True)
    if not cache.exists():cache.write_bytes(urllib.request.urlopen(url,timeout=90).read())
    raw=cache.read_bytes()
    if hashlib.md5(raw).hexdigest()!='1e86b04bc7d27c5c06edf8f617e1184a':raise RuntimeError('Official CPython package checksum mismatch')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:z.extractall(target)
    (target/'python312._pth').write_text('python312.zip\n.\nLib/site-packages\nengine\nimport site\n')
    packages=target/'Lib/site-packages'
    if packages.exists():shutil.rmtree(packages)
    subprocess.run([sys.executable,'-m','pip','install','--disable-pip-version-check','--only-binary=:all:','--platform','win_amd64','--python-version','3.12','--implementation','cp','--abi','cp312','--target',str(packages),'-r',str(ROOT/'requirements-document-tools.txt')],check=True)
    engine=target/'engine';engine.mkdir(exist_ok=True)
    for path in (ROOT/'agents').glob('*.py'):shutil.copy2(path,engine/path.name)
    shutil.copytree(ROOT/'agents/skills',engine/'skills',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
    output=ROOT/'build/windows-runtime.zip'
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        for path in target.rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:z.write(path,path.relative_to(target))
    print('Bundled Windows workflow runtime:',output)
    return output
if __name__=='__main__':prepare()
