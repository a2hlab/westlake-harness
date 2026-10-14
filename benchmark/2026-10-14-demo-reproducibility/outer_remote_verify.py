#!/usr/bin/env python3
import json,subprocess,time
from pathlib import Path
here=Path(__file__).resolve().parent
out=Path(__import__('sys').argv[1]);out.mkdir(parents=True,exist_ok=False)
import shlex
argv=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','hw248','python3 -c '+shlex.quote((here/'remote_probe.py').read_text())]
t=time.time()
with (out/'stdout.json').open('wb') as so,(out/'stderr.txt').open('wb') as se:
 r=subprocess.run(argv,input=(here/'remote-request.json').read_bytes(),stdout=so,stderr=se,timeout=240)
(out/'receipt.json').write_text(json.dumps({'rc':r.returncode,'elapsed_seconds':time.time()-t,'mode':'READONLY_NO_REMOTE_WRITE','request':str(here/'remote-request.json')},indent=2)+'\n')
raise SystemExit(r.returncode)
