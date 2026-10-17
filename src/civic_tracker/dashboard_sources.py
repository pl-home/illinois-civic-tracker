"""Public committee-calendar parsers. Empty success requires a recognized shape."""
from datetime import datetime, date
import re
from urllib.parse import urljoin, urlsplit
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup


def state_committees(body, source_url):
    soup = BeautifulSoup(body, 'html.parser')
    pane = soup.find(id='pane-Committees')
    if pane is None:
        raise ValueError('Member committee pane missing')
    chamber = 'House' if '/House/' in source_url else 'Senate'
    result = {}
    for anchor in pane.find_all('a', href=True):
        target = urljoin(source_url, anchor['href'])
        match = re.fullmatch(r'/(House|Senate)/Committees/Members/(\d+)', urlsplit(target).path)
        if match:
            if match[1] != chamber or urlsplit(target).netloc != 'ilga.gov':
                raise ValueError('Unexpected committee identity')
            result[match[2]] = {'id': match[2], 'name': anchor.get_text(' ', strip=True),
                'url': target, 'schedule_url': f'https://ilga.gov/{chamber}/Committees/Hearings/{match[2]}',
                'jurisdiction': 'IL', 'chamber': chamber}
    if not result:
        raise ValueError('Member committee links missing')
    return list(result.values())


def state_committee_role(body, source_url, member_id):
    """Read only this member's explicit roster role, never another member's title."""
    soup = BeautifulSoup(body, 'html.parser')
    roles = set()
    expected = f'/Members/Details/{member_id}'
    for anchor in soup.find_all('a', href=True):
        if not urlsplit(urljoin(source_url, anchor['href'])).path.endswith(expected):
            continue
        overlay = anchor.find_parent(class_='member-overlay')
        if overlay is not None:
            paragraph = overlay.find('p', class_='card-text')
            if paragraph is not None:
                lines = list(paragraph.stripped_strings)
                if lines:
                    roles.add(lines[0])
        row = anchor.find_parent('tr')
        if row is not None:
            label = next((span for span in row.find_all('span') if span.get_text(strip=True) == 'Role:'), None)
            if label is not None:
                parts = []
                for sibling in label.next_siblings:
                    if getattr(sibling, 'name', None) == 'br':
                        break
                    parts.append(sibling.get_text(' ', strip=True) if hasattr(sibling, 'get_text') else str(sibling))
                raw = ' '.join(' '.join(parts).split())
                if raw:
                    roles.add(raw)
    if len(roles) != 1:
        raise ValueError('Missing or conflicting member committee role')
    role = roles.pop()
    if len(role) > 80 or not re.fullmatch(r"[A-Za-z /&().,-]+", role):
        raise ValueError('Unrecognized member committee role')
    return {'role': role, 'role_source_url': source_url}


def state_schedule(body, source_url):
    soup = BeautifulSoup(body, 'html.parser')
    scheduled = soup.find(id='scheduled')
    if scheduled is None:
        raise ValueError('Scheduled hearing pane missing')
    found = {}
    for anchor in scheduled.find_all('a', href=True):
        target = urljoin(source_url, anchor['href'])
        if not re.fullmatch(r'/(House|Senate)/hearings/details/\d+/\d+', urlsplit(target).path, re.I):
            continue
        if urlsplit(target).netloc != 'ilga.gov':
            raise ValueError('Unexpected hearing host')
        row = anchor.find_parent('tr')
        if row is None:
            raise ValueError('Hearing row missing')
        match = re.search(r'\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}\s+[AP]M', row.get_text(' ', strip=True))
        if not match:
            raise ValueError('Hearing date missing')
        value = {'date_local': datetime.strptime(match[0], '%m/%d/%Y %I:%M %p').isoformat(timespec='minutes'),
                 'source_url': target, 'timezone': 'America/Chicago', 'timezone_basis': 'jurisdiction assumption',
                 'raw_date': match[0]}
        if target in found and found[target] != value:
            raise ValueError('Conflicting hearing dates')
        found[target] = value
    if not found and 'No Hearings Scheduled at this time.' not in scheduled.get_text(' ', strip=True):
        raise ValueError('Unrecognized empty hearing pane')
    return list(found.values())


