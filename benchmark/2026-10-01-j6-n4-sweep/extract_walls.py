#!/usr/bin/env python3
"""Pin exact lines supporting the observed post-registration failures."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
boards=list((P/'runs/n4order-targets-5ea').glob('5ea*'));assert len(boards)==1
patterns={
 'fd-app':['Caused by: java.lang.NullPointerException: Null reference used for synchronization','at android.os.SystemVibratorManager.getVibratorIds'],
 'fd-fluffychat':['resident runtime published for','Flutter private preload libandroid.so: Error loading shared library liboh_android_runtime.so'],
 'burgerking':['resident runtime published for','dlopen_ns failed for','Error loading shared library libz.so'],
 'firefox':['Caused by:','UnsatisfiedLinkError:','Error relocating','__get_h_errno','__errno','FATAL EXCEPTION','MUSL-SIGCHAIN']}
rows=[]
for key,terms in patterns.items():
 f=boards[0]/key/'hilog.txt'
 if not f.exists():continue
 lines=f.read_text(errors='replace').splitlines();matches=[{'line':i,'text':s} for i,s in enumerate(lines,1) if '[class_linker.cc:' not in s and any(t in s for t in terms)]
 rows.append({'key':key,'hilog':str(f.relative_to(P)),'hilog_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'matches':matches})
(P/'walls.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
