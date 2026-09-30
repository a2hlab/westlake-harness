#!/usr/bin/env python3
"""Nine single-key, clean-install trials, preserving every result."""
from pathlib import Path
import subprocess,sys,json,time,datetime
HERE=Path(__file__).resolve().parent
window=json.loads((HERE/'window.json').read_text())
deadline=datetime.datetime.fromisoformat(window['deadline']).timestamp()
for key in window['keys']:
 for trial in range(1,4):
  assert time.time()<deadline-90, 'insufficient authorized window for another trial'
  run=f'u5-flaky-{key}-{trial}'
  with (HERE/(run+'.log')).open('w') as log:
   result=subprocess.run([sys.executable,str(HERE/'run_batch.py'),'5ea',run,'--keys',key],stdout=log,stderr=subprocess.STDOUT)
  print(run, 'exit',result.returncode,flush=True)
  assert result.returncode in (0,1), 'batch stop: inspect before continuing'
