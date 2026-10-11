import io
import json
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from tarot.server import handler, runtime_identity
from tarot.core import Store, load_registry


class RuntimeTests(unittest.TestCase):
    def response(self, team='TGOOD', scopes='commands,chat:write'):
        response = io.BytesIO(json.dumps({'ok': True, 'team_id': team, 'bot_id': 'BFAKE', 'user_id': 'UFAKE', 'user': 'tarot'}).encode())
        response.headers = {'x-oauth-scopes': scopes}
        return response

    def test_auth_report_excludes_token_and_limits_identity_fields(self):
        with patch.dict(os.environ, {'SLACK_BOT_TOKEN': 'FAKE_ONLY', 'SLACK_TEAM_ID': 'TGOOD'}), patch('urllib.request.urlopen', return_value=self.response()):
            report = runtime_identity()
        self.assertNotIn('FAKE_ONLY', json.dumps(report))
        self.assertTrue(report['authenticated'])
        self.assertFalse(report['app_id_verified'])

    def test_health_exposes_only_component_flags(self):
        with tempfile.TemporaryDirectory() as temp:
            store = Store(str(Path(temp) / 'state.db'), load_registry('registry.json'))
            cls = handler(store, 'FAKE_SIGNING_ONLY', 'TGOOD', runtime_status={'worker': True, 'scheduler': True})
            req = cls.__new__(cls)
            req.path = '/health'
            req.wfile = io.BytesIO()
            with patch.object(req, 'send_response') as status, patch.object(req, 'send_header'), patch.object(req, 'end_headers'):
                req.do_GET()
            self.assertEqual(status.call_args.args[0], 200)
            data = json.loads(req.wfile.getvalue())
            self.assertTrue(data['worker'])
            self.assertTrue(data['scheduler'])
            self.assertNotIn('FAKE_SIGNING_ONLY', json.dumps(data))

    def test_wrong_team_or_insufficient_scope_fails_closed(self):
        for response in [self.response(team='OTHER'), self.response(scopes='commands')]:
            with patch.dict(os.environ, {'SLACK_BOT_TOKEN': 'FAKE_ONLY', 'SLACK_TEAM_ID': 'TGOOD'}), patch('urllib.request.urlopen', return_value=response), self.assertRaises(ValueError):
                runtime_identity()
