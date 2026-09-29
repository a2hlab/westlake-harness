#!/usr/bin/env python3
"""Copy selected immutable batch evidence; preserve facts verbatim."""
import json,re,shutil
from pathlib import Path
R=Path(__file__).resolve().parent
for run in (R/'runs').iterdir():
 if not run.is_dir():continue
 for board in run.iterdir():
  if not board.is_dir():continue
  dst=R/'evidence'/run.name/board.name;dst.mkdir(parents=True,exist_ok=True)
  for name in ['facts.txt','preflight.json','runtime-fingerprint.txt','runtime-fingerprint.json','summary.json']:
   if (board/name).is_file():shutil.copy2(board/name,dst/name)
  for record in board.glob('*/record.json'):
   d=dst/record.parent.name;d.mkdir(exist_ok=True)
   shutil.copy2(record,d/'record.json')
   for pattern in ['*.jpeg','processes-t*.txt','processes-final.txt']:
    for p in record.parent.glob(pattern):shutil.copy2(p,d/p.name)
   log=record.parent/'hilog.txt'
   if log.exists():
    selected=[]
    for i,line in enumerate(log.read_text(errors='replace').splitlines(),1):
     if re.search(r'FATAL EXCEPTION|JNI FatalError|ABORT:|java\.lang\.(?:UnsatisfiedLinkError|NullPointerException|RuntimeException)|Caused by:|Error loading shared library libhitrace',line):selected.append(f'{i}:{line}')
    (d/'failure-excerpts.txt').write_text('\n'.join(selected)+'\n')
