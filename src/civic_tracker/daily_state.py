"""Bounded Illinois FTP deltas and conditional official floor CSV refresh."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlencode, urlsplit
import xml.etree.ElementTree as ET
from .http import Client, fingerprint
from .vote_csv import read_csv, bill_id, choice

CODES = {'HB':'HB','SB':'SB','HR':'HR','SR':'SR','HJ':'HJR','SJ':'SJR','HC':'HJRCA','SC':'SJRCA','JS':'JSR'}


def listing(body, ga):
    rows = re.findall(r'(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2}\s+[AP]M)\s+(\d+)\s+<A HREF="([^"]+)"', body.decode('utf-8'), re.I)
    result = {}
    for day, clock, size, path in rows:
        match = re.fullmatch(r'/Legislation/'+str(ga)+r'/BillStatus/XML/'+str(ga)+r'00(HB|SB|HR|SR|HJ|SJ|HC|SC|JS)(\d+)\.xml',path,re.I)
        if not match:
            continue
        url = 'https://ftp.ilga.gov'+path
        if url in result:
            raise ValueError('Duplicate FTP identity')
        code, num = match.groups()
        result[url] = {'type':CODES[code.upper()], 'number':int(num), 'token':day+' '+clock+' '+size}
    if len(result) < 100:
        raise ValueError('FTP listing unexpectedly small')
    return result


def source_day(value):
    return datetime.strptime(value.strip(), '%m/%d/%Y').date().isoformat()


def parse_bill(body, meta, members, ga):
    tree = ET.fromstring(body)
    typ, number = meta['type'], meta['number']
    if not re.search(r'\b'+re.escape(typ)+r'\s*0*'+str(number)+r'\b', tree.findtext('title') or '', re.I):
        raise ValueError('XML identity mismatch')
    actions = []; current = {}
    for child in tree.findall('./actions/*'):
        text = ''.join(child.itertext()).strip()
        if child.tag == 'statusdate': current = {'date':source_day(text)}
        elif child.tag == 'chamber': current['chamber'] = text
        elif child.tag == 'action':
            if not current.get('date') or not current.get('chamber'):
                raise ValueError('Incomplete action tuple')
            actions.append({**current,'action':text}); current = {}
    if not actions:
        raise ValueError('Empty official history')
    def matches(text, member):
        return any(re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',text,re.I) for name in member.get('aliases',[member['name']]))
    roles = []
    for action in actions:
        raw = action['action']
        for member in members:
            if not matches(raw,member) or not re.search(r'Filed with|Sponsor',raw,re.I):continue
            role = ('original-filer' if re.search(r'Filed with',raw,re.I) else 'chief-co-sponsor' if re.search(r'Chief Co-Sponsor',raw,re.I)
                    else 'chief-sponsor' if re.search(r'Chief.*Sponsor',raw,re.I) else 'co-sponsor' if re.search(r'Co-Sponsor',raw,re.I) else 'sponsor')
            roles.append({**action,'member_id':member['official_member_id'],'role':role,
                          'operation':'removed' if re.search(r'Remov',raw,re.I) else 'filed' if role=='original-filer' else 'added-or-changed'})
    sponsors = [''.join(el.itertext()).strip() for el in tree.findall('./sponsor/*') if el.tag in ('sponsors','altsponsors')]
    targets = [m['official_member_id'] for m in members if any(matches(s,m) for s in sponsors)]
    first = next((a for a in actions if re.match(r'(?:Pre)?filed with (?:the )?(?:Clerk|Secretary) by ',a['action'],re.I)),None)
    last = tree.find('lastaction'); last_action = {}
    if last is not None and last.findtext('statusdate'):
        last_action = {'date':source_day(last.findtext('statusdate')),'chamber':last.findtext('chamber'),'action':last.findtext('action')}
    # The XML's title is not an invented legislative ID. Reuse the known
    # permalink when available; otherwise ILGA resolves type/number/session.
    url = meta.get('source_url') or 'https://ilga.gov/Legislation/BillStatus?'+urlencode({'DocNum':number,'GAID':meta['ga_id'],'DocTypeID':typ,'SessionID':meta['session_id']})
    return {'record_id':f'IL-{ga}-{typ}{number}','title':tree.findtext('shortdesc') or tree.findtext('title'),
            'type':typ,'number':number,'source_url':url,'role_events':roles,'current_target_sponsors':targets,
            'original_filing':first,'displayed_last_action':last_action}


def refresh(root, previous, state, now):
    archive = deepcopy(previous); state = deepcopy(state)
    config = json.loads((root/'config/project.json').read_text(encoding='utf-8'))
    ga = config['ga']; checked = now.isoformat(); client = Client(config,root/'.local')
    report = {'checked_at':checked,'status':'ok','errors':[],'limitations':['Committee votes retain historical PDF coverage; daily committee-vote discovery is pending.']}
    def error(source, ex):
        report['errors'].append({'source':source,'error':type(ex).__name__})
    base = f'https://ftp.ilga.gov/Legislation/{ga}/BillStatus/XML/'
    try:
        response = client.get(base); current = listing(response['body'],ga)
        report['listing'] = fingerprint(response)
        previous_tokens = state.setdefault('ftp_tokens',{})
        changed = sorted(url for url,meta in current.items() if previous_tokens.get(url)!=meta['token'])
        report['changed_files'] = len(changed); report['processed_files'] = 0
        # Do not advance failed/unprocessed entries; the next day retries them.
        for url in changed[:300]:
            try:
                response = client.get(url); meta = current[url]
                ident = f'IL-{ga}-{meta["type"]}{meta["number"]}'
                old = archive['bills'].get(ident,{})
                bill = parse_bill(response['body'],{**meta,'source_url':old.get('source_url'),'ga_id':config['ga_id'],'session_id':config['session_id']},config['subjects'],ga)
                bill['evidence'] = {**fingerprint(response),'retrieved_at':checked}
                if old or bill['role_events'] or bill['current_target_sponsors']:
                    archive['bills'][ident] = bill
                previous_tokens[url] = meta['token']; report['processed_files'] += 1
            except Exception as ex:error(url,ex)
        if len(changed)>300:
            report['errors'].append({'source':'Illinois FTP','error':'daily-file-bound-pending'})
    except Exception as ex:error(base,ex)
    csv_url = f'https://ilga.gov/documents/reports/static/{ga}MemberVotes.csv'
    csv_state = state.setdefault('floor_csv',{})
    headers = {}
    if csv_state.get('etag'):headers['If-None-Match']=csv_state['etag']
    if csv_state.get('last_modified'):headers['If-Modified-Since']=csv_state['last_modified']
    try:
        response = client.get(csv_url,headers=headers)
        report['floor_csv'] = fingerprint(response)
        if response['status']==200:
            scratch = root/'.local/daily-floor.csv'; scratch.write_bytes(response['body'])
            parsed = read_csv(scratch)
            if not parsed['subjects'] or parsed['row_count'] < 1000:
                raise ValueError('Incomplete floor CSV')
            latest = datetime.fromisoformat(parsed['latest_vote_date']).date().isoformat()
            if latest < csv_state.get('latest_vote_date',latest):
                raise ValueError('Regressed floor CSV date')
            for row in parsed['subjects']:
                if row['GA'] != str(ga) or row['Chamber'] not in ('House','Senate'):
                    raise ValueError('CSV session identity mismatch')
                datetime.fromisoformat(row['Vote Date'])
            # Existing PDF baseline remains intact. Initial old CSV rows are
            # history, not newly discovered activity. Recheck a seven-day overlap
            # around the last successful CSV watermark for corrections.
            baseline = json.loads((root/'config/daily.json').read_text(encoding='utf-8'))['floor_csv_baseline_through']
            watermark = csv_state.get('latest_vote_date',baseline)
            cutoff = (datetime.fromisoformat(watermark)-timedelta(days=7)).date().isoformat()
            fresh_votes = {}
            for row in parsed['subjects']:
                if row['Vote Date']<=cutoff:continue
                key = hashlib.sha256(json.dumps(row['roll']).encode()).hexdigest()[:24]
                ident = f'IL-{ga}-CSV-{key}'
                measure = f'IL-{ga}-'+bill_id(row['Legislation'])
                value = {'record_id':ident,'measure_id':measure,'date':row['Vote Date'],'chamber':row['Chamber'],
                         'scope':'floor','verification':'official-csv','motion_context':row['Vote Type'],'label':row['Legislation'],
                         'source_url':csv_url,'choices':[],'totals':{'no':row['nay_count']},
                         'evidence':{'retrieved_at':checked,'sha256':report['floor_csv']['sha256']}}
                # Never replace a PDF reconciled record with an approximate CSV
                # join. Separate dated-source records keep known conflicts visible.
                if row['Vote Date']<=baseline:continue
                member = next(m for m in config['subjects'] if m['id']==row['subject'])
                if ident not in fresh_votes:fresh_votes[ident]=value
                choices = fresh_votes[ident]['choices']
                if any(c['member_id']==member['official_member_id'] for c in choices):
                    raise ValueError('Duplicate member in CSV roll identity')
                choices.append({'member_id':member['official_member_id'],'choice':choice(row['Vote']),'raw':row['Vote']})
            superseded=state.setdefault('csv_superseded',{})
            for ident, old in list(archive['votes'].items()):
                if old.get('verification')=='official-csv' and old['date']>cutoff:
                    fresh=fresh_votes.get(ident)
                    fields=('date','motion_context','choices','totals')
                    if fresh is None or any(old.get(k)!=fresh.get(k) for k in fields):
                        revision=hashlib.sha256(json.dumps(old,sort_keys=True).encode()).hexdigest()
                        superseded[revision]=old
                    if fresh is None:del archive['votes'][ident]
            archive['votes'].update(fresh_votes)
            h={k.casefold():v for k,v in response['headers'].items()}
            csv_state.update(latest_vote_date=parsed['latest_vote_date'],etag=h.get('etag'),last_modified=h.get('last-modified'),checked_at=checked)
            report['floor_latest_vote_date']=parsed['latest_vote_date']
        elif not csv_state.get('latest_vote_date'):
            raise ValueError('304 without prior CSV baseline')
        else:csv_state['checked_at']=checked
    except Exception as ex:error(csv_url,ex)
    report['status']='partial' if report['errors'] else 'ok'
    # Per-source metadata is authoritative; one aggregate timestamp cannot
    # turn failed collection or historical committee votes into fresh coverage.
    if not report['errors']:archive['collected_at']=checked
    return archive,state,report
