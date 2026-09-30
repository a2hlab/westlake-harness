#!/usr/bin/env python3
"""Check bounded owner names and private lookup names before any deployment."""
import json,re
from pathlib import Path
p=Path(__file__).resolve().parent
artifacts=json.loads((p/'evidence-r3/artifacts.json').read_text())
s=(p/'src/flutter_domain.inc').read_text()
shared={n for literal in re.findall(r'"(lib[^"\n]*)"',s) for n in literal.split(':')}
private={v['soname'][0] for k,v in artifacts.items() if k!='libapp_native_loader.so'}
missing=sorted({n for k,v in artifacts.items() if k!='libapp_native_loader.so' for n in v['needed'] if n not in shared|private})
preload=re.findall(r'"(/system/android/lib64/[^"\n]+\.so)"',s)
name_mismatch=[{'filename':Path(f).name,'needed_name':artifacts[Path(f).name]['soname'][0]} for f in preload if Path(f).name!=artifacts[Path(f).name]['soname'][0]]
r={'passed':not missing and not name_mismatch,'missing_direct_owner_names':missing,'preload_name_mismatches':name_mismatch,'rule':'OH6.1 musl shortname matching; arbitrary DT_SONAME does not create a filename alias','device_io':False}
(p/'evidence-r3/domain-gate.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));raise SystemExit(0 if r['passed'] else 1)
