import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from civic_tracker.browse import build, card, records_from_export
from civic_tracker.privacy import violations
from civic_tracker.member_history import build_pages, MAX_HISTORY_BYTES

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/fritts-sponsorship-104.csv'


class BrowseTests(unittest.TestCase):
    def test_export_preserves_facts_and_does_not_invent_roles(self):
        records = records_from_export(FIXTURE, 104, 'fritts')
        with FIXTURE.open(encoding='utf-8', newline='') as stream:
            rows = {r['Legislation']: r for r in csv.DictReader(stream)}
        self.assertEqual(len(records), 134)
        self.assertEqual(sum(r['ceremonial'] for r in records), 24)
        self.assertEqual([r['last_action_date'] for r in records], sorted(
            [r['last_action_date'] for r in records], reverse=True))
        for record in records:
            source = rows[record['measure']]
            self.assertEqual(record['listed_chief_sponsor'], source['Chief Sponsor'])
            self.assertEqual(record['last_action'], source['Floor Action Description'])
            self.assertIsNone(record['subject_role'])
            self.assertIsNone(record['original_filer'])
            self.assertTrue(record['historical_baseline'])
            self.assertEqual(record['topics'], [])
        joint = next(r for r in records if r['measure'] == 'HJR0012')
        self.assertTrue(joint['official_url'].endswith('/10400HJ0012.xml'))

    def test_artifact_is_bounded_deterministic_private_data_free_and_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'site'
            report = build(ROOT, output)
            first = {p.name: p.read_bytes() for p in output.iterdir()}
            self.assertEqual(build(ROOT, output), report)
            self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, first)
            history, _ = build_pages(ROOT, json.loads(first['dashboard.json']))
            self.assertEqual(set(first), {'index.html', 'archive.html', 'dashboard.json', 'styles.css', 'app.js', 'dashboard.js', 'records.json', '.nojekyll', 'changes.json', 'changes.atom'} | set(history))
            self.assertLess(report['base_artifact_bytes'], 650_000)
            self.assertLess(report['member_history']['artifact_bytes'], MAX_HISTORY_BYTES)
            self.assertEqual(report['artifact_bytes'], sum(len(b) for b in first.values()))
            for name in first:
                self.assertEqual(violations(first[name].decode()), [], name)
            homepage = BeautifulSoup(first['index.html'].decode(), 'html.parser')
            self.assertEqual(len(homepage.select('.member-card')), 5)
            self.assertIn('witness', homepage.get_text().lower())
            html = BeautifulSoup(first['archive.html'].decode(), 'html.parser')
            cards = html.select('.record')
            payload = json.loads(first['records.json'])
            self.assertEqual(len(cards), 134)
            self.assertEqual(len({c['id'] for c in cards}), 134)
            self.assertEqual(sum(c['data-ceremonial'] == 'true' for c in cards), 24)
            self.assertFalse(payload['automatic_collection_enabled'])
            self.assertEqual(payload['mode'], 'historical-baseline')
            self.assertEqual(html.select_one('script')['src'], 'app.js')
            self.assertIsNotNone(html.select_one('noscript'))
            for record in payload['records']:
                item = html.find(id=record['id'])
                self.assertEqual(item.select_one('.record-links a')['href'], record['official_url'])
                self.assertIn(record['last_action_date'], item.get_text())
            self.assertNotIn('{{', first['index.html'].decode())
            self.assertNotIn('{{', first['archive.html'].decode())

    def test_untrusted_source_text_is_rendered_as_text(self):
        record = records_from_export(FIXTURE, 104, 'fritts')[0]
        record['title'] = '<img src=x onerror="alert(1)">'
        record['last_action'] = '<script>bad()</script>'
        record['listed_chief_sponsor'] = 'A & B "quoted"'
        html = BeautifulSoup(card(record), 'html.parser')
        self.assertIsNone(html.find('script'))
        self.assertIsNone(html.find('img'))
        self.assertEqual(html.select_one('.record-title').get_text(), record['title'])
        self.assertIn(record['last_action'], html.get_text())

    def test_malformed_duplicate_or_empty_export_fails_closed(self):
        with FIXTURE.open(encoding='utf-8', newline='') as stream:
            reader = csv.DictReader(stream)
            fields = reader.fieldnames
            row = next(reader)
        cases = [[], [row, row], [{**row, 'Legislation': '../HB0024'}],
                 [{**row, 'Floor Action Date': 'not-a-date'}]]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'export.csv'
            for rows in cases:
                with path.open('w', encoding='utf-8', newline='') as stream:
                    writer = csv.DictWriter(stream, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(rows)
                with self.assertRaises(ValueError):
                    records_from_export(path, 104, 'fritts')

    def test_output_directory_cannot_accidentally_publish_other_files(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / 'unreviewed.txt').write_text('synthetic private material')
            with self.assertRaisesRegex(ValueError, 'allowlisted'):
                build(ROOT, path)
            self.assertFalse((path / 'index.html').exists())

    def test_only_obsolete_generated_member_pages_are_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)
            obsolete=path/'member-fritts-99.html'
            obsolete.write_text('obsolete generated page')
            build(ROOT,path)
            self.assertFalse(obsolete.exists())
            self.assertTrue((path/'member-fritts.html').exists())
            invalid=path/'member-unknown.html'
            invalid.write_text('not an allowlisted member page')
            with self.assertRaisesRegex(ValueError,'allowlisted'):build(ROOT,path)
            self.assertTrue(invalid.exists())


if __name__ == '__main__':
    unittest.main()
