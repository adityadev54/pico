"""Start the separate test companion after restoring its private relay if needed.
No public deployment, permission expansion, or account secrets are copied.
"""
import fcntl,os,shutil,subprocess,sys,tempfile,time,urllib.request,zipfile,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FLY=os.environ.get('PICO_FLYCTL') or shutil.which('flyctl') or str(ROOT/'.local/bin/flyctl')
APP='pico-companion';MACHINE='18547edbd6d108'
REMOTE='/tmp/pico-teach-private-20261102'

def healthy():
    try:
        with urllib.request.urlopen('http://127.0.0.1:8766/health',timeout=3) as r:
            return r.status==200
    except Exception:return False

def run(args):
    subprocess.run(args,check=True,timeout=120)

def package_runtime(archive):
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for folder in ('relay','server'):
            for p in (ROOT/folder).rglob('*.py'):
                if '__pycache__' not in p.parts:z.write(p,p.relative_to(ROOT))
        # The server imports the shared pure validator, not the desktop helper.
        for name in ('agents/skills/__init__.py','agents/skills/contracts.py','scripts/run_private_relay.py'):
            z.write(ROOT/name,name)

def restore():
    run([FLY,'machine','start',MACHINE,'-a',APP])
    with tempfile.TemporaryDirectory(prefix='pico-private-') as temp:
        nonce=uuid.uuid4().hex
        remote_zip=f'/tmp/pico-test-{nonce}.zip'
        remote_script=f'/tmp/pico-test-{nonce}.py'
        archive=Path(temp)/'runtime.zip'
        package_runtime(archive)
        update=Path(temp)/'restore.py'
        update.write_text('''from pathlib import Path
import os,signal,subprocess,sys,time,zipfile
root=Path("/tmp/pico-teach-private-20261102")
pidfile=root/"runtime.pid"
if pidfile.exists():
 try:
  pid=int(pidfile.read_text()); command=Path(f"/proc/{pid}/cmdline").read_bytes()
  if b"run_private_relay.py" not in command:raise SystemExit("Refusing to stop a non-test process")
  os.kill(pid,signal.SIGTERM);time.sleep(1)
 except (ProcessLookupError,FileNotFoundError):pass
with zipfile.ZipFile("/tmp/pico-test-runtime.zip") as z:
 for name in z.namelist():
  if name.startswith("/") or ".." in Path(name).parts:raise SystemExit("Invalid archive member")
 z.extractall(root)
with (root/"runtime.log").open("ab") as log:
 p=subprocess.Popen([sys.executable,str(root/"scripts/run_private_relay.py")],cwd=root,stdout=log,stderr=log,start_new_session=True)
pidfile.write_text(str(p.pid))
print("Private test relay restored; public app unchanged.")
''')
        update.write_text(update.read_text().replace('/tmp/pico-test-runtime.zip',remote_zip))
        run([FLY,'ssh','sftp','put',str(archive),remote_zip,'-a',APP])
        run([FLY,'ssh','sftp','put',str(update),remote_script,'-a',APP])
        run([FLY,'ssh','console','-a',APP,'-C',f'python {remote_script}'])

def main():
    local=ROOT/'.local';local.mkdir(exist_ok=True)
    with (local/'test-session.lock').open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print('Pico Teach test session is already running.');return
        proxy=None
        try:
            # Refresh the bounded four-hour test runtime on each explicit launch.
            restore()
            if not healthy():
                proxy=subprocess.Popen([FLY,'proxy','8766:8770','-a',APP])
            for _ in range(30):
                if healthy():break
                if proxy is not None and proxy.poll() is not None:
                    raise RuntimeError('The test tunnel could not start. Close any stale tunnel using port 8766.')
                time.sleep(1)
            else:raise RuntimeError('Private relay is not reachable. No computer action was started.')
            print('Pico Teach connection ready. Keep this test-session window open.')
            subprocess.run(['sh','scripts/run_companion.sh','--state','.local/teach-companion','--relay','http://127.0.0.1:8766'],cwd=ROOT,check=True)
        finally:
            if proxy is not None:
                proxy.terminate()
                try:proxy.wait(timeout=5)
                except subprocess.TimeoutExpired:proxy.kill()
if __name__=='__main__':
    try:main()
    except (Exception,KeyboardInterrupt) as e:
        print(f'Test session stopped: {e}',file=sys.stderr);sys.exit(1)
