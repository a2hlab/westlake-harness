import json,subprocess,sys,tempfile
from pathlib import Path
H=Path(__file__).resolve().parent
if sys.argv[1]=='bionic':
 with tempfile.TemporaryDirectory() as d:
  p=Path(d)/'test';subprocess.run(['c++','-std=c++17',str(H/'src/test_compat.cpp'),str(H/'src/strerror_r_compat.cpp'),str(H/'src/dlopen_ext_compat.cpp'),'-o',str(p)],check=True);subprocess.run([str(p)],check=True)
subprocess.run([sys.executable,str(H/'audit.py')],check=True)
g=json.loads((H/'native-gate.json').read_text());assert g['status']=='REJECT' and not g['errors']
p=json.loads((H/'exception-proposal.json').read_text());assert p['status']=='PENDING_OUTER_APPROVAL' and p['counts']=={'N7-new':59,'U5-common':126}
assert all(x['approval']=='PENDING' for x in p['entries'])
print('PASS offline evidence only; candidate is NOT authorized for deployment')
