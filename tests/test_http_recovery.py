from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from civic_tracker.http import Client, source_error


class RecoveryTests(unittest.TestCase):
    def attempt(self, codes, retry_after=None):
        current=[100.0]; opener=MagicMock(); response=MagicMock()
        response.status=200;response.headers={};response.read.return_value=b'ok'
        def opening(*args,**kwargs):
            code=codes.pop(0)
            if code!=200:raise HTTPError('https://ilga.gov/public',code,'private transport text',{'Retry-After':retry_after} if retry_after else {},None)
            result=MagicMock();result.__enter__.return_value=response;return result
        opener.open.side_effect=opening
        with tempfile.TemporaryDirectory() as tmp,patch('civic_tracker.http.time.time',side_effect=lambda:current[0]),patch('civic_tracker.http.time.sleep',side_effect=lambda n:current.__setitem__(0,current[0]+n)),patch('civic_tracker.http.build_opener',return_value=opener):
            client=Client({'main_site_min_interval_seconds':10,'user_agent':'Public project','max_source_bytes':1000},Path(tmp))
            try:result=client.get('https://ilga.gov/public');error=None
            except Exception as ex:result=None;error=source_error(ex)
        return result,error,client.events

    def test_transient_retries_use_rate_gate_and_record_attempts(self):
        result,error,events=self.attempt([503,502,200])
        self.assertIsNone(error);self.assertEqual(result['request_attempts'],3)
        self.assertEqual([e['status'] for e in events],[503,502,200])
        self.assertTrue(all(b['started_epoch']-a['started_epoch']>=10 for a,b in zip(events,events[1:])))

    def test_permanent_errors_and_long_retry_after_do_not_loop(self):
        for codes,after in [([403],None),([404],None),([429],'120')]:
            _,error,events=self.attempt(codes,after)
            self.assertTrue(error.startswith('HTTP_'));self.assertEqual(len(events),1)

    def test_exhaustion_preserves_status_without_transport_text(self):
        _,error,events=self.attempt([503,503,503])
        self.assertEqual(error,'HTTP_503');self.assertEqual(len(events),3)


if __name__=='__main__':unittest.main()
