#!/usr/bin/env python3
"""Caller-domain regression gate: no direct namespace API calls in sealed ANL."""
import argparse,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
inc=(a.source/'flutter_domain.inc').read_text();main=(a.source/'app_native_loader.c').read_text()
code=re.sub(r'/\*.*?\*/|//[^\n]*','',inc+'\n'+main,flags=re.S)
direct=re.findall(r'\b(dlns_\w+|dlopen_ns)\s*\(',code)
errors=[]
if direct:errors.append('sealed ANL calls namespace APIs directly: '+','.join(sorted(set(direct))))
for kind in ['app','bridge']:
 if '"westlake.anl.'+kind+'.%ld.%lu"' not in inc:errors.append('stock-host owned-name grammar missing: '+kind)
for method in ['create_configured_namespaces','open_namespace']:
 if 'domain->runtime_gate.namespace_host_ops.'+method+'(' not in inc:errors.append('missing host callback '+method)
if '? domain->runtime_gate.namespace_host_ops.open_namespace(' not in main:errors.append('engine open bypasses callback')
packages=re.findall(r'"([a-z][a-z0-9_.]+)"',inc.split('static const char* const packages[] = {',1)[1].split('};',1)[0])
if set(packages)!={'chat.fluffy.fluffychat','app.alextran.immich','com.tombursch.kitchenowl','deckers.thibault.aves.libre','com.adilhanney.saber','org.localsend.localsend_app'}:errors.append('six-package scope changed')
for name in ['libandroid.so','libGLESv2.so','libjnigraphics.so']:
 if '"'+name+'"' not in inc:errors.append('missing canonical preload '+name)
result={'passed':not errors,'errors':errors,'direct_namespace_calls':direct,'scope':packages,'device_io':False,'limit':'caller dispatch/source gate; live loader closure still requires device validation'}
a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));raise SystemExit(0 if result['passed'] else 1)
