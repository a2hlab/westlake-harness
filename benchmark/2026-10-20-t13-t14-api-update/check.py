#!/usr/bin/env python3
"""Read-only additive view checks, reusing prior API packet CSV/link predicates."""
import argparse,csv,hashlib,json,subprocess
from pathlib import Path
from html.parser import HTMLParser
HERE=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,required=True);a=ap.parse_args();m=a.source_root.resolve();base=json.loads((HERE/'base.json').read_text());canonical=Path(base['canonical'])
old=json.loads(subprocess.check_output(['git','-C',str(m),'show',base['base_commit']+':'+str(canonical/'observations.json')]))
new=json.loads((HERE/'observations.json').read_text());assert new['rows'][:25]==old['rows'] and len(new['rows'])==27
assert {k:v for k,v in new.items() if k!='rows'}=={k:v for k,v in old.items() if k!='rows'}
for ref in base['original_files']+base['historical_files']:assert hashlib.sha256((m/ref['path']).read_bytes()).hexdigest()==ref['sha256'],'MAIN advanced: '+ref['path']
refs=0
for row in new['rows']:
 for group in ['source','build','evidence']:
  for item in row[group]:
   p=m/item['path'];assert p.is_file() and not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'];refs+=1
rows=list(csv.DictReader((HERE/'observations.csv').open(encoding='utf-8-sig')));assert len(rows)==27
for x,y in zip(rows,new['rows']):
 for k,v in y.items():assert (json.loads(x[k]) if isinstance(v,list) else x[k])==(v if isinstance(v,list) else str(v)),k
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,t,attrs):
  if t=='a':self.links.extend(v for k,v in attrs if k=='href')
links=Links();links.feed((HERE/'index.html').read_text())
for link in links.links:
 name=link.split('#')[0]
 p=HERE/name if name in ['observations.csv','observations.json'] else m/canonical/name
 assert p.resolve().is_file(),link
assert (HERE/'render.py').read_bytes()==(m/canonical/'render.py').read_bytes()
assert new['historical_rows']==315 and new['historical_semantics_changed'] is False
print(json.dumps({'status':'PASS','rows':27,'references':refs,'html_links':len(links.links),'csv_all_fields_equal':True,'old25_objects_unchanged':True,'original_renderer_unchanged':True,'historical315_modified':False,'device_calls':0,'builds':0}))
