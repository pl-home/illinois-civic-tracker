"""Behavioral tests for evidence-based audit decisions, using no private archive."""
import collections
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from civic_tracker.vote_audit import canonical_motion, classify_document, pdf_motion, tally_agrees

RULES = json.loads((Path(__file__).resolve().parents[1]/'config/vote-audit.json').read_text(encoding='utf-8-sig'))


def pdf(motion='THIRD READING', body='Y MemberOne N MemberTwo'):
    return {'date': '2026-05-01', 'pdf_date': '2026-05-01', 'roll_group': 'example-roll',
            'roll_number_displayed': 1, 'source_url': 'https://ilga.gov/example',
            'totals': {'yes': 1, 'no': 1, 'present': 0}, 'motion_context': motion,
            'pdf_text': 'HOUSE BILL 24\n'+motion+'\n1 YEA 1 NAY 0 PRESENT\n'+body}


def csv_roll(motion='THIRD READING', vote='Yea', date='2026-05-01'):
    return {'date': date, 'raw_motion': motion, 'motion': canonical_motion(motion),
            'totals': collections.Counter({'yes': 1, 'no': 1, 'present': 0}), 'subjects': {'fritts': vote}}


def classify(record, rolls, siblings=(), selected=None):
    selected = selected or {'raw': 'Y', 'choice': 'yes'}
    return classify_document(record, selected, rolls, siblings, RULES, 'fritts')[0]


class MotionAuditTests(unittest.TestCase):
    def test_fraction_is_not_a_column_separator(self):
        self.assertEqual(canonical_motion('3/5 VOTE REQUIRED / MOTION TO RECOMMIT HOUSE AMENDMENT NO. 1 / PREVAILED'),
                         'MOTION TO RECOMMIT HOUSE AMENDMENT NO 1')
        self.assertEqual(canonical_motion('3/5 VOTE REQUIRED'), '3/5 VOTE REQUIRED')

    def test_amendment_list_punctuation_preserves_numbers(self):
        expected = 'CONCUR IN SENATE AMENDMENTS NO 1,2,5'
        for raw in ['CONCUR IN SENATE AMENDMENT NO. 1, 2, AND 5',
                    'CONCUR IN SENATE AMENDMENTS NO. 1,2,& 5']:
            self.assertEqual(canonical_motion(raw), expected)
        self.assertNotEqual(canonical_motion('CONCUR IN SENATE AMENDMENT NO. 1'),
                            canonical_motion('CONCUR IN SENATE AMENDMENT NO. 2'))
        self.assertNotEqual(canonical_motion('CONCUR IN SENATE AMENDMENTS'), expected)

    def test_resolution_outcome_is_not_a_new_motion(self):
        self.assertEqual(canonical_motion('RESOLUTIONS /  / ADOPTED'), 'RESOLUTION')
        self.assertNotEqual(canonical_motion('RESOLUTIONS / MOTION TO RECONSIDER'), 'RESOLUTION')
        self.assertEqual(canonical_motion('CONSTITUTIONAL AMENDMENTS / Third Reading / PASSED'), 'THIRD READING')

    def test_procedural_motion_precedes_calendar_caption(self):
        record = pdf('FISCAL NOTE INAPPLICABLE\nHOUSE BILLS\nSECOND READING')
        self.assertEqual(pdf_motion(record, RULES)[0], 'FISCAL NOTE INAPPLICABLE')


class EvidenceDecisionTests(unittest.TestCase):
    def test_explicit_choice_and_tally_match(self):
        self.assertEqual(classify(pdf(), [csv_roll()]), 'resolved-explicit-motion')

    def test_no_vote_label_remains_unknown(self):
        self.assertEqual(classify(pdf(), [csv_roll(vote='No Vote')], selected={'raw': 'NV', 'choice': 'not-voting'}),
                         'retained-no-vote-vs-nv-label-difference')

    def test_contradictory_member_choice_is_retained(self):
        self.assertEqual(classify(pdf(), [csv_roll(vote='Nay')]), 'source-choice-conflict')

    def test_tally_conflict_is_not_a_choice_match(self):
        roll = csv_roll();roll['totals']['yes'] = 2
        self.assertEqual(classify(pdf(), [roll]), 'source-tally-conflict')
        self.assertFalse(tally_agrees({}, roll))

    def test_cross_date_candidate_is_not_repaired(self):
        self.assertEqual(classify(pdf(), [csv_roll(date='2026-05-02')]), 'source-date-conflict')

    def test_cross_date_with_missing_amendment_detail_is_not_a_match(self):
        record=pdf('CONCUR IN SENATE AMENDMENTS')
        roll=csv_roll('CONCUR IN SENATE AMENDMENT NO 1',date='2026-05-02')
        self.assertEqual(classify(record,[roll]),'source-date-and-motion-detail-conflict')

    def test_missing_csv_motion_stays_missing(self):
        self.assertEqual(classify(pdf(), [csv_roll(motion='')]), 'csv-motion-missing')

    def test_tally_only_cannot_fill_a_generic_motion(self):
        self.assertEqual(classify(pdf('CONCUR IN SENATE AMENDMENTS'),
                                 [csv_roll('CONCUR IN SENATE AMENDMENT NO 1')]), 'pdf-amendment-detail-missing')

    def test_same_roster_and_roll_can_supply_explicit_motion(self):
        record = pdf('CONCUR IN SENATE AMENDMENTS')
        explicit = pdf('CONCUR IN SENATE AMENDMENT NO 1')
        self.assertEqual(classify(record, [csv_roll('CONCUR IN SENATE AMENDMENT NO 1')], [explicit]),
                         'resolved-related-roll-document')

    def test_same_tally_with_different_named_votes_is_rejected(self):
        record = pdf('CONCUR IN SENATE AMENDMENTS')
        other = pdf('CONCUR IN SENATE AMENDMENT NO 1', body='N MemberOne Y MemberTwo')
        self.assertEqual(classify(record, [csv_roll('CONCUR IN SENATE AMENDMENT NO 1')], [other]),
                         'pdf-amendment-detail-missing')

    def test_competing_related_motions_are_ambiguous(self):
        record = pdf('CONCUR IN SENATE AMENDMENTS')
        motions = ['CONCUR IN SENATE AMENDMENT NO 1', 'CONCUR IN SENATE AMENDMENT NO 2']
        self.assertEqual(classify(record, [csv_roll(m) for m in motions], [pdf(m) for m in motions]),
                         'ambiguous-related-motion')


if __name__ == '__main__':
    unittest.main()
