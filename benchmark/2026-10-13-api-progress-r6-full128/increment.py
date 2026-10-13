#!/usr/bin/env python3
"""Update only NATIVE-173 full128 evidence through the original assembler; no device/main writes."""
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
 logical_package=logical_repo/'benchmark/2026-10-13-api-progress-r6-full128'
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
 a.markdown=lambda rows,summary:original_markdown(rows,summary).replace('更新：2026-10-12。','更新：2026-10-13（R6 full128受限采认增量；基础图为2026-10-12）。')
 def html(rows,summary):
  names={e['path'] for r in rows for e in r['evidence']}|{r['path'] for r in read(VIEW/'platform-context.json')}
  mapping=json.dumps({n:link(n) for n in sorted(names)},ensure_ascii=False).replace('<','\\u003c')
  old="function link(path){return path.startsWith('$WORKSPACES/')?'../../../'+path.slice(12):'../../'+path;}"
  text=original_html(rows,summary).replace('WESTLAKE HARNESS / 2026.10.12','WESTLAKE HARNESS / 2026.10.13 · R6 FULL128');assert text.count(old)==1,'original renderer link seam changed'
  return text.replace(old,'const evidenceLinks='+mapping+";\nfunction link(path){return evidenceLinks[path]||'#';}").replace('<p><a href="API-PROGRESS.zh.md">','<p><a href="index.en.html">English</a> · <a href="API-PROGRESS.zh.md">')
 a.html_atlas=html
 return a

def english_html(zh):
 # Keep the embedded315-row canonical payload exact; translate presentation only.
 begin='<script id="data" type="application/json">';first,rest=zh.split(begin,1)
 payload,last=rest.split('</script>',1)
 from readable import english_shell, english_presentation
 first,last=english_shell(first,last)
 marker='for(const r of rows){const d='
 assert last.count(marker)==1
 display=json.dumps(english_presentation(read(HERE/'row-r6.json')),ensure_ascii=False).replace('<','\\u003c')
 last=last.replace(marker,'const englishNative173='+display+";for(const canonical of rows){const r=canonical.id==='NATIVE-173'?Object.assign({},canonical,englishNative173):canonical;const d=")
 return first+begin+payload+'</script>'+last

def check():
 a=setup();result=a.check();negative=a.negative_checks()
 old=read(MAIN/'benchmark/2026-10-13-api-progress-r6/views/api-progress.json')['rows'];new=read(VIEW/'api-progress.json')['rows']
 previous={r['id']:r for r in old};current={r['id']:r for r in new}
 assert set(previous)==set(current) and len(new)==315
 assert all(current[k]==v for k,v in previous.items() if k!='NATIVE-173'),'old314 field drift'
 row=current['NATIVE-173'];oldrow=previous['NATIVE-173']
 changed=[k for k in row if row[k]!=oldrow[k]]
 assert set(changed)=={'oh_tested','route_generation','validations','gaps','evidence'}
 assert row['validations'][:-1]==oldrow['validations'] and row['evidence'][:-4]==oldrow['evidence']
 assert row['members']==['android.graphics.BLASTBufferQueue.nativeUpdate(JJJJI)V'] and row['implementation_status']=='partial'
 assert row['frozen_ids']==[] and row['deployment_status']=='candidate'
 assert row['android_tested']==row['android_api_level']==row['apk_target_sdk']=='unknown' and row['android_source'].startswith('unknown；source-only')
 assert '6.1.0.31' in row['oh_tested'] and '未冻结' in row['gaps'][0]
 receipts=read(HERE/'evidence/source-receipts.json')
 for ref in receipts['copied_byte_identical_receipts']:
  assert sha(a.resolve(ref['path']))==ref['sha256']==sha(HERE/ref['local_copy'])
 acceptance=read(a.resolve(receipts['authority']['path']))
 assert acceptance['status']=='ACCEPT_SCOPED_STARTUP_NONREGRESSION_WITH_EXISTING_LIMITATIONS'
 assert acceptance['canonical_keys']==128 and acceptance['completed_execute_rc']==acceptance['original947_recovery_rc']==0
 assert acceptance['v2_sealed'] is False and acceptance['authorizes61b_write'] is False
 assert acceptance['candidate_runtime_sha256']=='f28bd1b3d44e2944f77911c2ad71376869f7f3ebc6dcd8434dfea869f4056db0'
 assert len([v for v in row['validations'] if v['level']=='functional'])==1
 assert len([v for v in row['validations'] if v['level']=='reported'])==6
 en=(VIEW/'index.en.html').read_text();zh=(VIEW/'index.html').read_text()
 assert en==english_html(zh),'English HTML regeneration drift'
 marker='<script id="data" type="application/json">'
 assert en.split(marker,1)[1].split('</script>',1)[0]==zh.split(marker,1)[1].split('</script>',1)[0],'English canonical payload drift'
 assert 'index.en.html' in zh and 'index.html' in en
 result.update(old_rows_unchanged=314,changed_rows=['NATIVE-173'],changed_fields=changed,**negative,device_calls=0,api_frozen=False,v2_sealed=False,full128=acceptance['status'],authority_sha256=receipts['authority']['sha256'])
 return result

def build():
 VIEW.mkdir(parents=True,exist_ok=True)
 for name in ['row-template.json','curation.json','platform-context.json']:shutil.copy2(BASE/name,VIEW/name)
 a=setup();summary=a.build();summary['date']='2026-10-13'
 write(VIEW/'results.json',summary);data=read(VIEW/'api-progress.json');data['metadata']=summary;write(VIEW/'api-progress.json',data)
 (VIEW/'API-PROGRESS.zh.md').write_text(a.markdown(data['rows'],summary));(VIEW/'index.html').write_text(a.html_atlas(data['rows'],summary))
 (VIEW/'index.en.html').write_text(english_html((VIEW/'index.html').read_text()))
 result=check();write(HERE/'verification.json',result);return result
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('command',choices=['build','check']);args=ap.parse_args();print(json.dumps(build() if args.command=='build' else check(),ensure_ascii=False))
