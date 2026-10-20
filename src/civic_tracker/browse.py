"""Build a public, offline-capable historical browser; no requests or secrets.

The reviewed export establishes inclusion and last-action fields, not the
subject's precise sponsorship role, original filer, or votes. Do not fill those
gaps from the chief-sponsor column. This is separate from M1 collection.
"""
import argparse
import csv
from datetime import datetime
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
import shutil

from .rules import ceremonial, shell


def records_from_export(path, ga, subject_id):
    records = []
    seen = set()
    with path.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            # DictReader ignores blank lines. Any nonempty malformed row fails.
            ident = row['Legislation']
            match = re.fullmatch(r'(HB|SB|HR|SR|HJR|SJR)(\d{4})', ident)
            if not match or ident in seen:
                raise ValueError('Invalid or duplicate measure ID')
            seen.add(ident)
            typ, number = match.groups()
            source_code = {'HJR': 'HJ', 'SJR': 'SJ'}.get(typ, typ)
            date = datetime.strptime(row['Floor Action Date'], '%m/%d/%Y').date().isoformat()
            title = row['ABR'].strip()
            if not title or not row['Floor Action Description'].strip():
                raise ValueError('Missing export title or action')
            hidden = ceremonial(title)
            records.append({
                'id': f'ga{ga}-{typ.lower()}{int(number)}',
                'measure': ident, 'type': typ, 'ga': ga, 'subject_id': subject_id,
                'title': title, 'last_action_date': date,
                'last_action_chamber': row['Floor Action Chamber'],
                'last_action': row['Floor Action Description'],
                'listed_chief_sponsor': row['Chief Sponsor'],
                'listed_alternate_chief_sponsor': row['Alt Chief Sponsor'],
                'subject_role': None, 'original_filer': None, 'topics': [],
                'ceremonial': hidden,
                'hidden_reason': 'Ceremonial short-description rule' if hidden else None,
                'shell_title_flag': shell(title, ''),
                'official_url': f'https://ftp.ilga.gov/Legislation/{ga}/BillStatus/XML/{ga}00{source_code}{int(number):04d}.xml',
                'historical_baseline': True,
            })
    if not records:
        raise ValueError('Empty export cannot be presented as successful coverage')
    # Event dates, not build or import times, determine the browsing order.
    return sorted(records, key=lambda r: (r['last_action_date'], r['measure']), reverse=True)


def card(record):
    def e(value):
        return escape(str(value), quote=True)

    flags = ''
    if record['ceremonial']:
        flags += '<span class="tag quiet">Ceremonial · hidden by default</span>'
    if record['shell_title_flag']:
        flags += '<span class="tag">Technical-title flag · rewrite not assessed</span>'
    fields = [
        ('Last action in export', record['last_action']),
        ('Action chamber', record['last_action_chamber']),
        ('Chief sponsor listed in export', record['listed_chief_sponsor'] or 'Not listed'),
        ('Alternate chief sponsor listed', record['listed_alternate_chief_sponsor'] or 'Not listed'),
        ('Fritts’s exact role', 'Not established by this export'),
        ('Original filer / introduction', 'Not established by this export'),
        ('Topic', 'Not yet assessed'),
    ]
    if record['hidden_reason']:
        fields.append(('Why hidden', record['hidden_reason']))
    search = ' '.join(str(record[key]) for key in (
        'measure', 'title', 'last_action', 'last_action_chamber',
        'listed_chief_sponsor', 'listed_alternate_chief_sponsor'))
    measure_type, measure_number = re.fullmatch(r'([A-Z]+)(\d+)', record['measure']).groups()
    search += f' {measure_type}{int(measure_number)} {measure_type} {int(measure_number)}'
    return f'''<article class="record" id="{e(record['id'])}" data-type="{e(record['type'])}" data-ceremonial="{str(record['ceremonial']).lower()}" data-search="{e(search)}">
<details><summary><span class="measure">{e(record['measure'])}</span><span class="record-title">{e(record['title'])}</span><time datetime="{e(record['last_action_date'])}">{e(record['last_action_date'])}</time><span class="expand" aria-hidden="true">+</span></summary>
<div class="record-body"><div class="tags">{flags}</div><dl>{''.join(f'<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k, v in fields)}</dl>
<div class="record-links"><a href="{e(record['official_url'])}">Official bill record (XML) ↗</a><a href="#{e(record['id'])}" class="permalink">Link to this item</a></div>
<p class="record-note">Historical export entry. The date is a legislative action date, not a new tracker alert. Official links may reflect later changes.</p></div></details></article>'''


