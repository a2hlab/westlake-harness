#!/usr/bin/env python3
"""T136 authorized recovery continuation: no payload write and no reboot."""
import importlib.util,json,re,sys,time
from pathlib import Path
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('t136_entry',P/'execute.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
old=Path(sys.argv[1]).resolve()
assert json.loads((old/'result.json').read_text())['rollback']=='recovery_required'
old_receipts={p.parent.name.split('-',1)[1]:p.parent for p in old.glob('*/receipt.json')}
assert 'atomic-rollback' in old_receipts and 'rollback-reboot' in old_receipts
assert json.loads((old_receipts['atomic-rollback']/'receipt.json').read_text())['local_rc']==0
assert m.BASELINE in (old_receipts['rollback-disk']/'stdout').read_text()
w=m.Window();w.recovery=True
w.start=json.loads((old_receipts['held-before']/'command.json').read_text())['start_monotonic']
w.owner=(old_receipts['held-acquired']/'stdout').read_text().strip();assert w.owner.startswith(m.LANE+' ')
power=(old_receipts['power-before']/'stdout').read_text();b=re.search(r'Timeout=(\d+)ms',power);o=re.search(r'OverrideTimeout=(\d+)ms',power);assert b and o
w.prepower=dict(base=int(b.group(1)),override=int(o.group(1)))
w.original=json.loads((old/'fresh-binding.json').read_text())['identity']
expected=json.loads((old/'fresh-binding.json').read_text())['object']
m.save(w.run/'continuation.json',{'original_run':old.name,'original_budget_start_monotonic':w.start,'scope':'service readiness, baseline ordinary UI/mapping, original power and own unlock only','entry_sha256':m.digest(P/'execute.py'),'continuation_source_sha256':m.digest(Path(__file__))})
verified=False
try:
    w.held();until=min(time.monotonic()+120,w.start+1600)
    while time.monotonic()<until:
        r,s,e=w.call('service-readiness',[m.HDC,'-t',m.SERIAL,'shell',"hidumper -s PowerManagerService -a '-a' | grep -E 'ScreenOffTime|Current State'"],True)
        if r['local_rc']==0 and not e.strip() and re.search(r'Current State: \w+',s) and re.search(r'ScreenOffTime: Timeout=\d+ms',s):break
        time.sleep(2)
    else:raise RuntimeError('service not ready within120s')
    assert w.object('baseline-disk-before',m.TARGET)==expected
    identity=w.stage('baseline-restored',m.BASELINE)
    assert w.object('baseline-disk-after',m.TARGET)==expected
    system=w.object('system-final',m.SYSTEM)
    assert system['sha256']==m.SYSTEM_SHA
    w.screen('final-recovery');verified=True
    w.result.update(status='baseline_mapping_verified',baseline_actual_mapping_verified=True,identity=identity)
except BaseException as e:w.result.update(status='recovery_required',error=str(e));print('RECOVERY_STOP '+str(e),flush=True)
finally:
    try:
        w.held();w.shell('power-restore','power-shell timeout -o '+str(w.prepower['override']));post=w.power('power-final');assert all(post[k]==w.prepower[k] for k in ('base','override'));w.result['power_final']=post
        if verified:
            w.call('unlock',['bash',str(m.NOTE),'unlock',str(m.BOARD),m.SERIAL,m.LANE]);r,s,e=w.call('final-held',['bash',str(m.NOTE),'held',m.SERIAL],True);w.result['released']=r['local_rc']==1 and not s.strip() and not e.strip()
    except BaseException as e:w.result['cleanup_error']=str(e)
    w.result['elapsed_from_original_start']=w.elapsed();m.save(w.run/'result.json',w.result);print('DONE '+json.dumps(w.result),flush=True)
