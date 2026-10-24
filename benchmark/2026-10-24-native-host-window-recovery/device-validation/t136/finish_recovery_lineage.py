#!/usr/bin/env python3
"""T136 authorized recovery continuation: no payload write and no reboot."""
import importlib.util,json,re,sys,time
from pathlib import Path
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('t136_entry',P/'execute_v6.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
old=Path(sys.argv[1]).resolve()
assert json.loads((old/'result.json').read_text())['rollback']=='recovery_required'
old_receipts={p.parent.name.split('-',1)[1]:p.parent for p in old.glob('*/receipt.json')}
assert 'atomic-rollback' in old_receipts and 'rollback-reboot' in old_receipts
assert json.loads((old_receipts['atomic-rollback']/'receipt.json').read_text())['local_rc']==0
assert m.BASELINE in (old_receipts['rollback-disk']/'stdout').read_text()
from recovery_lineage import RecoveryWindow, select_main
w=RecoveryWindow();w.recovery=True
w.start=json.loads((old_receipts['held-before']/'command.json').read_text())['start_monotonic']
w.owner=(old_receipts['held-acquired']/'stdout').read_text().strip();assert w.owner.startswith(m.LANE+' ')
power=(old_receipts['power-before']/'stdout').read_text();b=re.search(r'Timeout=(\d+)ms',power);o=re.search(r'OverrideTimeout=(\d+)ms',power);assert b and o
w.prepower=dict(base=int(b.group(1)),override=int(o.group(1)))
sources=[old/name for name in ('fresh-binding.json','fresh-idle-admission.json') if (old/name).is_file()]
assert len(sources)==1, 'require exactly one authoritative preimage binding'
original_binding=json.loads(sources[0].read_text())
w.original=original_binding['identity']
expected=original_binding['object']
m.save(w.run/'continuation.json',{'original_run':old.name,'original_budget_start_monotonic':w.start,'scope':'PPID main-child and full same-name descendant baseline mapping; no icon/swipe/reboot/payload; final screenshot, power and own unlock only','entry_sha256':m.digest(P/'execute_v6.py'),'continuation_source_sha256':m.digest(Path(__file__)), 'lineage_source_sha256':m.digest(P/'recovery_lineage.py')})
verified=False
try:
    w.held()
    assert w.object('baseline-disk-before',m.TARGET)==expected
    identity,obj=w.bind('baseline-lineage',m.BASELINE)
    assert identity["boot"] != w.original["boot"], "recovery reboot must establish new boot"
    assert w.object('baseline-disk-after',m.TARGET)==expected
    assert w.object('system-final',m.SYSTEM)['sha256']==m.SYSTEM_SHA
    w.screen('final-recovery');verified=True
    w.result.update(status='baseline_mapping_verified',baseline_actual_mapping_verified=True,identity=identity,additional_icon_clicks=0,additional_payload_writes=0,additional_reboots=0)
except BaseException as e:w.result.update(status='recovery_required',error=str(e));print('RECOVERY_STOP '+str(e),flush=True)
finally:
    try:
        w.held();w.shell('power-restore','power-shell timeout -o '+str(w.prepower['override']));post=w.power('power-final');assert all(post[k]==w.prepower[k] for k in ('base','override'));w.result['power_final']=post
        if verified:
            w.call('unlock',['bash',str(m.NOTE),'unlock',str(m.BOARD),m.SERIAL,m.LANE]);r,s,e=w.call('final-held',['bash',str(m.NOTE),'held',m.SERIAL],True);w.result['released']=r['local_rc']==1 and not s.strip() and not e.strip()
    except BaseException as e:w.result['cleanup_error']=str(e)
    w.result['elapsed_from_original_start']=w.elapsed();m.save(w.run/'result.json',w.result);print('DONE '+json.dumps(w.result),flush=True)
