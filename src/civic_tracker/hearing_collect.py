"""Bounded public HTML hearing collection using the caller's rate-limited GET."""
from datetime import date, timedelta
from hashlib import sha256
from .dashboard_sources import state_schedule, open_slip_form
from .hearings import parse_hearing_details
from .hearing_changes import day, identity
from .http import source_error


def state_meetings(committee, body, listing_proof, previous, as_of, end, fetch, options, work, errors):
    scheduled = state_schedule(body, committee['schedule_url'])
    listed = {m['source_url']: m for m in scheduled}
    old = {m['source_url']: m for m in previous if m.get('committee_url') == committee['url']}
    candidates = {url: row for url, row in listed.items() if not day(row) or as_of.isoformat() <= day(row) <= end.isoformat()}
    cutoff = (as_of - timedelta(days=options['prior_hearing_lookback_days'])).isoformat()
    for url, row in sorted(old.items()):
        if not day(row) or cutoff <= day(row) <= end.isoformat():
            if url in listed:
                # Follow an already tracked ID even when a reschedule moves it
                # beyond the month or into the past; otherwise its old date lingers.
                candidates.setdefault(url, listed[url])
                continue
            if work.setdefault('missing_checks', 0) >= options['max_missing_hearing_rechecks']:
                errors.append({'source': url, 'error': 'hearing-recheck-bound'})
                committee['health'] = 'partial'
                candidates[url] = {**row, '_retain_only': True}
            else:
                work['missing_checks'] += 1
                candidates[url] = row
    rows = []
    for url, listing in sorted(candidates.items()):
        try:
            if listing.get('_retain_only'): raise ValueError('hearing-recheck-bound')
            key = identity({'source_url': url}, 'IL')
            if key.split('-')[-2] != committee['id'] or key.split('-')[2] != committee['chamber'].upper():
                raise ValueError('hearing-committee-mismatch')
            details = work.setdefault('details', {})
            if url not in details:
                if len(details) >= options['max_detail_pages_per_run']: raise ValueError('hearing-detail-bound')
                # Charge the attempt before GET/parse, including failures. A bad
                # page must not evade the bound or be refetched for each member.
                details[url] = None
                raw, proof = fetch(url, 'dashboard-hearing-' + sha256(url.encode()).hexdigest() + '.html')
                if raw.lstrip().startswith(b'%PDF' if isinstance(raw, bytes) else '%PDF'): raise ValueError('Unexpected hearing content')
                parsed = parse_hearing_details(raw, url)
                if len(parsed['items']) > options['max_agenda_items']: raise ValueError('hearing-agenda-bound')
                details[url] = (parsed, proof)
            if details[url] is None: raise ValueError('Earlier detail attempt failed')
            parsed, proof = details[url]
            if url in listed and parsed['date_local'] and listing.get('date_local') and parsed['date_local'] != listing['date_local']:
                # A date-only listing can agree with a detail with explicit time.
                if len(listing['date_local']) != 10 or listing['date_local'] != parsed['date_local'][:10]:
                    raise ValueError('hearing-date-conflict')
            explicit = {s for s in (parsed.get('status'), listed.get(url, {}).get('status')) if s}
            if len(explicit) > 1: raise ValueError('hearing-status-conflict')
            status = next(iter(explicit), 'scheduled' if url in listed else 'unconfirmed')
            row = {**listing, **parsed, 'hearing_key': key, 'committee_name': committee['name'], 'committee_url': committee['url'],
                'timezone': 'America/Chicago', 'timezone_basis': 'jurisdiction assumption',
                'status': status, 'status_basis': 'explicit-notice' if explicit else 'scheduled-listing' if url in listed else 'detail-only',
                'status_notice': parsed.get('status_notice') or listed.get(url, {}).get('status_notice'),
                'listing_present': url in listed, 'evidence': proof, 'listing_evidence': listing_proof,
                'last_known_date_local': old.get(url, {}).get('date_local') if not parsed['date_local'] else None}
            for item in row['items']:
                item['submission_verified'] = False
                slip = item.get('witness_slip_url')
                if not slip or status not in {'scheduled', 'rescheduled'} or url not in listed: continue
                forms = work.setdefault('forms', {})
                if slip not in forms:
                    if len(forms) >= options['max_witness_forms_per_run']:
                        item['submission_status'] = 'verification request bound reached'
                        continue
                    forms[slip] = {'open': False}
                    try:
                        form, form_proof = fetch(slip, 'dashboard-slip-' + sha256(slip.encode()).hexdigest() + '.html')
                        forms[slip] = {'open': open_slip_form(form, slip), 'checked_at': form_proof['checked_at']}
                    except Exception as error:
                        errors.append({'source': 'Witness form verification', 'error': source_error(error)})
                item['submission_verified'] = forms[slip]['open']
                item['submission_checked_at'] = forms[slip].get('checked_at')
            row['outside_display_window'] = not (as_of.isoformat() <= day(row) <= end.isoformat())
            rows.append(row)
        except Exception as error:
            committee['health'] = 'partial'
            code = str(error) if str(error) in {'hearing-recheck-bound','hearing-detail-bound','hearing-agenda-bound','hearing-date-conflict','hearing-status-conflict','hearing-committee-mismatch'} else source_error(error)
            errors.append({'source': url, 'error': code})
            if url in old:
                rows.append({**old[url], 'retained_after_failure': True,
                             'items': [{**i, 'submission_verified': False} for i in old[url].get('items', [])]})
    return sorted(rows, key=lambda m: (day(m), m['source_url']))
