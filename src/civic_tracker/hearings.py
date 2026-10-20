"""Read public ILGA hearing detail tables without calling the range API."""
from datetime import datetime
import re
from urllib.parse import urljoin, urlsplit, parse_qs
from bs4 import BeautifulSoup
from .hearing_changes import explicit_status, text

COLUMNS = ['Bill #', 'Motion', 'Vote Motion', 'Vote Total', 'Vote Result', 'Witness Slip Results']


def official_link(base, value):
    if not value:
        return None
    link = urljoin(base, value)
    parsed = urlsplit(link)
    if parsed.scheme != 'https' or parsed.netloc != 'ilga.gov':
        raise ValueError('Unexpected hearing link host')
    return link


def labeled_field(main, label, required=True):
    values = set()
    for row in main.find_all('tr'):
        cell = row.find('td')
        span = cell.find('span') if cell else None
        if span and span.get_text(' ', strip=True) == label + ':':
            text = cell.get_text(' ', strip=True)
            values.add(text[len(label)+1:].strip())
    if len(values) > 1:
        raise ValueError('Conflicting duplicate hearing field: ' + label)
    if not values:
        if required:
            raise ValueError('Missing hearing field: ' + label)
        return None
    return values.pop()


def local_datetime(raw):
    return datetime.strptime(raw, '%m/%d/%Y %I:%M %p').isoformat(timespec='minutes')


def hearing_date(raw):
    """Preserve date-only/TBA notices; do not invent a midnight meeting."""
    try: return local_datetime(raw), 'minute', None
    except ValueError: pass
    match = re.fullmatch(r'(\d{1,2}/\d{1,2}/\d{4})(?:\s+(.*))?', text(raw))
    if match:
        when = datetime.strptime(match[1], '%m/%d/%Y').date().isoformat()
        note = match[2] or 'Time not supplied'
        if match[2] and not re.search(r'\b(TBA|TBD|to be|upon|adjournment|call of|postponed|cancel)', note, re.I):
            raise ValueError('Unrecognized hearing time')
        return when, 'day', note
    if explicit_status(raw) or re.fullmatch(r'(?:TBA|TBD|To Be (?:Determined|Announced))', text(raw), re.I):
        return None, 'unknown', text(raw)
    raise ValueError('Unrecognized hearing date')


