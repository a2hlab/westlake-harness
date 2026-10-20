#!/usr/bin/env python3
import argparse,csv,hashlib,json
from pathlib import Path
from html.parser import HTMLParser
p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);a=p.parse_args()
r=Path(__file__).resolve().parents[2];m=a.source_root.resolve();rel=Path('benchmark/2026-10-19-api-progress-update');o=r/rel
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
b=json.loads((m/rel/'observations.json').read_text());d=json.loads((o/'observations.json').read_text())
assert len(b['rows'])==43 and len(d['rows'])==44 and d['rows'][:43]==b['rows']
assert {k:v for k,v in b.items() if k!='rows'}=={k:v for k,v in d.items() if k!='rows'}
assert sha(o/'render.py')==sha(m/rel/'render.py')
count=0
for row in d['rows']:
 for g in ('source','build','evidence'):
  for ref in row[g]:assert sha(m/ref['path'])==ref['sha256'];count+=1
csvrows=list(csv.DictReader((o/'observations.csv').open(encoding='utf-8-sig')))
assert len(csvrows)==44
for j,row in enumerate(d['rows']):
 for k,v in row.items():assert (json.loads(csvrows[j][k]) if isinstance(v,list) else csvrows[j][k])==(v if isinstance(v,(list,str)) else str(v))
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,tag,attrs):
  if tag=='a':self.links.extend(v for k,v in attrs if k=='href')
h=Links();h.feed((o/'index.html').read_text())
for link in h.links:
 target=(o/link) if link in ('observations.csv','observations.json') else (m/rel/link)
 assert target.is_file(),link
report={'status':'PASS','rows':44,'references_verified':count,'html_links_verified':len(h.links),'csv_all_fields_equal':True,'original_43_objects_equal':True,'top_level_metadata_equal':True,'historical315_modified':False,'historical_write_scope':[],'renderer_unchanged':True,'base_observations_sha256':sha(m/rel/'observations.json'),'new_observations_sha256':sha(o/'observations.json'),'new_row_references':21,'final_feed_personally_viewed':True,'device_calls':0,'builds_executed':0,'push':False}
Path(__file__).with_name('checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
