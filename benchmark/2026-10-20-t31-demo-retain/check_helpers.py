#!/usr/bin/env python3
"""New T31 window routing only; no devices or repeated candidate tests."""
import copy,hashlib,importlib.util,json,os,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
D=Path(__file__).resolve().parent;sys.path.insert(0,str(D));sys.path.insert(0,str(D/'helpers'))
import window_paths as wp
import cycle_frames
import window_exec
MAIN=Path(os.environ.get('T31_MAIN',str(D.parents[1].parent/'westlake-harness'))).resolve()
if D.parents[1].name=='westlake-harness':MAIN=D.parents[1]
DATA=MAIN/'benchmark/2026-10-20-t30-request-recovery/deployment/final-01'
class Tests(unittest.TestCase):
 def test_new_window_and_budget(self):
  self.assertEqual(wp.WINDOW.name,'t31-5cd-window-01');self.assertNotIn('t30-5cd-window',str(wp.WINDOW))
  c={'start':100};self.assertEqual(wp.budget(c,False,1299),1)
  with self.assertRaises(AssertionError):wp.budget(c,False,1300)
  self.assertEqual(wp.budget(c,True,1899),1)
  with self.assertRaises(AssertionError):wp.budget(c,True,1900)
  self.assertEqual(cycle_frames.offsets('play'),[0,5,10,20]);self.assertEqual(cycle_frames.offsets('pause'),[0,3]);self.assertEqual(cycle_frames.offsets('resume'),[0,5,10])
 def test_scoped_admission_is_actual_executor_arg(self):
  with tempfile.TemporaryDirectory() as tmp:
   w=Path(tmp)/'t31-5cd-window-91';w.mkdir();a=w/'scoped-admission.json';i=w/'identity.json'
   c={'deploy':str(DATA),'repo':str(MAIN),'serial':wp.SERIAL,'holder':'offline-holder','start':time.time()-5,'hdc':'MUST_NOT_RUN','inputs':str(w/'inputs')}
   ad={'holder':c['holder'],'window_start':c['start'],'boot':'offline-boot','deployment_scope':'T31_5CD_DEMO_CANDIDATE','origin_window_id':w.name,'executor_sha256':wp.EXECUTOR_SHA};a.write_text(json.dumps(ad));i.write_text(json.dumps({'boot':ad['boot'],'parent':111,'parent_birth':222}))
   for mode in ('preflight','apply'):
    argv=window_exec.command(mode,c,w,a,i,w/mode);self.assertEqual(argv[argv.index('--admission')+1],str(a));self.assertEqual(Path(argv[1]),DATA/'executor.py');self.assertEqual(argv[2],mode)
   ad.pop('deployment_scope');a.write_text(json.dumps(ad))
   with self.assertRaises(ValueError):window_exec.command('apply',c,w,a,i,w/'apply')
 def test_preserved_filler_and_no_old_output_root(self):
  for n in ('fill_admission.py','rollback_core.py','rollback_admission.py'):
   self.assertEqual((D/'helpers'/n).read_bytes(),(DATA.parent/'helpers'/n).read_bytes())
  for p in (D/'helpers').glob('*.py'):
   compile(p.read_text(),str(p),'exec');self.assertNotIn('t30-5cd-window-01',p.read_text())
  with patch.dict(os.environ,{},clear=True):
   with self.assertRaises(AssertionError):wp.live()
if __name__=='__main__':unittest.main(verbosity=2)
