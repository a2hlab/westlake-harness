#!/usr/bin/env python3
"""Check actual rendered hrefs; simulate only in T0 or audit an actual MAIN landing."""
import argparse,json,re,shutil,tempfile
from pathlib import Path
import generate as g

PACKAGE='benchmark/2026-10-14-api-source-delivery'

def expected_refs(view):
 data=g.read(view/'api-progress.json');summary=g.read(view/'source-delivery.json')
 pins=dict(summary['known_source_build_refs'])
 for row in data['rows']:
  for ref in row['evidence']:pins[ref['path']]=ref['sha256']
 for ref in g.read(view/'platform-context.json'):pins[ref['path']]=ref['sha256']
 pins['recipes/recipes.json']=g.sha(view/'recipes/recipes.json')
 return pins

def validate(view):
 """The origin is the supplied real physical view directory, never a fixed logical path."""
 view=Path(view).resolve();pins=expected_refs(view);receipts=[];maps=[]
 canonical=g.read(view/'api-progress.json')['rows']
 publisher_urls=0
 for row in canonical:
  audits=row['source_master_audit']+([row['build_entry_master_audit']] if row['build_entry_master_audit'] else [])
  for audit in audits:g.validate_publisher_url(audit);publisher_urls+=audit['master_url'] is not None
 for language in ('index.html','index.en.html'):
  text=(view/language).read_text()
  match=re.search(r'const evidenceLinks=(\{[^\n]*\});',text)
  g.need(match is not None,'rendered evidenceLinks missing')
  links=json.loads(match.group(1));g.need(set(links)==set(pins),'rendered link membership drift')
  maps.append(links)
  marker='<script id="data" type="application/json">'
  payload=json.loads(text.split(marker,1)[1].split('</script>',1)[0])
  g.need(payload['rows']==canonical,'rendered bilingual canonical rows differ')
  for name,href in sorted(links.items()):
   g.need(not href.startswith(('http:','https:','file:','javascript:')),'local pin has nonphysical href')
   path=(view/href).resolve()
   g.need(path.is_file() and g.sha(path)==pins[name],'physical rendered link SHA mismatch: '+name)
   receipts.append({'language':language,'name':name,'href':href,'physical_target':str(path),'sha256':pins[name]})
 g.need(maps[0]==maps[1],'bilingual evidenceLinks drift')
 md=(view/'API-PROGRESS.zh.md').read_text();md_receipts=[]
 for href in re.findall(r'\]\(<([^>]+)>\)',md):
  path=(view/href).resolve();g.need(path.is_file(),'Markdown physical link missing: '+href)
  md_receipts.append({'href':href,'physical_target':str(path),'sha256':g.sha(path)})
 return {'status':'PHYSICAL_LINKS_VERIFIED','physical_views':str(view),'rows':315,'links_per_language':len(pins),'markdown_links':len(md_receipts),'html_links':receipts,'markdown':md_receipts,'publisher_repository':g.PUBLISH_REPOSITORY,'publisher_branch':g.PUBLISH_BRANCH,'master_urls_checked':publisher_urls,'device_calls':0,'source_complete_claim':False}

def simulate(view):
 """Copy the new packet at exact final directory depth; existing MAIN files stay read-only."""
 with tempfile.TemporaryDirectory(prefix='landing-simulation-',dir=g.HERE) as temp:
  ws=Path(temp)/'workspaces';ws.mkdir();main=ws/'westlake-harness';main.mkdir()
  for child in g.WS.iterdir():
   if child.name!='westlake-harness':(ws/child.name).symlink_to(child,target_is_directory=child.is_dir())
  for child in g.MAIN.iterdir():
   if child.name not in ('benchmark','.git'):(main/child.name).symlink_to(child,target_is_directory=child.is_dir())
  bench=main/'benchmark';bench.mkdir()
  for child in (g.MAIN/'benchmark').iterdir():
   if child.name!=Path(PACKAGE).name:(bench/child.name).symlink_to(child,target_is_directory=child.is_dir())
  packet=main/PACKAGE;packet.mkdir()
  existing=g.MAIN/PACKAGE
  if existing.exists():
   for child in existing.iterdir():
    if child.name not in ('views','evidence'):(packet/child.name).symlink_to(child,target_is_directory=child.is_dir())
  shutil.copytree(view,packet/'views');(packet/'evidence').mkdir()
  if (existing/'evidence').exists():
   for child in (existing/'evidence').iterdir():(packet/'evidence'/child.name).symlink_to(child,target_is_directory=child.is_dir())
  for alias in g.read(g.HERE/'historical-aliases.json').values():
   dest=packet/alias['path'];dest.parent.mkdir(parents=True,exist_ok=True)
   if dest.is_symlink():dest.unlink()
   shutil.copy2(g.HERE/alias['path'],dest)
  result=validate(packet/'views');result.update(mode='ISOLATED_PHYSICAL_LANDING_SIMULATION',actual_main_written=False,final_relative_path=PACKAGE+'/views')
  return result

def main():
 parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('simulate','actual'));parser.add_argument('--views',type=Path,default=g.HERE/'views');parser.add_argument('--receipt',type=Path);a=parser.parse_args()
 try:
  if a.receipt:g.need(a.receipt.resolve().is_relative_to(g.HERE),'receipt must remain in T0 packet')
  if a.mode=='actual':
   g.need(a.views.resolve()==(g.MAIN/PACKAGE/'views').resolve(),'actual audit requires the real MAIN publication directory')
   result=validate(a.views);result.update(mode='ACTUAL_MAIN_PHYSICAL',actual_main_written=False)
  else:result=simulate(a.views)
  if a.receipt:g.write(a.receipt,result)
  print(json.dumps({k:v for k,v in result.items() if k not in ('html_links','markdown')},ensure_ascii=False));return 0
 except (ValueError,OSError,KeyError,TypeError) as exc:print('REJECT '+str(exc));return 2
if __name__=='__main__':raise SystemExit(main())
