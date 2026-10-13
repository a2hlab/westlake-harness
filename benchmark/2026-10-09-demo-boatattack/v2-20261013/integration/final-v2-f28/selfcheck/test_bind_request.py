import contextlib,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import bind_request as b
c=b.c;HERE=Path(__file__).resolve().parent
class BindingTests(unittest.TestCase):
 def invoke(self,extra=(),serial='5cd1e3dd00000000000000000923012c'):
  td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);root=Path(td.name)
  plan=root/'plan.json';plan.write_text(json.dumps(dict(serial=serial,boat_uid=20011301,synthetic=False)))
  out=root/'request.json';argv=['bind','--template',str(HERE/'request.5cd.pending.json'),'--plan',str(plan),'--out',str(out),*extra]
  with patch.object(sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()):b.main()
  return c.read(out)
 def test_same_landing_sibling_pins(self):
  q=self.invoke();self.assertEqual(c.pin(q['provider_freeze'],HERE),HERE.parent/'board5cd/provider-freeze.json')
  self.assertEqual(set(q['programs']),{'executor','contract','identity'})
  for ref in q['programs'].values():self.assertEqual(c.pin(ref,HERE).parent,HERE.parent/'board5cd/provider')
  self.assertFalse(q['execution_enabled']);self.assertIsNone(q['signed_by'])
 def test_unpaired_current_source_rejected(self):
  with self.assertRaisesRegex(ValueError,'paired'):self.invoke(['--base-selfcheck',str(HERE/'source-pins.json')])
 def test_wrong_board_rejected(self):
  with self.assertRaisesRegex(ValueError,'serial'):self.invoke(serial='61b0657200000000000000000324012c')
if __name__=='__main__':unittest.main()
