"""Offline audit of the remaining M0 vote comparison cases.

This classifies evidence; it never edits source votes or silently fills missing motions.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import collections
import csv
import json
import hashlib
import re

from .vote_csv import bill_id, choice, motion as legacy_motion, subject_id


def canonical_motion(value):
    text = ' '.join(value.upper().split()).replace('.', '')
    # A slash surrounded by spaces separates report columns. A fraction does not.
    parts = [part.strip() for part in re.split(r'(?<=\s)/(?=\s)', text)]
    prefixes = {'HOUSE BILL', 'HOUSE BILLS', 'SENATE BILL', 'SENATE BILLS',
                'CONSTITUTIONAL AMENDMENTS'}
    resolution_captions = {'RESOLUTION', 'RESOLUTIONS', 'JOINT RESOLUTIONS'}
    outcomes = {'', 'ADOPTED', 'PASSED'}
    if parts[0] in resolution_captions:
        if all(part in outcomes for part in parts[1:]):
            return 'RESOLUTION'
        return ' / '.join(parts)
    while len(parts) > 1 and (parts[0] in prefixes or re.fullmatch(r'\d+/\d+ VOTE REQUIRED', parts[0])):
        parts.pop(0)
    text = parts[0]
    text = re.sub(r'#\s*(?=\d)', 'NO ', text)
    text = re.sub(r'\bNO\s*(\d+)', r'NO \1', text)
    amended = re.fullmatch(r'(CONCUR IN (?:SENATE|HOUSE) AMENDMENTS?) (?:NOS? )?([\d ,&]+(?:AND[\d ,&]+)?)', text)
    if amended:
        numbers = sorted({int(number) for number in re.findall(r'\d+', amended[2])})
        prefix = re.sub(r'AMENDMENTS?$', 'AMENDMENTS', amended[1])
        return prefix + ' NO ' + ','.join(map(str, numbers))
    if text in {'RESOLUTION', 'RESOLUTIONS'}:
        return 'RESOLUTION'
    return text


def pdf_motion(record, rules):
    header = []
    for line in record.get('pdf_text', '').splitlines()[:35]:
        if re.search(r'\d+\s+YEAS?\s+\d+\s+NAYS?', line, re.I):
            break
        header.append(' '.join(line.upper().split()))
    # Procedural motions take priority over a surrounding reading/calendar caption.
    for pattern in rules['pdf_motion_patterns']:
        for line in header:
            if re.fullmatch(pattern, line):
                return canonical_motion(line), line, 'pdf-header'
    label = record.get('label', '')
    explicit = re.search(r' - (Third Reading|Second Reading) - ', label, re.I)
    if explicit:
        return canonical_motion(explicit[1]), explicit[1], 'official-index-label'
    return canonical_motion(record.get('motion_context', '')), record.get('motion_context', ''), 'retained-context'


def csv_rolls(path):
    rolls = {}
    with path.open(encoding='utf-8-sig', newline='') as handle:
        for row in csv.DictReader(handle):
            key = tuple(row[name] for name in ['GA', 'Chamber', 'Session', 'Legislation', 'Vote Type', 'Vote Date'])
            roll = rolls.setdefault(key, {'bill': bill_id(row['Legislation']), 'chamber': row['Chamber'],
                'date': row['Vote Date'], 'raw_motion': row['Vote Type'],
                'motion': canonical_motion(row['Vote Type']), 'totals': collections.Counter(), 'subjects': {}})
            roll['totals'][choice(row['Vote'])] += 1
            who = subject_id(row['Member'])
            if who:
                roll['subjects'][who] = row['Vote']
    return list(rolls.values())


def tally_agrees(record, roll):
    return all(record.get('totals', {}).get(key) == roll['totals'][key] for key in ['yes', 'no', 'present'])


def candidate_view(roll, who):
    return {'date': roll['date'], 'raw_motion': roll['raw_motion'], 'canonical_motion': roll['motion'],
            'raw_choice': roll['subjects'].get(who),
            'totals': {key: roll['totals'][key] for key in ['yes', 'no', 'present']}}


def roster_digest(record):
    text = record.get('pdf_text', '')
    tally = re.search(r'\d+\s+YEAS?\s+\d+\s+NAYS?\s+\d+\s+PRESENT', text, re.I)
    if not tally:
        return None
    body = ' '.join(text[tally.end():].split())
    return hashlib.sha256(body.encode()).hexdigest() if body else None


def classify_document(record, selected, eligible, siblings, rules, who):
    normalized, raw, basis = pdf_motion(record, rules)
    same_date = [roll for roll in eligible if roll['date'] == record['date']]
    exact = [roll for roll in same_date if roll['motion'] == normalized]
    corroborating = None
    if not exact and record.get('roll_group') and roster_digest(record):
        supported = collections.defaultdict(list)
        for other in siblings:
            # The complete normalized named-vote body must match, not merely totals.
            if (not record.get('roll_number_displayed') or
                other.get('roll_number_displayed') != record['roll_number_displayed'] or
                other.get('pdf_date') != record.get('pdf_date') or
                roster_digest(other) != roster_digest(record)):
                continue
            other_motion, other_raw, _ = pdf_motion(other, rules)
            matches = [roll for roll in same_date if roll['motion'] == other_motion and tally_agrees(record, roll)]
            if matches:
                supported[other_motion].append((other, other_raw, matches))
        if len(supported) > 1:
            candidates = [roll for entries in supported.values() for _, _, matches in entries for roll in matches]
            return 'ambiguous-related-motion', candidates, None, normalized, raw, basis
        if supported:
            other, other_raw, exact = next(iter(supported.values()))[0]
            corroborating = {'source_url': other['source_url'], 'motion': other_raw,
                             'roll_group': other['roll_group'], 'roster_sha256': roster_digest(record)}
    if exact:
        if not all(tally_agrees(record, roll) for roll in exact):
            category = 'source-tally-conflict'
        elif all(choice(roll['subjects'][who]) == selected['choice'] for roll in exact):
            category = 'resolved-related-roll-document' if corroborating else 'resolved-explicit-motion'
        elif selected['raw'] == 'NV' and all(roll['subjects'][who] == 'No Vote' for roll in exact):
            category = 'retained-no-vote-vs-nv-label-difference'
        else:
            category = 'source-choice-conflict'
        return category, exact, corroborating, normalized, raw, basis
    blank = [roll for roll in same_date if not roll['motion'].strip() and tally_agrees(record, roll)]
    cross_date = [roll for roll in eligible if roll['date'] != record['date'] and roll['motion'] == normalized and tally_agrees(record, roll)]
    cross_detail = [roll for roll in eligible if roll['date'] != record['date'] and tally_agrees(record, roll) and
                    normalized in {'CONCUR IN SENATE AMENDMENTS', 'CONCUR IN HOUSE AMENDMENTS'} and roll['motion'].startswith(normalized+' NO ')]
    if blank:
        category, candidates = 'csv-motion-missing', blank
    elif cross_date:
        category, candidates = 'source-date-conflict', cross_date
    elif cross_detail:
        category, candidates = 'source-date-and-motion-detail-conflict', cross_detail
    else:
        detailed = [roll for roll in same_date if tally_agrees(record, roll) and (
            (normalized in {'CONCUR IN SENATE AMENDMENTS', 'CONCUR IN HOUSE AMENDMENTS'} and roll['motion'].startswith(normalized+' NO ')) or
            (normalized == 'MOTION TO RECOMMIT' and roll['motion'].startswith(normalized+' HOUSE AMENDMENT NO ')))]
        captioned = [roll for roll in same_date if tally_agrees(record, roll) and re.search(
            r'BILLS? \d+ FA \d+ / '+re.escape(normalized)+r'(?: /|$)', roll['raw_motion'].upper())]
        if detailed:
            category, candidates = 'pdf-amendment-detail-missing', detailed
        elif captioned:
            category, candidates = 'csv-amendment-caption-detail', captioned
        else:
            category, candidates = 'unresolved-motion-metadata', same_date
    return category, candidates, None, normalized, raw, basis


def audit(root, archive_path):
    baseline = json.loads((root/'docs/evidence/m0-vote-reconciliation.json').read_text(encoding='utf-8'))
    archive = json.loads(archive_path.read_text(encoding='utf-8'))
    config = json.loads((root/'config/project.json').read_text(encoding='utf-8'))
    rules = json.loads((root/'config/vote-audit.json').read_text(encoding='utf-8'))
    members = {str(item['official_member_id']): item['id'] for item in config['subjects']}
    rolls = csv_rolls(root/'.local/104MemberVotes.csv')
    by_measure = collections.defaultdict(list)
    for roll in rolls:
        by_measure[(roll['bill'], roll['chamber'])].append(roll)
    documents = collections.defaultdict(list)
    related = collections.defaultdict(list)
    for record in archive['votes'].values():
        if record.get('scope') != 'floor':
            continue
        for selected in record['choices']:
            who = members.get(str(selected['member_id']))
            if not who:
                continue
            key = (who, bill_id(record['measure_id'].split('-')[-1]), record['chamber'], record['date'], legacy_motion(record.get('motion_context', '')))
            documents[key].append((record, selected))
            if record.get('roll_group'):
                group = (who, record['roll_group'], record['date'], record['chamber'], record['measure_id'])
                related[group].append(record)
    outcomes = []
    for case in baseline['mismatches']:
        key = tuple(case['key']); who, bill, chamber, date, old_motion = key
        evidence = []
        classifications = []
        for record, selected in documents[key]:
            eligible = [roll for roll in by_measure[(bill, chamber)] if who in roll['subjects']]
            group = (who, record.get('roll_group'), date, chamber, record['measure_id'])
            category, candidates, corroborating, normalized, raw, basis = classify_document(
                record, selected, eligible, related.get(group, []), rules, who)
            classifications.append(category)
            item = {'source_url': record['source_url'], 'source_sha256': record.get('evidence', {}).get('sha256'),
                    'roll_group': record.get('roll_group'), 'index_date': date, 'pdf_date': record.get('pdf_date'),
                    'pdf_motion': raw, 'motion_basis': basis, 'canonical_motion': normalized,
                    'pdf_raw_choice': selected['raw'], 'pdf_choice': selected['choice'],
                    'pdf_totals': record.get('totals'), 'classification': category,
                    'csv_candidates': [candidate_view(roll, who) for roll in candidates]}
            if record.get('pdf_date') != date:
                item['retained_date_conflict'] = True
            if corroborating:
                item['related_document'] = corroborating
            evidence.append(item)
        # Every original comparison key remains visible, even when it had duplicate PDFs.
        resolved = bool(classifications) and all(value.startswith('resolved-') for value in classifications)
        outcomes.append({'original_key': key, 'resolved_exact_choice': resolved,
                         'classifications': sorted(set(classifications)), 'documents': evidence})
    report = {'observed_at': datetime.now(timezone.utc).isoformat(),
              'method': 'Offline classification of the original 215 keys. Explicit header/index motions and same-roll sibling documents only; raw choices, missing CSV motion, dates and tally conflicts retained. No inferred equivalence for No Vote.',
              'baseline_unique_keys': baseline['unique_verified_floor_keys'],
              'baseline_exact_choice_matches': baseline['exact_choice_matches'],
              'cases_reviewed': len(outcomes), 'additional_keys_resolved': sum(item['resolved_exact_choice'] for item in outcomes),
              'case_classifications': dict(collections.Counter(category for item in outcomes for category in item['classifications'])),
              'cases': outcomes}
    report['exact_or_evidence_resolved_keys'] = report['baseline_exact_choice_matches'] + report['additional_keys_resolved']
    report['baseline_key_coverage_rate'] = report['exact_or_evidence_resolved_keys']/report['baseline_unique_keys']
    (root/'docs/evidence/m0-vote-audit.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'cases'}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    args = parser.parse_args()
    audit(Path.cwd(), args.archive)

if __name__ == '__main__':
    main()
