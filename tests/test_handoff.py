"""Protect handoff navigation and gates without touching runtime state or sources."""
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('handoff_check', ROOT/'scripts/check_handoff.py')
CHECK = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(CHECK)


class HandoffTests(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        root = Path(temp.name); (root/'docs').mkdir()
        (root/'README.md').write_text('# Fixture\n\n[Guide](docs/guide.md)\n')
        (root/'docs/guide.md').write_text('# Guide\n')
        manifest = {'schema_version': 1, 'execution_authorization': False,
            'documents': [{'path': 'README.md', 'class': 'current'},
                          {'path': 'docs/guide.md', 'class': 'reference'}],
            'packets': [{'id': 'P01', 'state': 'planned', 'depends_on': [],
                         'gates': ['new-owner-task'], 'start_files': ['README.md']}]}
        self.save(root, 'docs/handoff.json', manifest)
        for name, fields in CHECK.EXPECTED.items():
            data = {}
            for key, value in fields.items():
                target = data; parts = key.split('.')
                for part in parts[:-1]: target = target.setdefault(part, {})
                target[parts[-1]] = value
            self.save(root, name, data)
        return root, manifest

    def save(self, root, name, value):
        p = root/name; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value))

    def test_real_handoff_is_complete_and_checker_does_not_write(self):
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'data').glob('*.json')}
        report = CHECK.check(ROOT)
        self.assertTrue(report['passed'], report['errors'])
        self.assertFalse(report['authorization']); self.assertEqual(report['network_calls'], 0)
        self.assertEqual(before, {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in before})

    def test_broken_link_and_omitted_document_fail(self):
        root, manifest = self.fixture()
        (root/'docs/extra.md').write_text('# New but unclassified')
        (root/'README.md').write_text('[Missing](docs/missing.md) [Malformed](https://[)')
        report = CHECK.check(root)
        self.assertIn('documentation-inventory-mismatch', report['errors'])
        self.assertIn('broken-relative-link:README.md', report['errors'])
        self.assertIn('malformed-link:README.md', report['errors'])

    def test_dependencies_cannot_be_missing_or_cyclic(self):
        root, manifest = self.fixture()
        manifest['packets'][0]['depends_on'] = ['P01']
        self.save(root, 'docs/handoff.json', manifest)
        self.assertIn('packet-dependency-cycle', CHECK.check(root)['errors'])
        manifest['packets'][0]['depends_on'] = ['unknown']
        self.save(root, 'docs/handoff.json', manifest)
        self.assertIn('unknown-dependency:P01', CHECK.check(root)['errors'])

    def test_activation_drift_and_escaping_reference_fail_without_secret_values(self):
        root, manifest = self.fixture()
        manifest['packets'][0]['start_files'] = ['../private-note.md']
        self.save(root, 'docs/handoff.json', manifest)
        self.save(root, 'config/digest.json', {'delivery_enabled': True, 'secret': 'do-not-print-fixture'})
        report = CHECK.check(root)
        self.assertIn('unsafe-reference-path', report['errors'])
        self.assertIn('policy-drift:config/digest.json:delivery_enabled', report['errors'])
        self.assertNotIn('do-not-print-fixture', json.dumps(report))
