"""Known answers for boot-scoped recovery receipt polling; no board calls."""
import importlib.util,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location("restore",Path(__file__).with_name("restore_v2_enabled.py"));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ReceiptTests(unittest.TestCase):
 def run_poll(self,rows):
  rows=iter(rows);tick=[0];last=[""]
  def read():
   last[0]=next(rows,last[0]);return last[0]
  def sleep(n):tick[0]+=n
  return m.wait_ready(read,"new",timeout=6,clock=lambda:tick[0],sleep=sleep)
 def test_old_ready_then_current_ready(self):
  result=self.run_poll(["state=READY\nboot_id=old\nlayers=56","state=READY\nboot_id=new\nlayers=56"])
  self.assertIn("boot_id=new",result)
 def test_stale_receipt_times_out(self):
  with self.assertRaisesRegex(RuntimeError,"timeout"):self.run_poll(["state=READY\nboot_id=old\nlayers=56"])
 def test_current_failure_stops(self):
  with self.assertRaisesRegex(RuntimeError,"recover failed"):self.run_poll(["state=FAILED\nboot_id=new\nfailed_step=SHA"])
 def test_wrong_layers_never_pass(self):
  with self.assertRaisesRegex(RuntimeError,"timeout"):self.run_poll(["state=READY\nboot_id=new\nlayers=55"])
if __name__=="__main__":unittest.main()
