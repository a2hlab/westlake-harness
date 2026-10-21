#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent
R=D.parents[3]
def main():
 rows=json.loads((D/'input-sha.json').read_text())
 for r in rows:
  p=Path(r['path'].replace('$REPO',str(R)).replace('$WORKSPACES',str(R.parent)).replace('$HOME',str(Path.home())))
  assert p.is_file(),str(p)
  assert p.stat().st_size==r['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],str(p)
 i=Path.home()/'.local/share/westlake/commercial-game-20261021/g28-window01/game-ui';ls=(i/'hilog.txt').read_text().splitlines()
 for n,needle in [(3259,'s=_ctype_'),(3260,'Unable to find yuanshen'),(3261,'westlake.anl.app.14857.3'),(3671,'nativeRestartActivityIndicator'),(3722,'exit with code:1')]:assert needle in ls[n-1] and '14857' in ls[n-1]
 assert not any('14857' in s and '__register_atfork' in s for s in ls)
 m=json.loads((D/'maps-excerpts.json').read_text());assert m['read_rcs']==[0,0,0]
 for s in ['before','after']:assert (m[s]['pid'],m[s]['ppid'],m[s]['birth'])==(14857,12781,1768375)
 r=json.loads((D/'results.json').read_text());assert not r['runtime_pass'] and r['maps']['winner']=='UNKNOWN'
 print(json.dumps({'status':'PASS_STATIC_EVIDENCE','input_refs':len(rows),'runtime_provider_winner':'UNKNOWN'}))
if __name__=='__main__':main()
