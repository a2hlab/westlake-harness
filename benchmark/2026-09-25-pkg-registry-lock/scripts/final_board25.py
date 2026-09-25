from run25 import *
import hashlib
origin=R/'offline-fresh-1';d=json.loads((origin/'device-report.json').read_text());runtime=d['runtime']
expected=d['source_files'];actual={}
for start in range(0,len(expected),32):
 names=list(expected)[start:start+32]
 raw=dev('sha256sum '+' '.join(shlex.quote(runtime+'/'+n) for n in names),120)
 for l in raw.splitlines():
  if re.match(r'^[0-9a-f]{64} ',l):
   val,path=l.split(None,1);actual[path.removeprefix(runtime+'/')]=val
wanted={n:e['sha256'] for n,e in expected.items()}
result={'count':len(expected),'all_match':actual==wanted,'mismatches':[n for n,v in wanted.items() if actual.get(n)!=v]}
assert result['all_match'],result
(R/'final-runtime-verification.json').write_text(json.dumps(result,indent=2))
network(False)
# Kill only forwarders whose executable belongs to one of this task's deployments.
reports=[json.loads(p.read_text()) for p in R.glob('*/device-report.json')]
stages={x['stage'] for x in reports if 'stage' in x}
raw=dev('pidof touchfwd; true')
for p in raw.split():
 if p.isdigit() and any(stage in dev('readlink /proc/'+p+'/exe') for stage in stages):
  dev('kill '+p)
status=dev('iptables -S OUTPUT; ip6tables -S OUTPUT; ifconfig wlan0; ps -ef | grep -E "appspawn-x|article.news|touchfwd"; df -k /data')
(R/'final-board-state.txt').write_text(status)
all_refs={}
for name in sorted({pathlib.Path(x['runtime']).name for x in reports if 'runtime' in x}):
 refs=dev('cat /proc/[0-9]*/mountinfo 2>/dev/null | grep '+name,120)
 all_refs[name]=refs
 assert not refs.strip(),refs
(R/'final-runtime-references.json').write_text(json.dumps(all_refs,indent=2))
assert 'pkg28' not in status,status
print('PASS runtime',result['count'],'hashes; no task namespace or network rule remains')
