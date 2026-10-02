#!/usr/bin/env python3
"""Actual final ELF exports/dynamic tags; never infer API visibility from source alone."""
import json,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];W=R.parent
sys.path.insert(0,str(R/'scripts/lab'));import generation_bundle as gb,generation_static_checks as st,native_needed_gate as ng

def symbols(path,defined=True):
 flag='--defined-only' if defined else '--undefined-only'
 text=subprocess.check_output(['llvm-nm','-D',flag,'--format=posix',str(path)],text=True)
 return {line.split()[0].split('@')[0] for line in text.splitlines() if line.strip()}
def main():
 c=json.loads((H/'composition.json').read_text());n=Path(c['package'].replace('$WORKSPACES',str(W)))/'native';b=Path(c['base_bundle'].replace('$WORKSPACES',str(W)))/'native';rows=[]
 for name in ['libicu_jni.so','libnativeloader.so','libmediandk.so']:
  candidate=n/'payload/android/lib64'/name;old=b/'payload/android/lib64'/name;exports=symbols(candidate);meta=ng.parse_dynamic(subprocess.check_output(['llvm-readelf','-d','--wide',str(candidate)],text=True));row={'name':name,'sha256':gb.sha(candidate),'dynamic':meta,'exports':len(exports),'undefined':len(symbols(candidate,False))}
  if old.exists():before=symbols(old);row['removed_exports']=sorted(before-exports);row['added_exports']=sorted(exports-before)
  if name=='libmediandk.so':row['open_site_scan']=st.scan(candidate);row['existing_private_zigzag_unchanged']=gb.sha(n/'payload/zigzag/libmediandk.so')==gb.sha(b/'payload/zigzag/libmediandk.so')
  rows.append(row)
 (H/'artifact-checks.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps([{k:v for k,v in r.items() if k!='open_site_scan'} for r in rows],indent=2))
if __name__=='__main__':main()
