#!/usr/bin/env python3
"""Append one row using the original atlas assembler; no device or main writes."""
import argparse,copy,hashlib,importlib.util,json,os,posixpath,shutil
from pathlib import Path, PurePosixPath
HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',str(HERE.parents[2])))
MAIN=WS/'westlake-harness';BASE=MAIN/'benchmark/2026-10-12-api-progress';VIEW=HERE/'views'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,j):Path(p).write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
def setup():
 for r in read(HERE/'base-pins.json'):
  p=WS/r['path'].removeprefix('$WORKSPACES/');assert sha(p)==r['sha256'],'original generator/input drift: '+str(p)
 s=importlib.util.spec_from_file_location('original_api_atlas',BASE/'atlas.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
 original_collect=a.collect_rows;original_markdown=a.markdown;original_html=a.html_atlas
 a.ROOT=MAIN;a.HERE=VIEW;a.WORKSPACES=WS
 original_resolve=a.resolve
 aliases=read(HERE/'historical-evidence-aliases.json')
 def resolve(name):
  if name in aliases:
   ref=aliases[name];assert not Path(ref['path']).is_absolute() and '..' not in Path(ref['path']).parts
   p=HERE/ref['path'];assert sha(p)==ref['sha256'],'historical signed evidence alias drift';return p
  return original_resolve(name)
 a.resolve=resolve
 # Render against the FINAL logical layout, never the author/verification cwd.
 logical_repo=PurePosixPath('/WORKSPACES/westlake-harness')
 logical_package=logical_repo/'benchmark/2026-10-13-api-progress-r6'
 def link(name):
  if name in aliases:target=logical_package/aliases[name]['path']
  elif name.startswith('$WORKSPACES/'):target=PurePosixPath('/WORKSPACES')/name.removeprefix('$WORKSPACES/')
  else:target=logical_repo/name
  return posixpath.relpath(str(target),str(logical_package/'views'))
 a.source_link=lambda name,label=None:'['+(label or Path(name).name)+'](<'+link(name)+'>)'
 def collect():
  a.HERE=BASE
  try:shards,rows=original_collect()
  finally:a.HERE=VIEW
  row=read(HERE/'row-r6.json');assert row['id'] not in {r['id'] for r in rows}
  row['record_kind']='api_capability';shards['native']['rows'].append(row);rows.append(row)
  return shards,rows
 a.collect_rows=collect
 a.markdown=lambda rows,summary:original_markdown(rows,summary).replace('更新：2026-10-12。','更新：2026-10-13（R6一行增量；基础图为2026-10-12）。')
 def html(rows,summary):
  names={e['path'] for r in rows for e in r['evidence']}|{r['path'] for r in read(VIEW/'platform-context.json')}
  mapping=json.dumps({n:link(n) for n in sorted(names)},ensure_ascii=False).replace('<','\\u003c')
  old="function link(path){return path.startsWith('$WORKSPACES/')?'../../../'+path.slice(12):'../../'+path;}"
  text=original_html(rows,summary);assert text.count(old)==1,'original renderer link seam changed'
  return text.replace(old,'const evidenceLinks='+mapping+";\nfunction link(path){return evidenceLinks[path]||'#';}")
 a.html_atlas=html
 return a

def check():
 a=setup();result=a.check();negative=a.negative_checks();old=read(BASE/'api-progress.json')['rows'];new=read(VIEW/'api-progress.json')['rows']
 previous={r['id']:r for r in old};current={r['id']:r for r in new}
 assert set(current)-set(previous)=={'NATIVE-173'} and set(previous)<=set(current)
 assert all(current[k]==v for k,v in previous.items()),'an old row/whole family was upgraded'
 row=current['NATIVE-173'];assert row['members']==['android.graphics.BLASTBufferQueue.nativeUpdate(JJJJI)V'] and row['implementation_status']=='partial'
 assert row['frozen_ids']==[] and row['deployment_status']=='candidate'
 assert row['android_tested']==row['android_api_level']==row['apk_target_sdk']=='unknown' and row['android_source'].startswith('unknown；source-only')
 assert '6.1.0.31' in row['oh_tested'] and 'full128' not in row['members']
 assert any('128' in g and 'pending' in g for g in row['gaps']) and any('未冻结' in g for g in row['gaps'])
 assert len([v for v in row['validations'] if v['level']=='functional'])==1
 assert len([v for v in row['validations'] if v['level']=='reported'])==5
 result.update(old_rows_unchanged=len(old),new_rows=1,**negative,device_calls=0,api_frozen=False,full128='pending')
 return result

def build():
 VIEW.mkdir(parents=True,exist_ok=True)
 for name in ['row-template.json','curation.json','platform-context.json']:shutil.copy2(BASE/name,VIEW/name)
 a=setup();summary=a.build();summary['date']='2026-10-13'
 write(VIEW/'results.json',summary);data=read(VIEW/'api-progress.json');data['metadata']=summary;write(VIEW/'api-progress.json',data)
 (VIEW/'API-PROGRESS.zh.md').write_text(a.markdown(data['rows'],summary));(VIEW/'index.html').write_text(a.html_atlas(data['rows'],summary))
 result=check();write(HERE/'verification.json',result);return result
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('command',choices=['build','check']);args=ap.parse_args();print(json.dumps(build() if args.command=='build' else check(),ensure_ascii=False))