def senate_schedule(body):
    root = ET.fromstring(body)
    if root.tag != 'css_meetings_scheduled':
        raise ValueError('Senate calendar shape changed')
    events = []
    for meeting in root.findall('meeting'):
        fields = {child.tag: (child.text or '').strip() for child in meeting}
        when = date.fromisoformat(fields['date_iso_8601'])
        if fields.get('matter') == 'No committee hearings scheduled' and not fields.get('committee'):
            continue
        if not fields.get('committee') or not fields.get('cmte_code'):
            raise ValueError('Senate committee identity missing')
        events.append({'committee_name': fields['committee'], 'committee_code': fields['cmte_code'],
            'date_local': when.isoformat() + 'T' + fields['time'], 'location': fields.get('room', ''),
            'description': fields.get('matter', ''), 'timezone': 'America/New_York',
            'timezone_basis': 'jurisdiction assumption', 'source_url': 'https://www.senate.gov/general/committee_schedules/hearings.xml'})
    if not root.findall('meeting'):
        raise ValueError('Senate calendar unexpectedly empty')
    return events


def house_schedule(body, source_url, expected_start):
    soup = BeautifulSoup(body, 'html.parser')
    # Date headings in calendar cells establish which week the server returned.
    dates = {}
    for anchor in soup.find_all('a', title=True):
        match = re.search(r'ByDay\.aspx\?DayID=(\d{8})', anchor.get('href', ''))
        if match:
            dates[anchor['id']] = datetime.strptime(match[1], '%m%d%Y').date()
    if len(set(dates.values())) != 7 or min(dates.values()) != expected_start:
        raise ValueError('House calendar did not return the requested week')
    events = {}
    for anchor in soup.find_all('a', href=True):
        if not re.fullmatch(r'ByEvent\.aspx\?EventID=\d+', anchor['href'], re.I):
            continue
        cell = anchor.find_parent('td')
        heading = next((a for a in cell.find_all('a', id=True) if a['id'] in dates), None) if cell else None
        paragraph = anchor.find_parent('p')
        name = paragraph.find('b') if paragraph else None
        raw = paragraph.get_text(' ', strip=True) if paragraph else ''
        clock = re.search(r'\d{1,2}:\d{2}\s*[AP]M', raw)
        if heading is None or name is None or clock is None:
            raise ValueError('House meeting row changed')
        day = dates[heading['id']]
        when = datetime.combine(day, datetime.strptime(clock[0], '%I:%M %p').time())
        url = urljoin(source_url, anchor['href'])
        events[url] = {'committee_name': name.get_text(' ', strip=True), 'date_local': when.isoformat(timespec='minutes'),
            'source_url': url, 'timezone': 'America/New_York', 'timezone_basis': 'jurisdiction assumption',
            'description': 'Committee meeting; see official meeting details.'}
    return list(events.values())


def open_slip_form(body, source_url):
    """Conservative read-only verification of an explicitly published create form."""
    parsed = urlsplit(source_url)
    if parsed.scheme != 'https' or parsed.netloc not in {'ilga.gov', 'my.ilga.gov'}:
        return False
    soup = BeautifulSoup(body, 'html.parser')
    text = soup.get_text(' ', strip=True).casefold()
    if any(marker in text for marker in ('submissions closed', 'submission closed', 'not accepting witness slips',
                                        'no longer accepting', 'deadline has passed', 'hearing has concluded',
                                        'sign in to continue', 'log in to continue')):
        return False
    for form in soup.find_all('form'):
        action = urljoin(source_url, form.get('action') or source_url)
        destination = urlsplit(action)
        if destination.scheme != 'https' or destination.netloc != parsed.netloc:
            continue
        if not any(marker in destination.path.casefold() for marker in ('createwitnessslip', '/witnessslip/create')):
            continue
        fields = ' '.join(str(control.get('name', '')) for control in form.find_all(['input', 'select', 'textarea'])).casefold()
        required = ('firstname', 'lastname', 'email', 'position', 'representation')
        submit = [control for control in form.find_all(['input', 'button'])
                  if control.get('type', 'submit' if control.name == 'button' else 'text').casefold() == 'submit' and not control.has_attr('disabled')]
        if all(field in re.sub(r'[^a-z]', '', fields) for field in required) and submit:
            return True
    return False
