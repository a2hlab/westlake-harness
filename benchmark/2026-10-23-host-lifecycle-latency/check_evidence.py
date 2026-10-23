#!/usr/bin/env python3
"""Offline pin verification and same-thread synchronous trace-span extraction."""
import argparse, hashlib, json, re, zipfile
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--main-tree',type=Path,required=True)
p.add_argument('--persistent-root',type=Path,default=Path.home()/'.local/share/westlake')
a=p.parse_args()
h=lambda b:hashlib.sha256(b).hexdigest()
root=a.persistent_root/'toutiao-launcher-20261020'
source_root=a.main_tree/'benchmark/2026-10-20-toutiao-launcher-page'
compile_root=root/'compile-linux-01'; release_root=root/'release-01'
compile_receipt=json.loads((compile_root/'receipt.json').read_text())
release_receipt=json.loads((release_root/'receipt.json').read_text())
checks={}
checks['compile_receipt_to_release']=h((compile_root/'receipt.json').read_bytes())==release_receipt['compile_receipt_sha256']
checks['input_lock_to_release']=h((source_root/'inputs.lock.json').read_bytes())==release_receipt['input_lock_sha256']
source=source_root/'sources/baseline/EntryAbility.js'
source_sha=h(source.read_bytes())
checks['source_to_compile']=source_sha==compile_receipt['source_pins']['sources/baseline/EntryAbility.js']
abc=(compile_root/'baseline/EntryAbility.abc').read_bytes()
checks['abc_to_compile']=h(abc)==compile_receipt['artifacts']['baseline/EntryAbility.abc']['sha256']
hap=release_root/'candidate-signed.hap'
checks['hap_to_release']=h(hap.read_bytes())==release_receipt['artifacts']['candidate-signed.hap']['sha256']
with zipfile.ZipFile(hap) as z:
    checks['hap_member_exact_compiled_bytes']=z.read('ets/entryability/EntryAbility.abc')==abc
for base,rec in [(compile_root,compile_receipt),(release_root,release_receipt)]:
    for name,sha in rec['raw_pins'].items(): checks[f'{base.name}/{name}']=h((base/name).read_bytes())==sha
checks['compile_rc_zero']=(compile_root/'raw/baseline-EntryAbility.rc').read_text().strip()=='0'
starting=a.main_tree/'sources/api-implementations/source-build-host/westlake-java/apps/imehost/EntryAbility.js'
trace=a.persistent_root/'current-boot-manual-reopen-20261023/raw/04/t87-61aa5791.trace'
lines=trace.read_text().splitlines(); stacks={};spans=[];selected=[]
for line_no,line in enumerate(lines,1):
    m=re.search(r'-(\d+)\s+\([^)]*\).*?\s(\d+\.\d+): tracing_mark_write: ([BE])\|(\d+)(?:\|(.*))?$',line)
    if not m: continue
    tid,ts,kind,tgid,name=m.groups(); ts=float(ts); key=(tid,tgid)
    if kind=='B':
        stacks.setdefault(key,[]).append((ts,line_no,name))
    elif stacks.get(key):
        start,first,name=stacks[key].pop()
        if tgid=='4958' and ('CallObjectMethod:' in name or '##EntryAbility' in name or 'AfterForeground()' in name):
            spans.append({'tid':int(tid),'tgid':int(tgid),'name':name,'start':start,'end':ts,'duration_ms':round((ts-start)*1000,6),'start_line':first,'end_line':line_no})
    if kind=='B' and any(s in (name or '') for s in ['CompleteForegroundSuccess','RequestSceneSession(31 )','SCBCb:OnShiftFocus, PID:31']):
        selected.append({'line':line_no,'uptime':ts,'tgid':int(tgid),'name':name})
first_child=next(({'line':i,'raw':s} for i,s in enumerate(lines,1) if '|6291|' in s),None)
result={'all_checks_passed':all(checks.values()),'checks':checks,'source_sha256':source_sha,'starting_source_sha256':h(starting.read_bytes()),'abc_sha256':h(abc),'hap_sha256':h(hap.read_bytes()),'trace_sha256':h(trace.read_bytes()),'host_spans':spans,'window_framework_markers':selected,'first_child_trace_marker':first_child,'limitations':['Historical compiler SHA is receipt-pinned; compiler not executed or rehashed in this offline review.','Framework CallObjectMethod markers do not prove an application override exists or executed.','Window31 framework markers alone do not bind owner PID6291.','First recorded child marker is not child birth or first window.']}
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['all_checks_passed'] else 1)
