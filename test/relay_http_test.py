"""Request framing must not turn a valid Windows pairing into a code failure."""
import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer

from relay.app import make_handler


class PairingService:
    def __init__(self):
        self.claims = []

    def claim(self, body, address):
        self.claims.append(body)
        return {'device_id': 'test-computer', 'token': 'test-device-token'}


class RequestFramingTests(unittest.TestCase):
    def setUp(self):
        self.service = PairingService()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(self.service))
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.client = http.client.HTTPConnection(*self.server.server_address, timeout=5)

    def tearDown(self):
        self.client.close()
        self.server.shutdown()
        self.server.server_close()
        self.worker.join()

    def test_chunked_request_does_not_reach_code_validation(self):
        body = json.dumps({'code': '123456', 'os': 'windows'}).encode()
        self.client.putrequest('POST', '/claim')
        self.client.putheader('Content-Type','application/json')
        self.client.putheader('Transfer-Encoding','chunked')
        self.client.endheaders()  # Server rejects framing before accepting any body.
        response = self.client.getresponse()
        self.assertEqual(response.status, 411)
        self.assertIn('Update Pico', json.load(response)['error'])
        self.assertEqual(self.service.claims, [])

    def test_fixed_length_request_preserves_the_code(self):
        body = json.dumps({'code': '123456', 'os': 'windows'}).encode()
        self.client.request('POST', '/claim', body=body,
                            headers={'Content-Type': 'application/json'})
        response = self.client.getresponse()
        self.assertEqual(response.status, 200)
        self.assertEqual(json.load(response)['device_id'], 'test-computer')
        self.assertEqual(self.service.claims, [{'code': '123456', 'os': 'windows'}])


if __name__ == '__main__':
    unittest.main()
