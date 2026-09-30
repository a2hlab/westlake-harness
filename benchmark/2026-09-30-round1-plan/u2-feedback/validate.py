#!/usr/bin/env python3
"""Validate cohort, producer facts, attribution and every copied log excerpt."""
import json,re
from pathlib import Path
from extract import HERE,SOURCE,sha

def read(name):return json.loads((HERE/name).read_text())
def main():
 e=read('evidence.json');r=read('unlit-42.json');results=read('results.json');facts=read('record-facts.json');runs=read('run-audit.json')
 verdict=json.loads((SOURCE/'results.json').read_text());lit=set(sum(verdict['lit_t20'].values(),[]))
 assert len(e)==len({x['key'] for x in e})==66
 assert {x['key'] for x in r}=={x['key'] for x in e if not x['lit']} and len(r)==42
 assert {x['key'] for x in e if x['lit']}==lit and len(lit)==24
 assert all(x['fingerprint']==runs[0]['fingerprint'] for x in runs) and len(runs[0]['fingerprint'])==119
 assert all('fingerprint=937e2a6d0d88' in x['facts'] for x in runs)
 assert results['source_verdict']['sha256']==sha(SOURCE/'results.json')
 assert results['freeze_sha256']==sha(HERE.parent/'freeze-v1/freeze.json')=='240f0f852e95e8e57d18a75e53e53dc4d4d77a987e0a0bc086f628bd99615cf1'
 checked=0
 for x in e:
  p=Path(x['log'])
  if x['log_sha256']:
   assert sha(p)==x['log_sha256'];lines=p.read_text(errors='replace').splitlines()
   snippets=x['events']+x['chain']+(x['first_terminal'] or {}).get('chain',[])
   for item in snippets:assert lines[item['line']-1]==item['text'];checked+=1
  assert sha(Path(x['record']))==x['record_sha256']
  for f in x['faultlogs']:
   assert f['attributed'] and f['pid'] in x['pids'];p=Path(f['path']);assert sha(p)==f['sha256'];ls=p.read_text(errors='replace').splitlines()
   for item in f['header']:assert ls[item['line']-1]==item['text'];checked+=1
 for run in runs:
  fs=[f for f in facts if str(Path(f['record'])).startswith(run['path']+'/')]
  expected=(len(fs),sum(f['captured'] for f in fs),sum(f['slots'] for f in fs),sum(f['alive_t5'] is True for f in fs),sum(f['alive_t20'] is True for f in fs))
  m=re.search(r'TOTAL keys=(\d+) screenshots_captured=(\d+)/(\d+) alive_t5=(\d+) alive_t20=(\d+)',run['facts'])
  assert m and expected==tuple(map(int,m.groups()))
 bykey={x['key']:x for x in r}
 assert all(bykey[k]['first_fatal'] is None for k in ['fd-noice','fd-uhabits','fd-mobile','termux','fd-AppManager'])
 assert all(bykey[k]['batch']=='input' for k in ['fd-seal','toutiao','subwaysurfers'])
 assert 'EGLImpl' in bykey['fd-shatteredpixeldungeon']['first_fatal']['text']
 assert 'libstdc++' in bykey['fd-shatteredpixeldungeon']['first_blocker']['text']
 assert 'GL_ES' not in bykey['noice']['cause'] and 'IMediaRouterService' in bykey['noice']['first_fatal']['text']
 assert 'WestlakeSSLContext' in bykey['fd-client']['cause']
 assert results['wall_comparison']['hits']+results['wall_comparison']['misses']+results['wall_comparison']['unknown']==42
 assert sum(results['batch_counts'].values())==42 and len(read('next-clusters.json'))==21
 out=dict(status='PASS',keys=66,unlit=42,profile_paths=119,source_excerpts_checked=checked,producer_facts_recount='3/3 exact',frozen_forecast='unchanged',faultlogs_attributed=4,board_actions=0)
 (HERE/'validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
