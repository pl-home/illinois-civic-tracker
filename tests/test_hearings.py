"""Synthetic HTML checks for the public hearing fallback, not raw source snapshots."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from civic_tracker.hearings import parse_hearing_details

URL='https://ilga.gov/House/hearings/details/3062/23132'
COLUMNS='<tr>'+''.join('<th>'+name+'</th>' for name in ['Bill #','Motion','Vote Motion','Vote Total','Vote Result','Witness Slip Results'])+'</tr>'
ROW='<tr><td><a href="/legislation/BillStatus?DocTypeID=HB&amp;DocNum=24">HB0024 (SFA2)</a></td><td>Concur</td><td>Do Pass</td><td>1 - 0 - 0</td><td>Passed</td><td><a title="View Witness Slips" href="../../Results?View=Bill">Results</a></td></tr>'
FIELDS='<table><tr><td><span>Date: </span>5/27/2026 8:00 AM</td></tr><tr><td><span>Location:</span>Room 114</td></tr><tr><td><span>Posting Date: </span>5/21/2026 11:12 PM</td></tr></table>'


def html(row=ROW,fields=FIELDS,columns=COLUMNS,duplicate=False):
    table='<table>'+columns+row+'</table>'
    return '<main><h2>House Example Committee Hearing Details - 104th General Assembly (2025-2026)</h2>'+fields+table+(table if duplicate else '')+'</main>'


class HearingTests(unittest.TestCase):
    def test_hearing_date_is_not_posting_date(self):
        r=parse_hearing_details(html(),URL)
        self.assertEqual(r['date_local'],'2026-05-27T08:00')
        self.assertEqual(r['posting_date_local'],'2026-05-21T23:12')
        self.assertFalse(r['source_timezone_explicit'])

    def test_amendment_and_historical_results_are_distinct(self):
        r=parse_hearing_details(html(),URL)['items'][0]
        self.assertEqual((r['bill'],r['amendment']),('HB24','SFA2'))
        self.assertIsNone(r['witness_slip_url'])
        self.assertIn('/hearings/Results?',r['witness_results_url'])

    def test_duplicate_views_are_deduplicated(self):
        self.assertEqual(len(parse_hearing_details(html(duplicate=True),URL)['items']),1)

    def test_conflicting_duplicate_dates_fail(self):
        field=FIELDS.replace('5/27/2026 8:00 AM','5/28/2026 8:00 AM')
        with self.assertRaisesRegex(ValueError,'Conflicting'):parse_hearing_details(html(fields=FIELDS+field),URL)

    def test_conflicting_duplicate_bill_result_fails(self):
        with self.assertRaisesRegex(ValueError,'Conflicting'):
            parse_hearing_details(html(row=ROW+ROW.replace('1 - 0 - 0','2 - 0 - 0')),URL)

    def test_changed_table_columns_fail(self):
        with self.assertRaisesRegex(ValueError,'columns changed'):
            parse_hearing_details(html(columns=COLUMNS.replace('Vote Total','New Label')),URL)

    def test_posting_date_cannot_replace_missing_hearing_date(self):
        fields=FIELDS.replace('<tr><td><span>Date: </span>5/27/2026 8:00 AM</td></tr>','')
        with self.assertRaisesRegex(ValueError,'Missing hearing field: Date'):parse_hearing_details(html(fields=fields),URL)

    def test_external_bill_link_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'link host'):
            parse_hearing_details(html(row=ROW.replace('/legislation/BillStatus?','https://unrelated.example/BillStatus?')),URL)

    def test_permalink_must_match_the_displayed_measure(self):
        with self.assertRaisesRegex(ValueError,'permalink disagree'):
            parse_hearing_details(html(row=ROW.replace('DocNum=24','DocNum=25')),URL)

    def test_an_observed_create_link_can_be_recorded(self):
        row=ROW.replace('href="../../Results?View=Bill"','href="./CreateWitnessSlip?bill=24"')
        self.assertIn('/CreateWitnessSlip?',parse_hearing_details(html(row=row),URL)['items'][0]['witness_slip_url'])

if __name__=='__main__':unittest.main()
