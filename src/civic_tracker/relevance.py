"""Explicit topic and noise reasons. Relevance never represents an owner's stance."""
from collections import Counter
from pathlib import Path
import re
from .changes import read
from .rules import ceremonial


def explain(fact, config=None):
    config = config or read(Path(__file__).resolve().parents[2]/'config/relevance.json')
    text = fact.get('title', '') + ' ' + fact.get('detail', '')
    # Structural associations outrank provisional words; a committee referral is
    # not a claim about the bill's current amended text or an owner's position.
    committees = list(fact.get('committee_names', []))
    committees += re.findall(r'(?:Assigned|Referred) to ([^;\n]+)', fact.get('detail', ''), re.I)
    statutes = fact.get('statutes', [])
    topics = []
    for topic, rule in config['topics'].items():
        reasons = ['committee association: ' + value for value in committees if value.casefold() in {c.casefold() for c in rule['committees']}]
        reasons += ['statute reference: ' + value for value in statutes if any(re.match(re.escape(prefix) + r'(?:\b|/)', value, re.I) for prefix in rule['statutes'])]
        structural = bool(reasons)
        if not reasons:
            match = next((re.search(r'\b' + re.escape(word) + r'\b', text, re.I) for word in rule['keywords'] if re.search(r'\b' + re.escape(word) + r'\b', text, re.I)), None)
            if match: reasons = ['provisional keyword: ' + match[0].casefold()]
        if reasons: topics.append({'topic': topic, 'basis': 'structural' if structural else 'keyword-provisional', 'reasons': reasons})
    hidden = []
    if fact.get('kind') in {'filing', 'sponsor-role', 'bill-action', 'bill-title', 'vote'} and ceremonial(fact.get('title', '')):
        hidden.append('ceremonial short-description rule; preserved in index')
    totals = fact.get('totals', {})
    # Zero recorded nays is weaker than unanimity: absences and missing choices
    # are not silently converted to support, and missing tally is never zero.
    if fact.get('kind') == 'vote' and any(type(totals.get(key)) is int and totals[key] == 0 for key in ('no', 'nays', 'nay')):
        hidden.append('no recorded opposition in source tally; index-only, not a unanimity claim')
    return {'topics': topics, 'hidden': bool(hidden), 'reasons': hidden or ['tracked subject activity retained; topic match is not required'], 'stance': 'not inferred'}


def audit(ledger):
    counts = Counter(); topics = Counter()
    for row in ledger['facts'].values():
        result = explain(row['fact'])
        for reason in result['reasons']: counts[reason] += 1
        for topic in result['topics']: topics[topic['topic']] += 1
    return {'policy': 'deterministic-v1', 'reason_counts': dict(counts), 'topic_counts': dict(topics),
            'stance': 'not inferred', 'source_limit': 'Official compact XML does not supply statute citations; absent structure uses provisional words only.'}
