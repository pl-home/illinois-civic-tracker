"""Offline, read-only handoff consistency check. A pass is not authorization."""
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


EXPECTED = {
    'config/digest.json': {'delivery_enabled': False},
    'config/pdf-extraction.json': {'routine_enabled': False, 'paid_ocr_fallback': False},
    'config/rollcall-evaluation.json': {'routine_enabled': False},
    'config/rollcall-diagnostics-v2.json': {'routine_enabled': False},
    'config/inference-plan.json': {'enabled': False},
    'config/media.json': {'enabled': True, 'inference.enabled': True,
                          'inference.daily_cap_usd': '0.02',
                          'inference.weekly_cap_usd': '0.20',
                          'inference.lifetime_cap_usd': '20'},
    'config/daily.json': {'enabled': True, 'timezone': 'America/Chicago',
                          'start_hour': 1, 'review_before': '2027-01-03'},
}
CLASSES = {'current', 'reference', 'historical', 'deferred'}
STATES = {'planned', 'owner-gated', 'source-dependent', 'future-design'}


def check(root):
    root = root.resolve(); errors = []

    def local(name):
        if not isinstance(name, str):
            errors.append('non-string-path'); return None
        p = Path(name)
        if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name:
            errors.append('unsafe-reference-path'); return None
        result = root / p
        if not result.resolve().is_relative_to(root):
            errors.append('reference-outside-root'); return None
        if not result.is_file():
            errors.append('missing:' + name); return None
        return result

    def read(name):
        p = local(name)
        if p is None: return {}
        try:
            value = json.loads(p.read_text(encoding='utf-8'))
            if not isinstance(value, dict):
                errors.append('json-object-required:' + name); return {}
            return value
        except (OSError, ValueError, UnicodeError):
            errors.append('unreadable-json:' + name); return {}

    manifest = read('docs/handoff.json')
    if manifest.get('schema_version') != 1 or manifest.get('execution_authorization') is not False:
        errors.append('handoff-schema-or-authorization')
    docs = manifest.get('documents', [])
    if not isinstance(docs, list): docs = []; errors.append('documents-shape')
    names = []
    for item in docs:
        if not isinstance(item, dict): errors.append('document-shape'); continue
        name = item.get('path')
        if not isinstance(name, str): errors.append('document-path'); continue
        names.append(name)
        if item.get('class') not in CLASSES: errors.append('document-class:' + name)
        p = local(name)
        if not p: continue
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', p.read_text(encoding='utf-8')):
            target = target.strip('<>')
            try: url = urlsplit(target)
            except ValueError:
                errors.append('malformed-link:' + name); continue
            if url.scheme or url.netloc or not url.path: continue
            resolved = p.parent / unquote(url.path)
            if not resolved.resolve().is_relative_to(root) or not resolved.exists():
                errors.append('broken-relative-link:' + name)
    inventory = {p.relative_to(root).as_posix() for p in root.glob('*.md')}
    inventory |= {p.relative_to(root).as_posix() for p in (root/'docs').rglob('*.md')}
    if len(names) != len(set(names)) or set(names) != inventory:
        errors.append('documentation-inventory-mismatch')
    packets = manifest.get('packets', [])
    if not isinstance(packets, list): packets = []; errors.append('packets-shape')
    ids = [p.get('id') for p in packets if isinstance(p, dict)]
    if any(not isinstance(i, str) for i in ids) or len(ids) != len(packets) or len(ids) != len(set(ids)):
        errors.append('packet-identities'); packets = []
    graph = {}
    for packet in packets:
        ident = packet['id']; deps = packet.get('depends_on', [])
        if not isinstance(deps, list) or any(d not in ids for d in deps):
            errors.append('unknown-dependency:' + ident); deps = []
        graph[ident] = deps
        if packet.get('state') not in STATES: errors.append('packet-state:' + ident)
        if not packet.get('gates') or not packet.get('start_files'):
            errors.append('packet-missing-boundary:' + ident)
        for name in packet.get('start_files', []): local(name)
    visited = set(); active = set()

    def visit(node):
        if node in active: errors.append('packet-dependency-cycle'); return
        if node in visited: return
        active.add(node)
        for child in graph[node]: visit(child)
        active.remove(node); visited.add(node)
    for node in graph: visit(node)
    for name, expected in EXPECTED.items():
        value = read(name)
        for key, wanted in expected.items():
            actual = value
            for part in key.split('.'):
                actual = actual.get(part) if isinstance(actual, dict) else None
            if type(actual) is not type(wanted) or actual != wanted:
                errors.append('policy-drift:' + name + ':' + key)
    return {'passed': not errors, 'errors': sorted(set(errors)),
            'documents': len(names), 'packets': len(packets),
            'authorization': False, 'live_health_verified': False,
            'network_calls': 0, 'model_calls': 0, 'writes': 0}


if __name__ == '__main__':
    result = check(Path(__file__).resolve().parents[1])
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result['passed'] else 1)
