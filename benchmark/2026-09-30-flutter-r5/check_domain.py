#!/usr/bin/env python3
"""Reject wrong owner names/private filenames; this is not a device namespace test."""
import argparse,hashlib,json,re
from pathlib import Path
p=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,default=p/'src/flutter_domain.inc');ap.add_argument('--package',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
artifacts=json.loads((p.parent/'2026-09-30-flutter-candidate/evidence-r3/artifacts.json').read_text());s=a.source.read_text();m=json.loads((a.package/'package.json').read_text())
shared={n for literal in re.findall(r'"(lib[^"\n]*)"',s) for n in literal.split(':')}
private={v['soname'][0] for k,v in artifacts.items() if k!='libapp_native_loader.so'}
missing=sorted({n for k,v in artifacts.items() if k!='libapp_native_loader.so' for n in v['needed'] if n not in shared|private})
block=s.split('const char* preload[] = {',1)[1].split('};',1)[0];preload=re.findall(r'"([^"\n]+)"',block)
root='/system/android/lib64/westlake_flutter';expected=['libandroid.so','libGLESv2.so','libjnigraphics.so'];errors=[]
if preload!=expected:errors.append('preload must use three canonical basenames')
if 'const char* private_root = "'+root+'";' not in s:errors.append('private root missing')
if '&domain->flutter, app_name, search, permitted)' not in s:errors.append('private search not used')
if 'libnative_window.so:libnative_buffer.so' in s:errors.append('input filenames used instead of real SONAME')
for n,v in artifacts.items():
 if n=='libapp_native_loader.so':continue
 dest='payload/android/lib64/westlake_flutter/'+v['soname'][0];f=a.package/dest
 if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=v['sha256'] or m['files'].get(dest)!=v['sha256'] or m['live_hashes'].get(root+'/'+v['soname'][0])!=v['sha256']:errors.append('private file identity: '+dest)
packages=re.findall(r'"([a-z][a-z0-9_.]+)"',s.split('static const char* const packages[] = {',1)[1].split('};',1)[0])
if set(packages)!={'chat.fluffy.fluffychat','app.alextran.immich','com.tombursch.kitchenowl','deckers.thibault.aves.libre','com.adilhanney.saber','org.localsend.localsend_app'}:errors.append('package scope changed')
r={'passed':not missing and not errors,'missing_direct_owner_names':missing,'errors':errors,'preload':preload,'package_scope':packages,'device_io':False,'limit':'physical identity + source policy only; live owners and symbol lookup still need device validation'}
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));raise SystemExit(0 if r['passed'] else 1)
