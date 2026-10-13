#!/usr/bin/env python3
"""Read rendered links from the physical MAIN views directory; never use core.link()."""
import argparse,csv,hashlib,json,os,re,sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',str(HERE.parents[2]))).resolve()
MAIN=WS/'westlake-harness'
FINAL=MAIN/'benchmark/2026-10-14-api-progress-final61b/views'
BASELINE=MAIN/'benchmark/2026-10-13-api-progress-r6-full128/views'
PARENT=BASELINE.parent

def need(ok,message):
 if not ok:raise ValueError(message)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def embedded(text,marker,end):
 need(text.count(marker)==1,'rendered data/link seam missing or duplicated')
 return json.loads(text.split(marker,1)[1].split(end,1)[0])
def evidence_target(name,aliases):
 if name in aliases:return (PARENT/aliases[name]['path']).resolve(strict=True)
 if name.startswith('$WORKSPACES/'):return (WS/name.removeprefix('$WORKSPACES/')).resolve(strict=True)
 need(not Path(name).is_absolute() and '..' not in Path(name).parts,'nonportable evidence name')
 return (MAIN/name).resolve(strict=True)
def verify(view,final=True):
 view=Path(view).resolve(strict=True)
 expected_view=FINAL if final else BASELINE
 need(view==expected_view.resolve(strict=True),'physical published directory differs from exact landing destination')
 data=read(view/'api-progress.json');rows=data['rows']
 need(len(rows)==315 and len({r['id'] for r in rows})==315,'canonical315 missing/duplicate')
 if final:need(data['metadata'].get('actual61b_evidence') is True,'actual final61b build not present')
 aliases=read(PARENT/'historical-evidence-aliases.json')
 named={}
 for row in rows:
  for ref in row['evidence']:
   need(ref['path'] not in named or named[ref['path']]==ref['sha256'],'conflicting evidence SHA')
   named[ref['path']]=ref['sha256']
 for ref in read(view/'platform-context.json'):
  need(ref['path'] not in named or named[ref['path']]==ref['sha256'],'context/evidence SHA conflict')
  named[ref['path']]=ref['sha256']
 languages={};canonical=None
 for name in ('index.html','index.en.html'):
  text=(view/name).read_text();payload=embedded(text,'<script id="data" type="application/json">','</script>')
  need(payload['rows']==rows,'rendered canonical rows differ: '+name)
  if canonical is None:canonical=payload
  else:need(payload==canonical,'bilingual canonical data differs')
  mappings=embedded(text,'const evidenceLinks=',';\nfunction link(')
  need(set(mappings)==set(named),'rendered evidenceLinks membership differs: '+name)
  checked=[]
  for source,relative in sorted(mappings.items()):
   need(isinstance(relative,str) and relative and not Path(relative).is_absolute() and ':' not in relative and '#' not in relative and '?' not in relative,'nonlocal rendered link')
   # This is the actual physical HTML parent, not /WORKSPACES or core origin.
   actual=(view/relative).resolve(strict=True)
   wanted=evidence_target(source,aliases)
   need(actual==wanted and actual.is_file(),'rendered link resolves to wrong physical evidence: '+source)
   need(sha(actual)==named[source],'rendered evidence SHA drift: '+source)
   checked.append({'evidence':source,'rendered_href':relative,'physical_resolved_target':str(actual),'sha256':named[source]})
  languages[name]=checked
 with (view/'api-progress.csv').open(encoding='utf-8-sig',newline='') as stream:
  reader=csv.DictReader(stream);fields=reader.fieldnames;exported=list(reader)
 need(len(exported)==315,'CSV count differs')
 for row,record in zip(rows,exported):
  for key in fields:
   want=json.dumps(row[key],ensure_ascii=False) if isinstance(row[key],(list,dict)) else str(row[key])
   need(record[key]==want,'CSV canonical field differs: '+row['id']+'/'+key)
 md=(view/'API-PROGRESS.zh.md').read_text();md_links=re.findall(r'\]\(<([^>]+)>\)',md)
 for relative in md_links:need((view/relative).resolve(strict=True).is_file(),'physical Markdown link missing')
 return {'status':'ACTUAL_MAIN_PUBLISHED_LINKS_VERIFIED' if final else 'BASELINE_MAIN_PHYSICAL_LINK_CONTROL_ONLY','physical_views':str(view),'canonical_rows':315,'links_each_language':len(named),'Markdown_links_checked':len(md_links),'languages':languages,'actual_final61b_checked':final,'fixed_origin_used':False,'core_generator_imported':False,'device_calls':0}
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--views',type=Path,required=True);parser.add_argument('--baseline-control',action='store_true');parser.add_argument('--receipt',type=Path);args=parser.parse_args()
 try:
  result=verify(args.views,final=not args.baseline_control)
  if args.receipt:
   need(args.receipt.resolve().is_relative_to(HERE) and not args.receipt.exists(),'fresh T0 publication receipt required')
   args.receipt.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
  print(json.dumps({k:v for k,v in result.items() if k!='languages'},ensure_ascii=False));return 0
 except (ValueError,OSError,KeyError,TypeError) as exc:print('REJECT '+str(exc),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
