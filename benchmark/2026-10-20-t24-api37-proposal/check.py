"""Validate additive proposal through an exact copy of the canonical renderer."""
import argparse,csv,hashlib,json,shutil,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();m=a.source_root.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
b=json.loads((P/'preimage.json').read_text());c=m/b['canonical']
def guard():
 for r in b['files']:assert h(m/r['path'])==r['sha256'],r['path']
guard();old=json.loads((c/'observations.json').read_text());assert len(old['rows'])==36 and old['historical_rows']==315
row=json.loads((P/'proposal.json').read_text());new=json.loads(json.dumps(old));new['rows'].append(row)
assert new['rows'][:36]==old['rows'] and len(new['rows'])==37
assert row['build']==[] and row['frozen'] is False and row['kind'].startswith('Android reference')
(out/'observations.json').write_text(json.dumps(new,ensure_ascii=False,indent=2)+'\n');shutil.copyfile(c/'render.py',out/'render.py');assert h(out/'render.py')==h(c/'render.py')
argv=['python3',str(out/'render.py'),'--source-root',str(m)];(out/'argv.json').write_text(json.dumps(argv)+'\n');r=subprocess.run(argv,capture_output=True,timeout=60)
for suffix,data in [('stdout',r.stdout),('stderr',r.stderr),('rc',(str(r.returncode)+'\n').encode())]:(out/suffix).write_bytes(data)
assert r.returncode==0,r.stderr
rows=list(csv.DictReader((out/'observations.csv').open(encoding='utf-8-sig')));assert len(rows)==37
for left,right in zip(rows,new['rows']):
 for k,v in right.items():assert (json.loads(left[k]) if isinstance(v,list) else left[k])==(v if isinstance(v,list) else str(v)),k
assert (out/'index.html').read_text().count('<article>')==37
guard();rr=json.loads((out/'results.json').read_text());result={'status':'PASS_PROPOSAL_ONLY','old36_objects_unchanged':True,'historical315_unchanged':True,'canonical_main_files_unchanged':True,'copied_renderer_sha256':h(out/'render.py'),'rendered_rows':37,'references_verified':rr['references_verified'],'csv_all_fields_equal':True,'html_cards':37,'proposal_runtime_builds':0,'API_implementation_count_increment':0,'OH_pass_increment':0,'device_calls':0,'promotion_requires_outer':True}
(out/'check-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
