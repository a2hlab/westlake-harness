"""Verify actual host receipts and their logs, artifacts, sources; no device access."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
STATUS='OFFLINE_MODULE_ONLY_NOT_DEPLOYABLE'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify(out,receipt=None):
 out=Path(out);r=json.loads((out/'receipt.json').read_text()) if receipt is None else receipt
 assert r['status']==STATUS and r['complete'] is True
 assert r['device_calls']==0 and r['production_binding'] is False and r['shared_library'] is False
 assert set(r['sources'])=={'window_module.c','window_module.h','test_window.c','build_host.py'}
 for n,s in r['sources'].items():assert sha(HERE/n)==s, 'source drift'
 assert r['header_dependencies'] and r['tools']
 for item in [*r['tools'].values(),*r['header_dependencies']]:assert sha(item['path'])==item['sha256'], 'build dependency drift'
 assert set(r['artifacts'])=={'window_module.o','test_window'}
 for n,item in r['artifacts'].items():assert sha(out/n)==item['sha256'] and (out/n).stat().st_size==item['bytes']
 assert set(r['groups']) and set(r['groups'])<={'pair','failures','concurrency'}
 expected=['00-frozen','01-compiler','02-search','03-include-deps','04-link-plan','10-module','11-test']+['20-'+x for x in r['groups']]
 assert [x['name'] for x in r['commands']]==expected, 'actual command sequence'
 for command in r['commands']:
  assert command['rc']==0
  assert set(command['raw'])=={'raw/'+command['name']+suffix for suffix in ['.command.json','.stdout.txt','.stderr','.rc']}
  for n,s in command['raw'].items():assert sha(out/n)==s
  assert (out/'raw'/ (command['name']+'.rc')).read_text()=='0\n'
 for group,item in r['groups'].items():
  p=out/'raw'/('20-'+group+'.stdout.txt');rows=[json.loads(s) for s in p.read_text().splitlines()]
  assert len(rows)==item['cases'] and item['status']=='PASS' and sha(p)==item['journal_sha256']
  assert len({x['case'] for x in rows})==len(rows) and all(x['status']=='PASS' and isinstance(x['journal'],list) for x in rows)
  assert len(rows)=={'pair':7,'failures':34,'concurrency':8}[group]
 return r
