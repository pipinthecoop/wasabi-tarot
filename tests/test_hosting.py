import io
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from tarot.preview_server import address, handler
from tarot.server import bind_address


class HostingTests(unittest.TestCase):
    def test_native_bind_and_existing_container_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(bind_address(), ("0.0.0.0", 8080))
            self.assertEqual(address(), ("127.0.0.1", 8765))
        with patch.dict(os.environ, {"BIND_HOST": "127.0.0.1", "PORT": "8765"}, clear=True):
            self.assertEqual(bind_address(), ("127.0.0.1", 8765))
        for port in ("0", "65536", "invalid"):
            with patch.dict(os.environ, {"PORT": port}, clear=True), self.assertRaises(ValueError):
                bind_address()
        with patch.dict(os.environ, {"BIND_HOST": "0.0.0.0"}, clear=True), self.assertRaisesRegex(ValueError, "loopback"):
            address()

    def request(self, path, method="GET"):
        cls = handler(Path(__file__).resolve().parents[1])
        req = cls.__new__(cls)
        req.path, req.command = path, method
        req.wfile = io.BytesIO()
        with patch.object(req, "send_response") as status, patch.object(req, "send_header"), patch.object(req, "end_headers"):
            (req.do_POST if method == "POST" else req.do_GET)()
        return status.call_args.args[0], req.wfile.getvalue()

    def test_demo_is_read_only_and_does_not_serve_private_files(self):
        status, body = self.request("/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"status": "ok", "mode": "asset-demo-only", "slack_ingress": False, "worker": False, "database": False})
        self.assertEqual(self.request("/slack/commands", "POST")[0], 405)
        self.assertEqual(self.request("/api/login", "POST")[0], 405)
        self.assertEqual(self.request("/api/table")[0], 401)
        for path in ("/.env", "/registry.json", "/assets/decks/private/major-0.png", "/assets/decks/crt/../../.env"):
            self.assertEqual(self.request(path)[0], 404)
        self.assertEqual(self.request("/assets/decks/crt/major-0.gif")[0], 200)
        self.assertEqual(self.request("/assets/theme/crt-back.png")[0], 200)


if __name__ == "__main__":
    unittest.main()
