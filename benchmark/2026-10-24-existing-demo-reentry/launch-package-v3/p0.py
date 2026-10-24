"""Frozen T123 P0, followed by the same process's ordinary recorder."""
from receipt_candidate import *
import runpy,sys
publish_once(RUN/'clock.json',{'wallclock':wall(),'monotonic':time.monotonic()})
try:
    commands=PLAN['phases'][0]['commands']
    r,s,e=call('00-held',commands[0]);assert r['rc']==1 and not r['timeout'] and s=='' and e==''
    r,s,e=call('01-identity',commands[1]);good(r,s,e);ident=identity(s)
    r,s,e=call('02-power',commands[2]);good(r,s,e);preimage=power(s)
    r,s,e=call('03-hashes',commands[3]);good(r,s,e)
    found={}
    for line in s.splitlines():
        m=re.fullmatch(r'([0-9a-f]{64})\s+(.+)',line)
        if not m or m[2] in found:raise RuntimeError('hash parse/duplicate')
        found[m[2]]=m[1]
    assert found==PLAN['control_expected_sha256'],'control SHA mismatch'
    result={'status':'P0_PASS','identity':ident,'power_preimage':preimage,'hash_count':len(found)}
except Exception as error:
    result={'status':'P0_STOP_NO_MUTATION','error':repr(error)}
publish_once(RUN/'p0-result.json',result)
print('P0_RESULT '+json.dumps(result),flush=True)
if result['status']!='P0_PASS':raise SystemExit(2)
sys.argv=[str(RUN/'initial_stage_candidate.py'),str(RUN/'select_icon.py')]
runpy.run_path(str(RUN/'initial_stage_candidate.py'),run_name='__main__')
