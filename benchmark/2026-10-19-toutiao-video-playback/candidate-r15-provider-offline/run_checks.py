#!/usr/bin/env python3
"""Each Rust selector executes the real build/oracle in a fresh persistent OUT."""
import json, subprocess, sys, time
from pathlib import Path
from build import HERE, ROOT, sha
from verify import verify, negative_checks

def main():
 group=sys.argv[1] if len(sys.argv)==2 else ''
 if group not in ['pair','layout','failures','concurrency','receipt']:raise SystemExit('unknown group')
 out=HERE/'.private'/('selector-'+group+'-'+str(time.time_ns()));out.mkdir(parents=True,exist_ok=False)
 def build(mode,g):
  target=out/mode;argv=[sys.executable,str(HERE/'build.py'),'--mode',mode,'--group',g,'--out',str(target),'--source-repo',str(ROOT)]
  (out/(mode+'.command.json')).write_text(json.dumps(argv,indent=2)+'\n')
  with (out/(mode+'.stdout.txt')).open('wb') as so,(out/(mode+'.stderr')).open('wb') as se:rc=subprocess.run(argv,stdout=so,stderr=se,timeout=120).returncode
  (out/(mode+'.rc')).write_text(str(rc)+'\n')
  if rc:raise SystemExit(str(target)+' failed rc='+str(rc))
  return target
 host=build('host','all' if group=='receipt' else group);result={'group':group,'host':verify(host),'receipt_sha256':sha(host/'receipt.json')}
 if group in ['layout','receipt']:
  oh=build('oh','all');result['oh']=verify(oh);result['oh_receipt_sha256']=sha(oh/'receipt.json')
  if group=='receipt':result['negative_cases']=negative_checks(host,oh)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
