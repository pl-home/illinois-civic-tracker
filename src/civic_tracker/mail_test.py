"""One owner-only M0 SMTP test. Reservation prevents an automatic duplicate send."""
from pathlib import Path
from datetime import datetime,timezone
from email.message import EmailMessage
from email.headerregistry import Address
import argparse,imaplib,json,os,smtplib,ssl,time,uuid


def now():return datetime.now(timezone.utc).isoformat()


def app_password(value):
    # Google displays the app passcode in groups; whitespace is presentation only.
    return ''.join(value.split())


def self_address_pair(sender,recipient):
    # Accept only bare Gmail addresses for the same mailbox, with a recipient + tag.
    # Return booleans/errors without reflecting private values into output.
    try:
        a=Address(addr_spec=sender);b=Address(addr_spec=recipient)
    except Exception:raise ValueError('Invalid address configuration') from None
    if any(c in sender+recipient for c in '\r\n') or str(a)!=sender or str(b)!=recipient:
        raise ValueError('Expected bare addresses')
    domains={'gmail.com','googlemail.com'}
    base=lambda name:name.split('+',1)[0].replace('.','').casefold()
    if a.domain.casefold() not in domains or b.domain.casefold() not in domains or not a.username or '+' not in b.username or not b.username.split('+',1)[1] or base(a.username)!=base(b.username):
        raise ValueError('M0 recipient must be a plus alias of the sender Gmail mailbox')


def inbox_contains(sender,password,message_id):
    # Read-only INBOX search for this exact test. No other message bodies are read.
    with imaplib.IMAP4_SSL('imap.gmail.com',ssl_context=ssl.create_default_context(),timeout=30) as inbox:
        inbox.login(sender,password)
        status,_=inbox.select('INBOX',readonly=True)
        if status!='OK':raise RuntimeError('INBOX unavailable')
        for attempt in range(6):
            status,data=inbox.search(None,'HEADER','Message-ID',message_id)
            if status=='OK' and any(value.strip() for value in data if value):return True
            if attempt<5:time.sleep(5)
    return False


def write(path,report):path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')


def reserve(path,after_credential_update=False):
    previous=None
    if path.exists():
        if not after_credential_update:
            print('M0 mail reservation exists; no additional send authorized by this workflow.');return 1
        previous=json.loads(path.read_text())
        diagnostics=path.with_name('m0-mail-diagnostics.json')
        check=json.loads(diagnostics.read_text()) if diagnostics.exists() else {}
        authenticated=any(item.get('smtp_authentication_code')==235 for item in check.get('connections',[]))
        if previous.get('status') not in {'failed-or-uncertain','failed-before-submission'} or previous.get('submission_started',False) or previous.get('smtp_submitted') or previous.get('inbox_confirmed') or not authenticated or check.get('exact_test_found_in_inbox') is not False or check.get('observed_at','')<=previous.get('finished_at',''):
            print('Credential-correction retry gate not satisfied.');return 1
        history_path=path.with_name('m0-mail-attempts.json')
        history=json.loads(history_path.read_text()) if history_path.exists() else []
        if not any(item['test_id']==previous['test_id'] for item in history):history.append(previous)
        write(history_path,history)
    report={'test_id':str(uuid.uuid4()),'reserved_at':now(),'status':'reserved','smtp_submitted':False,'inbox_confirmed':False,'submission_started':False}
    if previous is not None:report['retry_of']=previous['test_id'];report['retry_reason']='operator-confirmed credential correction; no prior submission acknowledged; exact test absent from INBOX'
    path.parent.mkdir(parents=True,exist_ok=True);write(path,report)
    print('Reserved one owner-only M0 test.');return 0


def send(path):
    if not path.exists():print('M0 mail reservation missing.');return 1
    report=json.loads(path.read_text())
    if report['status']!='reserved':print('M0 test already attempted; no duplicate send.');return 1
    # The reservation must already be committed and pushed by the workflow. A process
    # crash leaves it reserved; rerunning the workflow stops at reserve, not at send.
    try:
        values=[os.environ.get(key,'') for key in ['GMAIL_USER','GMAIL_APP_PASSWORD','DIGEST_TO']]
        if not all(values):raise ValueError('Missing required secrets')
        sender,password,recipient=values;password=app_password(password);self_address_pair(sender,recipient)
        message=EmailMessage();message['From']=sender;message['To']=recipient
        message['Subject']='Illinois civic tracker: one-time M0 delivery test'
        message_id='<'+report['test_id']+chr(64)+'illinois-civic-tracker.invalid>'
        message['Message-ID']=message_id
        message.set_content('One-time owner-only delivery verification for the Illinois civic tracker. No weekly digest schedule is enabled.\nProject: https://github.com/pl-home/illinois-civic-tracker\n')
        message.add_alternative('<p>One-time owner-only delivery verification for the Illinois civic tracker. No weekly digest schedule is enabled.</p><p><a href="https://github.com/pl-home/illinois-civic-tracker">Project</a></p>',subtype='html')
        report['attempted_at']=now();report['status']='attempting';report['stage']='connect';write(path,report)
        with smtplib.SMTP('smtp.gmail.com',587,timeout=30) as smtp:
            report['stage']='tls';write(path,report)
            smtp.ehlo();smtp.starttls(context=ssl.create_default_context());smtp.ehlo()
            report['stage']='authentication';write(path,report);smtp.login(sender,password)
            report['stage']='submission';report['submission_started']=True;write(path,report);smtp.send_message(message)
            # Record acceptance before QUIT: a disconnect during QUIT does not undo it.
            report['smtp_submitted']=True;report['status']='submitted';report['stage']='accepted';write(path,report)
        report['inbox_confirmed']=inbox_contains(sender,password,message_id)
        report['status']='inbox-confirmed' if report['inbox_confirmed'] else 'submitted-inbox-unconfirmed'
    except Exception as error:
        # SMTP/IMAP exceptions can contain addresses; never print their text or traceback.
        report['status']='submitted-inbox-unconfirmed' if report['smtp_submitted'] else 'failed-or-uncertain'
        report['error_type']=type(error).__name__
    report['finished_at']=now();write(path,report)
    print(json.dumps({key:report[key] for key in ['status','smtp_submitted','inbox_confirmed']}))
    return 0 if report['inbox_confirmed'] else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['reserve','send']);parser.add_argument('--after-credential-update',action='store_true');args=parser.parse_args()
    path=Path('docs/evidence/m0-mail-delivery.json')
    return reserve(path,args.after_credential_update) if args.action=='reserve' else send(path)

if __name__=='__main__':raise SystemExit(main())
