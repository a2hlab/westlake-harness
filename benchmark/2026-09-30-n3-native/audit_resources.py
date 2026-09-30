#!/usr/bin/env python3
"""Evaluate the actual VLC style graph; do not invent a resource fallback."""
from pathlib import Path
import hashlib,json,re,subprocess
P=Path(__file__).resolve().parent
apk=Path('/Users/zhaoyue/a2hlab/app-inputs/vlc/vlc.apk')
aapt='/Users/zhaoyue/Library/Android/sdk/build-tools/37.0.0/aapt2'
s=subprocess.check_output([aapt,'dump','resources',str(apk)],text=True)
styles={};current=None
for l in s.splitlines():
 m=re.match(r'    resource (0x[0-9a-f]+) style/(.*)',l)
 if m:current=m.group(1);styles[current]={'name':m.group(2),'parents':set(),'defines_attr':False,'raw':[l]};continue
 if l.startswith('    resource '):current=None
 if current:
  styles[current]['raw'].append(l)
  m=re.search(r'parent=style/.* \((0x[0-9a-f]+)\)',l)
  if m:styles[current]['parents'].add(m.group(1))
  if 'background_default(0x7f040072)=' in l:styles[current]['defines_attr']=True
out={};all_seen=set()
for root in ['0x7f1402f9','0x7f140278','0x7f1402ec']:
 todo=[root];seen=set();chain=[]
 while todo:
  x=todo.pop()
  if x in seen:continue
  seen.add(x)
  if x not in styles:continue
  row=styles[x];chain.append(dict(id=x,name=row['name'],defines_attr=row['defines_attr']));todo+=sorted(row['parents'])
 out[root]=dict(chain=chain,definition_present=any(r['defines_attr'] for r in chain));all_seen|=seen
assert not out['0x7f1402f9']['definition_present']
assert not out['0x7f140278']['definition_present']
assert out['0x7f1402ec']['definition_present']
(P/'evidence/vlc-theme-graph.json').write_text(json.dumps({'apk':str(apk),'apk_sha256':hashlib.sha256(apk.read_bytes()).hexdigest(),'styles':out,'limit':'Union of APK config variants; framework parent cannot define app-specific 0x7f attribute. Explains active theme failure, does not establish why that context was selected.'},indent=2)+'\n')
(P/'evidence/vlc-selected-resources.txt').write_text('\n'.join(l for k in sorted(all_seen) if k in styles for l in styles[k]['raw'])+'\n')
print('PASS actual APK: Transparent and Empty lack attr; Onboarding parent provides it')
