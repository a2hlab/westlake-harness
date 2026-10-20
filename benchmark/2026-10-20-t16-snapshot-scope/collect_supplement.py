#!/usr/bin/env python3
"""Read the 26 unsupported original5cd targets; no deployment or permission changes."""
import argparse,hashlib,json,re,shlex,subprocess,time
from pathlib import Path
B=Path(__file__).resolve().parent;SERIAL='5cd1e3dd00000000000000000923012c'
def main():
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true')
 for k in ('repo','out'):p.add_argument('--'+k,type=Path)
 for k in ('hdc','boot','holder'):p.add_argument('--'+k)
 a=p.parse_args();targets=json.loads((B/'supplement-targets.json').read_text())
 if not a.execute:print(json.dumps({'device_calls':0,'original_supplement_targets':len(targets),'extra':'compat state'}));return
 assert a.repo and a.out and a.hdc and a.boot and re.fullmatch(r'[a-f0-9-]{36}',a.boot)
 assert a.out.is_absolute() and not str(a.out).startswith(('/tmp/','/private/tmp/'))
 a.out.mkdir(parents=True,exist_ok=False)
 def lockcheck(tag):
  r=subprocess.run(['bash',str(a.repo/'scripts/lab/board_note.sh'),'held',SERIAL],capture_output=True,timeout=10)
  (a.out/(tag+'.stdout')).write_bytes(r.stdout);(a.out/(tag+'.stderr')).write_bytes(r.stderr)
  if a.holder:assert r.returncode==0 and r.stdout.decode().strip()==a.holder,'exact holder'
  else:assert r.returncode==1 and not r.stdout.strip(),'board acquired by another task'
 lockcheck('lock-before')
 cmd='sh -c '+shlex.quote((B/'supplement.sh').read_text())+' t16 '+shlex.quote(a.boot)
 argv=[a.hdc,'-t',SERIAL,'shell',cmd];result={'status':'PARTIAL_UNVERIFIED','argv':argv,'started':time.time(),'boot':a.boot,'targets':len(targets)}
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 with (a.out/'stdout.raw').open('wb') as out,(a.out/'stderr.raw').open('wb') as err:
  try:result['rc']=subprocess.run(argv,stdout=out,stderr=err,timeout=120).returncode
  except subprocess.TimeoutExpired:result.update(rc=None,timed_out=True)
  except OSError as e:result.update(rc=None,error=str(e))
 try:
  raw=(a.out/'stdout.raw').read_bytes();assert result.get('rc')==0 and not result.get('timed_out')
  assert raw.startswith(('T16_SUPPLEMENT_BOOT '+a.boot+'\n').encode()) and raw.endswith(b'T16_SUPPLEMENT_COMPLETE\n')
  for i,row in enumerate(targets):assert raw.count(f'T16_TARGET {i} {row["target"]}\n'.encode())==1
  lockcheck('lock-after');result['status']='SUPPLEMENT_BYTES_COMPLETE'
 except Exception as e:result['error']=str(e)
 result['finished']=time.time();result['raw']={n:{'sha256':hashlib.sha256((a.out/n).read_bytes()).hexdigest(),'bytes':(a.out/n).stat().st_size} for n in ('stdout.raw','stderr.raw')}
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return 0 if result['status']=='SUPPLEMENT_BYTES_COMPLETE' else 1
if __name__=='__main__':raise SystemExit(main())