def build(root, output):
    config = json.loads((root / 'config/browse.json').read_text(encoding='utf-8'))
    if config['schema_version'] != 1:
        raise ValueError('Unsupported browse schema')
    export = root / config['export_path']
    records = records_from_export(export, config['ga'], config['export_subject_id'])
    if len(records) != config['expected_records']:
        raise ValueError('Reviewed baseline record count changed; review before publishing')
    payload = {
        'schema_version': 1, 'mode': 'historical-baseline',
        'source_reviewed_on': config['export_reviewed_on'],
        'source_export_sha256': sha256(export.read_bytes()).hexdigest(),
        'source_member_url': config['export_source_url'],
        'source_note': 'Reviewed sponsorship export; exact subject role and original filer are not supplied. Review date is not a source retrieval timestamp.',
        'automatic_collection_enabled': False, 'records': records,
    }
    substitutions = {
        'TITLE': escape(config['title']), 'COUNT': str(len(records)),
        'QUIET_COUNT': str(sum(r['ceremonial'] for r in records)),
        'REVIEWED_ON': escape(config['export_reviewed_on']),
        'RECORDS': '\n'.join(card(record) for record in records),
        'COVERAGE': ''.join(f'<li><strong>{escape(item["name"])}</strong><span>{escape(item["status"])}</span></li>' for item in config['coverage']),
    }
    template = (root / 'web/archive.html').read_text(encoding='utf-8')
    for key, value in substitutions.items():
        template = template.replace('{{' + key + '}}', value)
    if re.search(r'\{\{[A-Z_]+\}\}', template):
        raise ValueError('Unresolved page template')
    # Write an allowlisted artifact only. Never recursively copy the repository.
    artifact_names = {'index.html', 'archive.html', 'dashboard.json', 'records.json', 'styles.css', 'app.js', 'dashboard.js', '.nojekyll', 'changes.json', 'changes.atom', 'digest-preview.html', 'digest-preview.txt', 'digest-preview.json', 'digest-preview.css'}
    from .member_history import artifact_names as history_names, build_pages
    managed_history_names = history_names()
    if output.is_symlink() or (output.exists() and any(
            item.name not in artifact_names | managed_history_names or not item.is_file() or item.is_symlink()
            for item in output.iterdir())):
        raise ValueError('Output must contain only the allowlisted public artifact files')
    output.mkdir(parents=True, exist_ok=True)
    from .dashboard import render
    homepage, snapshot = render(root)
    history_pages, history_report = build_pages(root, snapshot)
    from .change_feed import build as build_change_feed
    build_change_feed(root, output)
    from .digest import artifacts as digest_artifacts
    digest_pages, digest_report = digest_artifacts(root)
    for name, content in digest_pages.items():
        (output/name).write_text(content, encoding='utf-8', newline='\n')
    (output / 'index.html').write_text(homepage, encoding='utf-8', newline='\n')
    (output / 'archive.html').write_text(template, encoding='utf-8', newline='\n')
    (output / 'dashboard.json').write_text(json.dumps(snapshot, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8', newline='\n')
    (output / 'records.json').write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8', newline='\n')
    for name in ('styles.css', 'app.js', 'dashboard.js'):
        shutil.copyfile(root / 'web' / name, output / name)
    (output / '.nojekyll').write_text('', encoding='utf-8')
    for name, content in history_pages.items():
        (output / name).write_text(content, encoding='utf-8', newline='\n')
    # Remove obsolete generated pages only, after the closed file/symlink check.
    for item in output.iterdir():
        if item.name in managed_history_names and item.name not in history_pages:
            item.unlink()
    artifact_bytes = sum((output / name).stat().st_size for name in artifact_names)
    if artifact_bytes > 650_000:
        raise ValueError('browser-artifact-size-budget-exceeded')
    return {'records': len(records), 'ceremonial': sum(r['ceremonial'] for r in records),
            'artifact_bytes': artifact_bytes + history_report['artifact_bytes'],
            'base_artifact_bytes': artifact_bytes, 'member_history': history_report, 'digest_preview': digest_report}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('.local/site'))
    args = parser.parse_args()
    print(json.dumps(build(Path.cwd(), args.output)))


if __name__ == '__main__':
    main()
