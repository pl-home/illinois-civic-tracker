"""M0 mail diagnostics: no SMTP login or send; exact-message INBOX search only."""
from pathlib import Path
from datetime import datetime,timezone
import json,os,smtplib,ssl
from .mail_test import inbox_contains


def main():
    root=Path.cwd();report={'observed_at':datetime.now(timezone.utc).isoformat(),'smtp_messages_sent':0,'connections':[]}
    for port in [587,465]:
        stage='connect';result={'host':'smtp.gmail.com','port':port}
        try:
            factory=smtplib.SMTP if port==587 else smtplib.SMTP_SSL
            options={'timeout':20}
            if port==465:options['context']=ssl.create_default_context()
            with factory('smtp.gmail.com',port,**options) as smtp:
                stage='ehlo';code,_=smtp.ehlo();result['ehlo_code']=code
                if port==587:stage='starttls';smtp.starttls(context=ssl.create_default_context())
                result['verified_tls']=True;stage='quit'
            result['status']='connected-no-authentication-no-send'
        except Exception as error:
            result.update({'status':'failed','stage':stage,'error_type':type(error).__name__})
            if isinstance(error,smtplib.SMTPResponseException):result['smtp_code']=error.smtp_code
        report['connections'].append(result)
    receipt=root/'docs/evidence/m0-mail-delivery.json'
    if receipt.exists():
        test=json.loads(receipt.read_text());message_id='<'+test['test_id']+chr(64)+'illinois-civic-tracker.invalid>'
        try:
            sender=os.environ.get('GMAIL_USER','');password=os.environ.get('GMAIL_APP_PASSWORD','')
            if not sender or not password:raise ValueError('Missing secrets')
            report['exact_test_found_in_inbox']=inbox_contains(sender,password,message_id)
        except Exception as error:report['inbox_error_type']=type(error).__name__
    destination=root/'docs/evidence/m0-mail-diagnostics.json';destination.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))

if __name__=='__main__':main()
