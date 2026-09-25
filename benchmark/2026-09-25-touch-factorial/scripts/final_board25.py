from run25 import *
import hashlib
origin=R/'offline-fresh-2';d=json.loads((origin/'device-report.json').read_text());runtime=d['runtime']
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
# Only this task's still-running forwarder, identified by its deployment executable.
raw=dev('pidof touchfwd; true')
for p in raw.split():
 if p.isdigit() and d['stage'] in dev('readlink /proc/'+p+'/exe'):
  dev('kill '+p)
status=dev('iptables -S OUTPUT; ip6tables -S OUTPUT; ifconfig wlan0; ps -ef | grep -E "appspawn-x|article.news|touchfwd"; df -k /data')
(R/'final-board-state.txt').write_text(status)
refs=dev('cat /proc/[0-9]*/mountinfo 2>/dev/null | grep '+pathlib.Path(runtime).name,120)
(R/'final-runtime-references.txt').write_text(refs)
assert not refs.strip(),refs
assert 'touch25' not in status,status
print('PASS runtime',result['count'],'hashes; no task namespace or network rule remains')
