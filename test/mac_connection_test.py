import io
import json
import queue
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'agents'))
from client import DeviceClient,DeviceError,connection_error
from companion import Companion

class MacConnectionTests(unittest.TestCase):
    def test_macos_does_not_probe_system_proxy(self):
        import urllib.request
        with patch('client.sys.platform','darwin'), patch('urllib.request.getproxies',side_effect=AssertionError('unsafe CoreFoundation lookup')), patch.dict('os.environ',{},clear=True):
            with patch('urllib.request.OpenerDirector.open',return_value=io.BytesIO(b'{"ok":true}')) as send:
                self.assertEqual(DeviceClient('https://example.test').post('/agent/revoke',{}),{'ok':True})
                self.assertTrue(send.called)

    def test_environment_proxy_is_preserved(self):
        with patch('client.sys.platform','darwin'), patch.dict('os.environ',{'https_proxy':'http://localhost:9999'},clear=True), patch('urllib.request.build_opener') as build:
            build.return_value.open.return_value=io.BytesIO(b'{}')
            DeviceClient('https://example.test').post('/claim',{})
            self.assertEqual(build.call_args.args[0].proxies['https'],'http://localhost:9999')

    def test_revoked_elsewhere_still_finishes_unpair(self):
        c=Companion.__new__(Companion);c.client=Mock();c.client.post.side_effect=PermissionError()
        c.overlay=True;c.events=queue.Queue()
        with patch('companion.threading.Thread') as thread:
            thread.side_effect=lambda target,**kw:Mock(start=target)
            c.unpair()
        self.assertEqual(c.events.get_nowait(),('revoked',None))

    def test_failure_does_not_claim_unpaired(self):
        c=Companion.__new__(Companion);c.client=Mock();c.client.post.side_effect=TimeoutError()
        c.overlay=True;c.events=queue.Queue()
        with patch('companion.threading.Thread') as thread:
            thread.side_effect=lambda target,**kw:Mock(start=target)
            c.unpair()
        event=c.events.get_nowait();self.assertEqual(event[0],'notice')
        self.assertNotIn('fresh code',event[1])

    def test_server_pairing_error_is_not_hidden(self):
        self.assertEqual(connection_error(DeviceError('Unpair the existing computer first.',409)),'Unpair the existing computer first.')