def parse_hearing_details(body, source_url):
    match = re.fullmatch(r'/(House|Senate)/hearings/details/(\d+)/(\d+)/?', urlsplit(source_url).path, re.I)
    if not match:
        raise ValueError('Expected an official hearing detail URL')
    official_link(source_url, source_url)
    soup = BeautifulSoup(body, 'html.parser')
    main = soup.find('main')
    if main is None:
        raise ValueError('Missing hearing main content')
    heading = next((h.get_text(' ', strip=True) for h in main.find_all(['h1','h2'])
                    if 'Hearing Details -' in h.get_text()), None)
    if not heading:
        raise ValueError('Missing hearing title')
    if not re.search(r'\b104(?:th)?\s+General Assembly\b', heading, re.I):
        raise ValueError('Hearing session mismatch')
    raw_date = labeled_field(main, 'Date', required=False)
    raw_posted = labeled_field(main, 'Posting Date', required=False)
    notices = []
    for label in ('Status', 'Hearing Status', 'Notice'):
        value = labeled_field(main, label, required=False)
        if value: notices.append(value)
    # Only dedicated notices/headings, not text in bill rows or site footers.
    notices.extend(node.get_text(' ', strip=True) for node in main.select('.alert,.hearing-status,h1,h2,h3,h4')
                   if node.find_parent('table') is None)
    if explicit_status(raw_date): notices.append(raw_date)
    statuses = {explicit_status(value) for value in notices} - {None}
    if len(statuses) > 1: raise ValueError('Conflicting explicit hearing status')
    status = next(iter(statuses), None)
    status_notice = next((value for value in notices if explicit_status(value) == status), None) if status else None
    if raw_date:
        when, precision, time_note = hearing_date(raw_date)
    elif status in {'canceled', 'postponed'}:
        when, precision, time_note = None, 'unknown', 'No date on the official status notice'
    else:
        raise ValueError('Missing hearing field: Date')
    result = {'source_url': source_url, 'chamber': match[1].title(), 'committee_id': match[2],
              'hearing_id': match[3], 'title': heading, 'raw_date': raw_date,
              'date_local': when, 'time_precision': precision, 'time_note': time_note,
              'status': status, 'status_notice': status_notice, 'status_basis': 'explicit-notice' if status else None,
              'timezone_assumption': 'America/Chicago', 'source_timezone_explicit': False,
              'location': labeled_field(main, 'Location', required=False),
              'raw_posting_date': raw_posted, 'posting_date_local': local_datetime(raw_posted) if raw_posted else None,
              'items': []}
    found_table = False
    by_key = {}
    for table in main.find_all('table'):
        headers = [cell.get_text(' ', strip=True) for cell in table.find_all('th')]
        if not headers:
            continue
        if headers != COLUMNS:
            raise ValueError('Hearing bill columns changed')
        found_table = True
        for row in table.find_all('tr'):
            cells = row.find_all('td', recursive=False)
            if not cells:
                continue
            if len(cells) != len(COLUMNS):
                raise ValueError('Hearing bill row shape changed')
            anchor = cells[0].find('a', href=True)
            if not anchor:
                raise ValueError('Hearing bill permalink missing')
            label = anchor.get_text(' ', strip=True)
            measure = re.fullmatch(r'(HJRCA|SJRCA|HJR|SJR|HB|SB|HR|SR)\s*0*(\d+)(?:\s*\(([^)]+)\))?', label)
            if not measure:
                raise ValueError('Unrecognized hearing bill label')
            bill_url = official_link(source_url, anchor['href'])
            parsed_url = urlsplit(bill_url)
            query = {key.casefold(): values for key, values in parse_qs(parsed_url.query).items()}
            if (parsed_url.path.casefold() != '/legislation/billstatus' or
                query.get('doctypeid') != [measure[1]] or
                len(query.get('docnum', [])) != 1 or not query['docnum'][0].isdigit() or
                int(query['docnum'][0]) != int(measure[2])):
                raise ValueError('Hearing bill label and permalink disagree')
            item = {'bill': measure[1]+str(int(measure[2])), 'amendment': measure[3], 'raw_label': label,
                    'official_url': bill_url,
                    'motion': cells[1].get_text(' ', strip=True),
                    'vote_motion': cells[2].get_text(' ', strip=True),
                    'vote_total_raw': cells[3].get_text(' ', strip=True),
                    'vote_result': cells[4].get_text(' ', strip=True),
                    'witness_results_url': None, 'witness_slip_url': None}
            for link in cells[5].find_all('a', href=True):
                if link.get('title') == 'View Witness Slips':
                    item['witness_results_url'] = official_link(source_url, link['href'])
                if any(part in link['href'].casefold() for part in ('createwitnessslip', '/witnessslip/create')):
                    submission = urljoin(source_url, link['href'])
                    parsed = urlsplit(submission)
                    if parsed.scheme != 'https' or parsed.netloc not in {'ilga.gov', 'my.ilga.gov'}:
                        raise ValueError('Unexpected witness submission host')
                    item['witness_slip_url'] = submission
            # A historical results link is not an available witness-slip submission form.
            key = (item['bill'], item['amendment'], item['motion'])
            if key in by_key and by_key[key] != item:
                raise ValueError('Conflicting duplicate hearing bill')
            by_key[key] = item
    if not found_table and status not in {'canceled', 'postponed'}:
        raise ValueError('No supported hearing bill table; empty coverage is not a parse success')
    result['agenda_coverage'] = 'complete' if found_table else 'not-published'
    result['items'] = list(by_key.values())
    return result
