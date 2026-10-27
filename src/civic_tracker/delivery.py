"""Bounded owner-only digest delivery with durable reservation before SMTP.

The public digest remains preview-only. This module is the separate, explicitly
scheduled owner delivery path. It never addresses legislators, parties or
campaigns and never writes credential values to state or logs.
"""
import argparse, json, os, smtplib, ssl, uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from . import digest
from .changes import packed, read, timestamp
from .mail_test import app_password, inbox_contains, self_address_pair

STATE = Path('data/digest-delivery.json')


def now():
    return datetime.now(timezone.utc).isoformat()


def config(root):
    value = read(root / 'config/digest-delivery.json', {})
    if value.get('schema_version') != 1 or value.get('enabled') is not True:
        raise ValueError('digest-delivery-disabled')
    if value.get('timezone') != 'America/Chicago' or value.get('interval_days') != 3:
        raise ValueError('digest-delivery-cadence-bound')
    if not 1 <= value.get('max_attempts', 0) <= 24:
        raise ValueError('digest-delivery-attempt-bound')
    return value


def load(root):
    value = read(root / STATE, {'schema_version': 1, 'last_sent_at': None, 'attempts': []})
    if value.get('schema_version') != 1 or not isinstance(value.get('attempts'), list):
        raise ValueError('digest-delivery-state-invalid')
    return value


def save(root, value):
    value = dict(value, schema_version=1, attempts=value.get('attempts', [])[-24:])
    raw = packed(value) + '\n'
    if len(raw.encode()) > 96000:
        raise ValueError('digest-delivery-state-bound')
    path = root / STATE; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(raw, encoding='utf-8', newline='\n')


def due(state, at, interval_days=3):
    if state.get('last_sent_at') is None:
        return True
    try:
        return (timestamp(at) - timestamp(state['last_sent_at'])).total_seconds() >= interval_days * 86400
    except (TypeError, ValueError):
        raise ValueError('digest-delivery-last-sent-invalid')


def current_preview(root):
    data = digest.preview(root)
    html = digest.render_html(data).replace(
        '<strong>Email delivery disabled.</strong> Review only. No message was sent.',
        '<strong>Scheduled owner digest.</strong> No public recipient or outreach.')
    text = digest.render_text(data).replace(
        'EMAIL DELIVERY DISABLED — review only; no message was sent.',
        'SCHEDULED OWNER DIGEST — owner-only delivery; no outreach was sent.')
    return data, html, text


def reserve(root, at=None):
    at = at or now(); cfg = config(root); state = load(root)
    previous = state.get('attempts', [])[-1] if state.get('attempts') else None
    if previous and previous.get('status') in {'reserved', 'submitting', 'uncertain', 'submitted-inbox-unconfirmed'}:
        print(json.dumps({'status': 'blocked-pending-attempt'})); return 1
    if not due(state, at, cfg['interval_days']):
        print(json.dumps({'status': 'not-due'})); return 2
    data, _, _ = current_preview(root)
    attempt = {'attempt_id': str(uuid.uuid4()), 'status': 'reserved', 'reserved_at': at,
               'preview_id': data['preview_id'], 'input_sha256': data['input_sha256'],
               'period': data['period']}
    state['attempts'] = state.get('attempts', []) + [attempt]
    save(root, state)
    print(json.dumps({'status': 'reserved', 'preview_id': data['preview_id']})); return 0


def send(root):
    cfg = config(root); state = load(root)
    if not state.get('attempts') or state['attempts'][-1].get('status') != 'reserved':
        print(json.dumps({'status': 'not-sendable'})); return 1
    attempt = state['attempts'][-1]; data, html, text = current_preview(root)
    if data['preview_id'] != attempt['preview_id'] or data['input_sha256'] != attempt['input_sha256']:
        attempt['status'] = 'rejected'; attempt['error_code'] = 'preview-changed-after-reservation'; save(root, state)
        print(json.dumps({'status': 'rejected'})); return 1
    values = [os.environ.get(cfg[name], '') for name in ('sender_secret', 'password_secret', 'recipient_secret')]
    if not all(values):
        attempt['status'] = 'rejected'; attempt['error_code'] = 'missing-secret'; save(root, state)
        print(json.dumps({'status': 'rejected'})); return 1
    sender, password, recipient = values; password = app_password(password)
    try:
        self_address_pair(sender, recipient)
    except ValueError:
        attempt['status'] = 'rejected'; attempt['error_code'] = 'invalid-owner-address'; save(root, state)
        print(json.dumps({'status': 'rejected'})); return 1
    message = EmailMessage(); message['From'] = sender; message['To'] = recipient
    message['Subject'] = 'Illinois civic tracker · owner digest'
    message['Message-ID'] = '<' + attempt['attempt_id'] + chr(64) + 'illinois-civic-tracker.invalid>'
    message.set_content(text); message.add_alternative(html, subtype='html')
    attempt['status'] = 'submitting'; attempt['submission_started'] = True; attempt['started_at'] = now(); save(root, state)
    try:
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=30) as smtp:
            smtp.ehlo(); smtp.starttls(context=ssl.create_default_context()); smtp.ehlo(); smtp.login(sender, password)
            smtp.send_message(message)
        attempt['smtp_submitted'] = True
        attempt['status'] = 'sent' if inbox_contains(sender, password, message['Message-ID']) else 'submitted-inbox-unconfirmed'
        attempt['finished_at'] = now()
        if attempt['status'] == 'sent': state['last_sent_at'] = attempt['finished_at']
    except Exception as error:
        attempt['status'] = 'submitted-inbox-unconfirmed' if attempt.get('smtp_submitted') else 'uncertain'
        attempt['error_type'] = type(error).__name__; attempt['finished_at'] = now()
    save(root, state)
    print(json.dumps({'status': attempt['status'], 'smtp_submitted': bool(attempt.get('smtp_submitted'))})); return 0 if attempt['status'] == 'sent' else 1


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['reserve', 'send']); args = parser.parse_args()
    root = Path.cwd(); return reserve(root) if args.action == 'reserve' else send(root)


if __name__ == '__main__':
    raise SystemExit(main())
