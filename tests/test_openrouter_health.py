import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock,patch
from civic_tracker import openrouter_health as health
from civic_tracker.daily import load


class HealthTests(unittest.TestCase):
    def test_read_only_health_never_records_private_key_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'data').mkdir()
            responses=[]
            for data in [{'label':'private label','hash':'private hash','usage':12}, {'endpoints':[{
                'tag':'deepinfra/fp8','status':-2,'supported_parameters':['response_format']}]}]:
                response=MagicMock();response.read.return_value=json.dumps({'data':data}).encode();responses.append(response)
            opener=MagicMock();opener.open.side_effect=[MagicMock(__enter__=MagicMock(return_value=r)) for r in responses]
            with patch.dict('os.environ',{'OPENROUTER_API_KEY':'private secret'}),patch.object(health,'build_opener',return_value=opener):
                health.check(root)
            report=load(root/'data/openrouter-health.json')
            self.assertEqual(report['model_calls'],0)
            self.assertEqual(report['authentication'],{'status':'ok'})
            self.assertNotIn('private',json.dumps(report))
            requests=[c.args[0] for c in opener.open.call_args_list]
            self.assertTrue(all(r.get_method()=='GET' for r in requests))
            self.assertFalse(requests[1].has_header('Authorization'))
