#!/usr/bin/env python3
"""Reuse the frozen315 atlas chain for a five-field final61b evidence increment."""
import argparse,copy,importlib.util,json,os,posixpath,re,shutil,sys,tempfile
from pathlib import Path,PurePosixPath
import consume

HERE=Path(__file__).resolve().parent
WS=consume.WS;MAIN=WS/'westlake-harness'
PARENT=MAIN/'benchmark/2026-10-13-api-progress-r6-full128'

def write(p,obj):Path(p).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def module(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def old_rows():
 consume.base()
 return consume.read(PARENT/'views/api-progress.json')['rows']
def make_row(binding):
 row=copy.deepcopy(next(r for r in old_rows() if r['id']=='NATIVE-173'))
 row['oh_tested']+='；本轮实际61b/boot086d同板128受限首屏不退化采认，OH仍仅6.1.0.31'
 row['route_generation']+='；61b原八窗128、121t10+7t20、256原截图；source c208/runtime f28，不是V2或API冻结签认'
 refs=binding['evidence'];paths=[e['path'] for e in refs]
 result=binding['authority']['status']+'；同61b原128/256及两路逐key审定；仅startup nonregression。'+binding['facts_total']+'；原detach未采global driver_exit_code（null/unknown）；完成由原128 completion、driver退出观察、八窗真实rc及三次identity PASS支持。原NOT_LIT/加载/空态、foreground_unconfirmed和失败/崩溃状态不改，不代表一般功能全可用。'
 row['validations'].append({'level':'reported','apk':'Fixed128 / same61b startup only','result':result,'evidence_paths':paths})
 row['evidence'].extend(refs)
 row['gaps']=[g.replace('61b用户解封/同板最终V2验收仍pending。','本轮同61b128只补受限首屏证据；最终V2封板独立签认。')
               .replace('受保护61b解封及最终同板验收仍待完成','本轮同61b128仅受限首屏采认；最终封板独立签认')
               .replace('Protected61b unseal and final sameboard acceptance still pending','Same61b128 accepted only for scoped startup; final sealing is independent') for g in row['gaps']]
 row['gaps'].append('实际61b128限于首屏/截图，不升格功能验证，不签V2；outer原限制：'+'；'.join(binding['authority']['limitations']))
 return row
def link(name):
 aliases=consume.read(PARENT/'historical-evidence-aliases.json')
 root=PurePosixPath('/WORKSPACES/westlake-harness')
 package=root/'benchmark/2026-10-14-api-progress-final61b'
 if name in aliases:target=root/'benchmark/2026-10-13-api-progress-r6-full128'/aliases[name]['path']
 elif name.startswith('$WORKSPACES/'):target=PurePosixPath('/WORKSPACES')/name.removeprefix('$WORKSPACES/')
 else:target=root/name
 return posixpath.relpath(str(target),str(package/'views'))
def setup(view,row):
 # Original assembler/row validator and historical aliases remain in use.
 parent=module(PARENT/'increment.py','frozen_full128_atlas');a=parent.setup()
 a.HERE=view;collect=a.collect_rows;md=a.markdown;html=a.html_atlas
 def rows():
  try:shards,records=collect()
  finally:a.HERE=view
  for shard in shards.values():
   shard['rows']=[copy.deepcopy(row) if r['id']=='NATIVE-173' else r for r in shard['rows']]
  return shards,[copy.deepcopy(row) if r['id']=='NATIVE-173' else r for r in records]
 a.collect_rows=rows
 a.source_link=lambda name,label=None:'['+(label or Path(name).name)+'](<'+link(name)+'>)'
 a.markdown=lambda rows,summary:md(rows,summary).replace('2026-10-13（R6 full128受限采认增量；基础图为2026-10-12）','2026-10-14（同61b128受限补证；基础图与旧证据保留）')
 def html_final(rows,summary):
  text=html(rows,summary)
  names={e['path'] for r in rows for e in r['evidence']}|{r['path'] for r in consume.read(view/'platform-context.json')}
  mapping=json.dumps({n:link(n) for n in sorted(names)},ensure_ascii=False).replace('<','\\u003c')
  text,n=re.subn(r'const evidenceLinks=\{[^\n]*\};',lambda m:'const evidenceLinks='+mapping+';',text)
  consume.need(n==1,'frozen logical-link seam changed')
  return text.replace('2026.10.13 · R6 FULL128','2026.10.14 · FINAL61B SCOPED128')
 a.html_atlas=html_final
 return a
def english_html(zh,row,binding):
 presentation=module(PARENT/'readable.py','frozen_english_presentation')
 marker='<script id="data" type="application/json">'
 first,rest=zh.split(marker,1);payload,last=rest.split('</script>',1)
 first,last=presentation.english_shell(first,last)
 translated=presentation.english_presentation(row)
 translated['oh_tested']+=' Actual61b/boot086d same-board128 scoped startup evidence added; OH still only6.1.0.31.'
 translated['route_generation']+=' Actual61b eight windows,121t10+7t20,256 raw captures and two original review routes. This update does not sign V2 or register/freeze the API.'
 translated['validations'][-1]['result']='Actual outer '+binding['authority']['status']+': same61b128 scoped startup nonregression only. '+binding['facts_total']+'. Original detach did not capture the global driver exit code (null/unknown). Original128 completion, observed driver exit, eight-window real return codes and three identity PASS receipts per window establish completion. Preserve all raw NOT_LIT/loading/empty states, foreground_unconfirmed and failed/crashed app statuses. Not full functionality.'
 # Parent English captions cover its last four historical receipts only.
 previous=consume.read(PARENT/'row-r6.json')
 old_display=presentation.english_presentation(previous)
 translated['evidence']=old_display['evidence']+copy.deepcopy(binding['evidence'])
 translated['gaps']=[g.replace('Protected61b unseal and final sameboard acceptance still pending.','Same61b128 has scoped startup acceptance; final sealing is separate.') for g in translated['gaps']]
 translated['gaps'].append('Actual61b scope remains startup/screenshots only; no general feature or V2/API freeze claim. Original outer limits: '+'; '.join(binding['authority']['limitations']))
 token='for(const r of rows){const d='
 consume.need(last.count(token)==1,'frozen English presentation seam changed')
 data=json.dumps(translated,ensure_ascii=False).replace('<','\\u003c')
 last=last.replace(token,'const englishNative173='+data+";for(const canonical of rows){const r=canonical.id==='NATIVE-173'?Object.assign({},canonical,englishNative173):canonical;const d=")
 return first+marker+payload+'</script>'+last
def invariant(rows,row):
 previous={r['id']:r for r in old_rows()};current={r['id']:r for r in rows}
 consume.need(len(rows)==len(current)==315 and set(current)==set(previous),'315 ID membership changed')
 consume.need(all(current[k]==v for k,v in previous.items() if k!='NATIVE-173'),'original314 field drift')
 changed={k for k in row if row[k]!=previous['NATIVE-173'][k]}
 consume.need(changed==consume.FIELDS,'only five evidence fields may change')
 consume.need(row['validations'][:-1]==previous['NATIVE-173']['validations'],'old validation rewritten')
 consume.need(row['evidence'][:len(previous['NATIVE-173']['evidence'])]==previous['NATIVE-173']['evidence'],'old evidence rewritten')
 consume.need(row['members']==previous['NATIVE-173']['members'] and row['frozen_ids']==[],'native family/registration expanded')
 consume.need(row['android_tested']==row['android_api_level']==row['apk_target_sdk']=='unknown','Android range promoted')
 consume.need(sum(v['level']=='functional' for v in row['validations'])==sum(v['level']=='functional' for v in previous['NATIVE-173']['validations']),'startup promoted to functional')
 return sorted(changed)
def link_check(view,rows):
 names={e['path'] for r in rows for e in r['evidence']}|{r['path'] for r in consume.read(view/'platform-context.json')}
 origin=PurePosixPath('/WORKSPACES/westlake-harness/benchmark/2026-10-14-api-progress-final61b/views')
 for name in names:
  logical=PurePosixPath(posixpath.normpath(str(origin/link(name))))
  consume.need(str(logical).startswith('/WORKSPACES/'),'link escapes WORKSPACES')
  consume.need((WS/str(logical).removeprefix('/WORKSPACES/')).is_file(),'logical cross-tree evidence link missing: '+name)
 return len(names)
def render(out,binding):
 view=out/'views';view.mkdir(parents=True,exist_ok=False)
 for name in ['row-template.json','curation.json','platform-context.json']:shutil.copy2(PARENT/'views'/name,view/name)
 row=make_row(binding);a=setup(view,row);summary=a.build();summary['date']='2026-10-14'
 summary.update(actual61b_evidence=True,api_frozen=False,v2_signed_by_this_table=False)
 data=consume.read(view/'api-progress.json');data['metadata']=summary;write(view/'api-progress.json',data);write(view/'results.json',summary)
 (view/'API-PROGRESS.zh.md').write_text(a.markdown(data['rows'],summary));(view/'index.html').write_text(a.html_atlas(data['rows'],summary))
 (view/'index.en.html').write_text(english_html((view/'index.html').read_text(),row,binding))
 write(out/'binding.json',binding);return check_output(out,binding)
def check_output(out,binding):
 view=out/'views';row=make_row(binding);a=setup(view,row);result=a.check();result.update(a.negative_checks())
 data=consume.read(view/'api-progress.json');result['changed_fields']=invariant(data['rows'],row)
 zh=(view/'index.html').read_text();en=(view/'index.en.html').read_text()
 consume.need(en==english_html(zh,row,binding),'English regeneration drift')
 marker='<script id="data" type="application/json">'
 consume.need(en.split(marker,1)[1].split('</script>',1)[0]==zh.split(marker,1)[1].split('</script>',1)[0],'bilingual canonical payload differs')
 result.update(old_rows_unchanged=314,links_each_language=link_check(view,data['rows']),device_calls=0,api_frozen=False,v2_signed_by_this_table=False,authority_sha256=binding['authority_pin']['sha256'])
 return result
def build(request,out):
 binding=consume.consume(consume.read(request)) # Reject incomplete/fixture inputs BEFORE output creation.
 out=out.resolve();consume.need(out.is_relative_to(HERE) and out!=HERE,'output must be a new child of this independent packet')
 consume.need(not out.exists(),'fresh output required')
 with tempfile.TemporaryDirectory(prefix='api-final61b-',dir=HERE) as temp:
  staging=Path(temp);result=render(staging,binding);write(staging/'verification.json',result)
  shutil.copy2(request,staging/'request.actual.json');staging.rename(out)
 return result
def core_check():
 consume.base()
 import unittest,test_increment
 result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(test_increment))
 consume.need(result.wasSuccessful(),'offline consumer tests failed')
 published=[p for p in HERE.iterdir() if p.is_dir() and (p/'request.actual.json').is_file()]
 actual=[]
 for out in published:
  binding=consume.consume(consume.read(out/'request.actual.json'))
  actual.append(check_output(out,binding))
 return {'status':'ACTUAL_SAME61B_SCOPED_EVIDENCE_VERIFIED' if actual else 'CORE_READY_WAITING_ACTUAL_OUTER','actual61b_bound':bool(actual),'actual_outputs_checked':len(actual),'tests':result.testsRun,'device_calls':0,'formal_views_created':False}
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['build','check']);parser.add_argument('--request',type=Path);parser.add_argument('--out',type=Path);args=parser.parse_args()
 try:
  if args.command=='build':consume.need(args.request is not None and args.out is not None,'actual --request and fresh --out required');result=build(args.request,args.out)
  elif args.request is None and args.out is None:result=core_check()
  else:
   consume.need(args.request is not None and args.out is not None,'both --request and --out required');binding=consume.consume(consume.read(args.request));result=check_output(args.out,binding)
  print(json.dumps(result,ensure_ascii=False));return 0
 except (ValueError,AssertionError,OSError,KeyError,TypeError) as exc:print('REJECT '+str(exc),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
