"""Deterministic Illinois veto-session metadata and action classification."""
from datetime import date
import json
from pathlib import Path
import re


def load_config(root):
    return json.loads((Path(root) / 'config' / 'veto-session.json').read_text(encoding='utf-8'))


def _day(value):
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def context(config, as_of):
    """Return display-safe context without claiming a daily calendar check."""
    days = sorted(config['session_days'])
    current = _day(as_of)
    if current < _day(days[0]):
        status = 'upcoming'
    elif current > _day(days[-1]):
        status = 'completed'
    elif current.isoformat() in days:
        status = 'active'
    else:
        status = 'between-published-session-days'
    return {'id': config['id'], 'general_assembly': config['general_assembly'],
            'label': config['label'], 'session_days': days, 'status': status,
            'calendar_status': config['calendar_status'],
            'calendar_urls': config['calendar_urls'], 'scope_note': config['scope_note']}


_RULES = (
    ('gubernatorial-veto', r'\bveto(?:ed|es)?\b.{0,80}\bgovernor\b|\bgovernor\b.{0,80}\bveto(?:ed|es)?\b'),
    ('governor-recommendations', r'\breturned\b.{0,100}\brecommendations?\b|\brecommendations?\b.{0,100}\bgovernor\b'),
    ('reduced-or-vetoed-appropriation', r'\bappropriat(?:ion|ions|ed)\b.{0,100}\b(?:reduc|veto)'),
    ('veto-session-procedure', r'\b(?:motion|message|notice|resolution)s?\b'),
)


def classify_action(text):
    """Return explainable scope labels from an official action description."""
    value = re.sub(r'\s+', ' ', str(text or '')).strip()
    return [label for label, pattern in _RULES if re.search(pattern, value, re.I)]
