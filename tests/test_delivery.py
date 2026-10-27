import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from civic_tracker import delivery


class DeliveryTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); (self.root / 'config').mkdir(); (self.root / 'data').mkdir()
        (self.root / 'config/digest-delivery.json').write_text(json.dumps({
            'schema_version': 1, 'enabled': True, 'timezone': 'America/Chicago',
            'interval_days': 3, 'max_attempts': 24,
            'sender_secret': 'GMAIL_USER', 'password_secret': 'GMAIL_APP_PASSWORD',
            'recipient_secret': 'DIGEST_TO'}))
        self.preview = {'preview_id': 'digest-fixture', 'input_sha256': {'data/x': 'a' * 64},
                        'period': {'start': '2026-10-20T06:00:00-05:00'}}

    def test_reservation_is_due_once_and_contains_no_recipient(self):
        with patch.object(delivery, 'current_preview', return_value=(self.preview, '<p>html</p>', 'text')):
            self.assertEqual(delivery.reserve(self.root, '2026-10-27T12:00:00+00:00'), 0)
            state = json.loads((self.root / 'data/digest-delivery.json').read_text())
            self.assertEqual(state['attempts'][-1]['status'], 'reserved')
            self.assertNotIn('@', json.dumps(state))
            self.assertEqual(delivery.reserve(self.root, '2026-10-28T12:00:00+00:00'), 1)

    def test_send_rejects_missing_secrets_without_smtp(self):
        with patch.object(delivery, 'current_preview', return_value=(self.preview, '<p>html</p>', 'text')):
            delivery.reserve(self.root, '2026-10-27T12:00:00+00:00')
            with patch.dict(os.environ, {}, clear=True), patch.object(delivery.smtplib, 'SMTP') as smtp:
                self.assertEqual(delivery.send(self.root), 1)
                smtp.assert_not_called()
            state = json.loads((self.root / 'data/digest-delivery.json').read_text())
            self.assertEqual(state['attempts'][-1]['status'], 'rejected')
            self.assertEqual(state['attempts'][-1]['error_code'], 'missing-secret')
