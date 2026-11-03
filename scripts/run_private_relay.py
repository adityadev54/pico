"""Isolated development relay, reachable only through the owner's Fly tunnel.
Uses existing authenticated accounts, a separate mailbox prefix, and shared
model budget. Never changes the production listener or exports server keys.
"""
import os,socket,sys,threading,time,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['PICO_MAIL_NAMESPACE']='teach-v1'
from relay import app
app.ThreadingHTTPServer.address_family=socket.AF_INET6
sys.argv=[sys.argv[0],'--host','::','--port','8770','--state',str(Path(__file__).resolve().parents[1]/'private-relay.sqlite')]
def keep_test_session_awake():
    until=time.monotonic()+4*60*60
    while time.monotonic()<until:
        try:
            with urllib.request.urlopen('https://pico-companion.fly.dev/health',timeout=12) as reply:reply.read(4096)
        except Exception:pass
        time.sleep(25)
threading.Thread(target=keep_test_session_awake,daemon=True).start()
app.main()
