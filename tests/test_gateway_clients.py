import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
import unittest
from unittest import mock
from urllib.parse import parse_qs


REPO = Path(__file__).resolve().parents[1]
PATHS = [
    'LoRa-Gateway/Gateway/Python/ap-01-lora-gateway-2-read-httpGet.py',
    'Demos_sourceCode/01_2017CES_TsuNaMi/Gateway/ap-QNAP-lora-gateway-2-read-httpGet.py',
    'Sample-Java/02-iFrogLabLevel1-Lib/ap-QNAP-lora-gateway-2-read-httpGet.py',
    'Samples-Python/Ver2/02-iFrogLabLevel1-Lib/ap-QNAP-lora-gateway-2-read-httpGet.py',
]
KEY = 'test-only-placeholder-key-32-characters'


def load_adapter(path):
    source = (REPO / path).read_text(encoding='utf-8')
    adapter = source.split('# BEGIN HTTP API ADAPTER', 1)[1].split('\n', 1)[1]
    adapter = adapter.split('# END HTTP API ADAPTER', 1)[0]
    namespace = {}
    exec(compile(adapter, path + ':HTTP-adapter', 'exec'), namespace)
    return namespace


class Handler(BaseHTTPRequestHandler):
    records = []
    status = 200
    body = b'{"Result":"OK","Record":{"Id":123}}'

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
        self.records.append((self.path, dict(self.headers), body))
        self.send_response(self.status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *args):
        pass


class GatewayClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.endpoint = 'http://127.0.0.1:%d/AjaxIoT.php' % cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def env(self, **overrides):
        settings = {'IOT_API_URL': self.endpoint, 'IOT_API_KEY': KEY}
        settings.update(overrides)
        return mock.patch.dict(os.environ, settings)

    def setUp(self):
        Handler.records.clear()
        Handler.status = 200
        Handler.body = b'{"Result":"OK","Record":{"Id":123}}'

    def test_post_preserves_fields_key_header_only_and_success(self):
        fields = {'action': 'insertByAPIKey', 'KeyName': 'x&=', 'Data': '12.3 + 9', 'Datatype': '1'}
        for path in PATHS:
            with self.subTest(path=path), self.env():
                result = load_adapter(path)['Fun_HTTPPost'](fields)
                self.assertEqual(result['Record']['Id'], 123)
                endpoint, headers, body = Handler.records[-1]
                self.assertEqual(endpoint, '/AjaxIoT.php')
                self.assertEqual(headers['X-API-Key'], KEY)
                self.assertNotIn(KEY, endpoint)
                self.assertNotIn(KEY.encode(), body)
                self.assertNotIn('APIKey', parse_qs(body.decode()))
                self.assertEqual(parse_qs(body.decode()), {key: [value] for key, value in fields.items()})

    def test_default_endpoint_and_reject_missing_short_or_header_injection_keys(self):
        for path in PATHS:
            adapter = load_adapter(path)
            for key in ['', 'short', KEY + '\r\nX-Evil: yes', KEY + ' ']:
                with self.subTest(path=path, invalid_key=key != ''), self.env(IOT_API_KEY=key):
                    with self.assertRaisesRegex(RuntimeError, 'IOT_API_KEY'):
                        adapter['Fun_HTTPPost']({'action': 'insertByAPIKey'})
            with mock.patch.dict(os.environ, {'IOT_API_KEY': KEY}):
                endpoint = os.environ.pop('IOT_API_URL', None)
                try:
                    parsed, _ = adapter['_api_settings']()
                    self.assertEqual((parsed.scheme, parsed.hostname, parsed.port, parsed.path),
                                     ('http', '127.0.0.1', 8080, '/AjaxIoT.php'))
                finally:
                    if endpoint is not None:
                        os.environ['IOT_API_URL'] = endpoint
        self.assertEqual(Handler.records, [])

    def test_reject_invalid_endpoint_before_connecting(self):
        for path in PATHS:
            adapter = load_adapter(path)
            for endpoint in ['file:///etc/passwd', 'http://user:pass@localhost/a', self.endpoint + '?APIKey=secret',
                             self.endpoint + '#fragment', 'http://127.0.0.1:99999/a', 'http://127.0.0.1:bad/a',
                             'http://127.0.0.1/a b']:
                with self.subTest(path=path, endpoint=endpoint), self.env(IOT_API_URL=endpoint):
                    with self.assertRaisesRegex(RuntimeError, 'IOT_API_URL'):
                        adapter['Fun_HTTPPost']({})
        self.assertEqual(Handler.records, [])

    def test_reject_http_errors_bad_json_and_json_error_without_echoing_response(self):
        responses = [(403, b'{"Result":"ERROR","Message":"' + KEY.encode() + b'"}', 'HTTP 403'),
                     (302, b'redirect', 'HTTP 302'), (200, b'<html>not-json</html>', 'invalid JSON'),
                     (200, b'{"Result":"ERROR","Message":"' + KEY.encode() + b'"}', 'did not accept'),
                     (200, b'[]', 'did not accept')]
        for path in PATHS:
            for status, body, message in responses:
                Handler.status, Handler.body = status, body
                with self.subTest(path=path, status=status, message=message), self.env():
                    with self.assertRaisesRegex(RuntimeError, message) as error:
                        load_adapter(path)['Fun_HTTPPost']({'action': 'insertByAPIKey'})
                    self.assertNotIn(KEY, str(error.exception))

    def test_closes_connection_on_success_and_transport_failure(self):
        for path in PATHS:
            for failure in [False, True]:
                connection = mock.Mock()
                if failure:
                    connection.request.side_effect = OSError('test transport disconnected')
                else:
                    response = connection.getresponse.return_value
                    response.status = 200
                    response.read.return_value = b'{"Result":"OK"}'
                with self.subTest(path=path, failure=failure), self.env(), mock.patch.object(
                        http.client, 'HTTPConnection', return_value=connection):
                    adapter = load_adapter(path)
                    if failure:
                        with self.assertRaises(OSError):
                            adapter['Fun_HTTPPost']({})
                    else:
                        adapter['Fun_HTTPPost']({})
                    connection.close.assert_called_once_with()


if __name__ == '__main__':
    unittest.main(verbosity=2)

