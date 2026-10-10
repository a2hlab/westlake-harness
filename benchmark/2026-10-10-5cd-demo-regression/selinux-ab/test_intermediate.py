"""Known answers for ten-record, finished-only intermediate reporting."""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import intermediate
class IntermediateTests(unittest.TestCase):
 def record(self,root,key,finish):
  p=root/'permissive-0-t10'/'run'/'serial'/key;p.mkdir(parents=True)
  (p/'record.json').write_text(json.dumps({'key':key,'finished_at':finish}))
  (p/'t10.jpeg').write_bytes(b'fixture')
  return p/'record.json'
 def test_nine_finished_no_report(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/'run'
   for i in range(9):self.record(root,str(i),str(i))
   self.record(root,'inflight',None)
   with patch.object(intermediate.subprocess,'run') as call:
    self.assertFalse(intermediate.publish(root,Path(t)/'out'));call.assert_not_called()
 def test_first_ten_by_finish_time(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/'run';out=Path(t)/'out'
   for i in range(11):self.record(root,f'key-{i:02}',f'{10-i:02}')
   def analyze(p):
    v=json.loads(p.read_text());return dict(v,key=v['key'],cantopen_log_lines=2,target_cantopen_log_lines=1,wms_already_existed_log_lines=3,target_wms_already_existed_log_lines=1,last_shot={'scheduled_seconds':10})
   with patch.object(intermediate.r,'analyze',analyze),patch.object(intermediate.subprocess,'check_output',return_value='FACTS fixture\n'),patch.object(intermediate.subprocess,'run'):
    self.assertTrue(intermediate.publish(root,out))
   rows=json.loads((out/'counts.json').read_text());self.assertEqual(len(rows),10)
   self.assertEqual(rows[0]['key'],'key-10');self.assertEqual(rows[-1]['key'],'key-01')
   self.assertFalse((out/'run'/intermediate.r.SERIAL/'key-00').exists())
if __name__=='__main__':unittest.main()
