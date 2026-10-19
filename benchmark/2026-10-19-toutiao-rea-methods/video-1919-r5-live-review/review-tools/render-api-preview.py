#!/usr/bin/env python3
"""Render an unpublished row5 against exact MAIN refs in an isolated temp tree."""
from pathlib import Path
from html.parser import HTMLParser
import csv,hashlib,io,json,shutil,subprocess,tempfile
P=Path(__file__).resolve().parents[1];R=next(x for x in P.parents if (x/'scripts/lab/run_facts.py').is_file());M=R.parent/'westlake-harness';S=Path.home()/'.local/share/westlake/toutiao-resume-20261019';A=Path('benchmark/2026-10-19-api-progress-update');O=P/'api-preview';O.mkdir(exist_ok=True)
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def w(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
assert json.loads((P/'results.json').read_text())['frozen'] is False
src=S/'video-r5-param-restored';dest=P/'parameter-restored';dest.mkdir(exist_ok=True)
for n in ['result.json','param-before.txt']:(dest/n).write_bytes((src/n).read_bytes())
for idx in ['00006','00007','00010']:
 for f in (src/'commands').glob('command-'+idx+'.*'):
  assert b'/Users/' not in f.read_bytes();out=dest/'commands'/f.name;out.parent.mkdir(exist_ok=True);out.write_bytes(f.read_bytes())
result=json.loads((src/'result.json').read_text());assert result['boot']=='d90678dd-bc14-49b3-a714-a83931b35794'
raw=(src/'commands/command-00007.stdout.txt').read_text();assert 'errNum is:106!' in raw and '__BMS_REMOTE_RC_4e0aeaf791be40da82f6e9f93ed20587__0' in raw
assert json.loads((src/'commands/command-00007.json').read_text())['exit_code']==0
for idx in ['00006','00010']:assert (src/'commands'/('command-'+idx+'.stdout.txt')).read_text().splitlines()[0]==result['boot']
r=json.loads((P/'results.json').read_text());r['parameter_absence_restored']={'status':'VERIFIED_EXACT106','boot':result['boot'],'evidence':'parameter-restored/commands/command-00007.stdout.txt','semantic_result':'NOT_FOUND106','transport_and_remote_rc':0,'boot_before_after_equal':True};r['rollback']='physical restoration reported by outer; final identity/feed/unlock pending';w(P/'results.json',r)
pins=json.loads((P/'source-pins.json').read_text());rows={x['path']:x for x in pins['files']}
for f in src.rglob('*'):
 if f.is_file():
  k='$HOME/'+str(f.relative_to(Path.home()));rows[k]={'path':k,'sha256':h(f),'bytes':f.stat().st_size}
script=S/'video_r5_control.py';assert h(script)=='1ee4cff85024cfbd2c54116d0bbf03585ef97b5f5dec95e0428691f8f9ada3b4';assert b'/Users/' not in script.read_bytes();sout=P/'historical-recipes/video_r5_control.py';sout.parent.mkdir(exist_ok=True);sout.write_bytes(script.read_bytes());k='$HOME/'+str(script.relative_to(Path.home()));rows[k]={'path':k,'sha256':h(script),'bytes':script.stat().st_size};pins['files']=list(rows.values());w(P/'source-pins.json',pins)
base=json.loads((M/A/'observations.json').read_text());assert len(base['rows'])==4;new=json.loads(json.dumps(base));draft=json.loads((P/'api-row5.draft.json').read_text());row=draft['row']
row['status']='诊断未到达消费者；P1=NOT_OBSERVED（收窗未闭合）'
row['deployment']='原r4四件复用，无新二进制；物理原版回滚由外环报告，freshboot d90678dd已实际读回errNum106。最终identity、真实feed、snapshot及UNLOCK待闭合，未发布。'
def ref(path):
 f=R/path if path.startswith(str(P.relative_to(R))) else M/path
 assert f.is_file() and not f.is_symlink();return {'path':path,'sha256':h(f)}
prefix=str(P.relative_to(R))+'/'
param='benchmark/2026-10-19-toutiao-rea-methods/video-1919-r5-param-recovery/'
row['source']=[ref(prefix+'historical-recipes/video_r5_control.py'),ref(param+'source-final.json'),ref(param+'provider-final.json')]
row['build']=[ref('benchmark/2026-10-19-toutiao-rea-methods/video-1919-r4-live-review/archive/build-artifacts-receipt.json')]
row['evidence']=[ref(prefix+x) for x in ['results.json','admission.original.json','first-child-loaded/identity.original.txt','second-child-exited/identity.original.txt','third-child-exited/guardian-excerpt.txt','third-child-exited/screen.jpeg','parameter-restored/commands/command-00007.stdout.txt']]
draft['row']=row;draft['publication_ready']=False;draft['baseline_observations_sha256']=h(M/A/'observations.json');w(P/'api-row5.draft.json',draft);new['rows'].append(row)
with tempfile.TemporaryDirectory(prefix='t4-r5-api-preview-') as tmp:
 root=Path(tmp);target=root/A;target.mkdir(parents=True);shutil.copyfile(M/A/'render.py',target/'render.py');w(target/'observations.json',new)
 for rr in new['rows']:
  for group in ['source','build','evidence']:
   for it in rr[group]:
    f=R/it['path'] if it['path'].startswith(prefix) else M/it['path'];assert h(f)==it['sha256'];t=root/it['path'];t.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,t)
 basehtml=Path('benchmark/2026-10-14-api-source-delivery/views/index.html');(root/basehtml).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(M/basehtml,root/basehtml)
 proc=subprocess.run(['python3',str(target/'render.py')],capture_output=True,text=True);assert proc.returncode==0,proc.stderr
 class Links(HTMLParser):
  def __init__(self):super().__init__();self.hrefs=[]
  def handle_starttag(self,tag,attrs):
   if tag=='a':self.hrefs.extend(v for k,v in attrs if k=='href')
 links=Links();links.feed((target/'index.html').read_text());assert all((target/u.split('#')[0]).is_file() for u in links.hrefs)
 cr=list(csv.DictReader(io.StringIO((target/'observations.csv').read_text(encoding='utf-8-sig'))));assert len(cr)==5
 for a,b in zip(cr,new['rows']):
  for k,v in b.items():assert (json.loads(a[k]) if isinstance(v,list) else a[k])==(v if isinstance(v,list) else str(v)),k
 assert new['rows'][:4]==base['rows']
 for n in ['observations.json','observations.csv','index.html','results.json']:shutil.copyfile(target/n,O/n)
 (O/'renderer.stdout.txt').write_text(proc.stdout);(O/'renderer.stderr.txt').write_text(proc.stderr)
 checks={'token':'video-1919-r5-live-review','status':'DRAFT_ONLY_NOT_PUBLISHED_NOT_FROZEN','original_renderer_sha256':h(M/A/'render.py'),'renderer_rc':proc.returncode,'rows':5,'refs_by_row':[sum(len(rr[g]) for g in ['source','build','evidence']) for rr in new['rows']],'html_links':len(links.hrefs),'all_links_resolved_in_isolated_combined_tree':True,'csv_all_fields_equal':True,'first_four_rows_unchanged':True,'historical315_changed':False,'baseline_input_sha256':h(M/A/'observations.json'),'preview_input_sha256':h(O/'observations.json'),'pending':['final restored identity','feed','snapshot closure','canonical UNLOCK','archive'],'note':'Original renderer run on exact copied MAIN refs plus this unfrozen evidence in temp combined root. Saved HTML is a render preview at intended canonical path, not a published alternate website.'};w(O/'checks.json',checks)
 (O/'README.md').write_text('# Unpublished row5 preview\n\nGenerated with unchanged MAIN renderer in an isolated combined tree. All exact references, HTML links and CSV fields checked. First4 rows and historical315 unchanged. This preview is not frozen, not landed to canonical API and not acceptance: P1 NOT_OBSERVED, no video tap, true consumption not observed, audio unknown. Final recovery feed/identity/snapshot/UNLOCK pending. Saved HTML assumes the canonical API directory after future reviewed integration; do not treat this nested preview as published links.\n')
 print(json.dumps(checks,indent=2))
