"""Offline, exact-evidence reuse of one completed no-placement R2 baseline."""
import argparse, hashlib, json, os
from pathlib import Path
SERIAL='5cd1e3dd00000000000000000923012c'
def need(ok,msg):
 if not ok: raise ValueError(msg)
def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def resolve(p): return Path(os.path.expandvars(str(p))).resolve()
def portable(p):
 p=Path(p).resolve(); ws=resolve(os.environ['WORKSPACES'])
 return '$WORKSPACES/'+str(p.relative_to(ws))
def pin(p): return dict(path=portable(p),sha256=sha(p))
def check(ref):
 p=resolve(ref['path']);need(p.is_file() and sha(p)==ref['sha256'],'evidence SHA drift: '+ref['path']);return p
def files(root):
 paths=sorted(root.rglob('*'));need(not any(p.is_symlink() for p in paths),'symlink in historical run')
 return {str(p.relative_to(root)):sha(p) for p in paths if p.is_file()}
def inspect(request_path, result_path):
 q=read(request_path);root=resolve(q['out']);boot=read(check(q['plan']))['boot_id']
 need(q['serial']==SERIAL,'prior serial')
 need(result_path.resolve()==root.parent/'board-run/board-run-result.json','prior board_run result location')
 result=read(result_path)
 need(result.get('after_lock')==2 and result.get('before_unlock')==0 and result.get('smoke') is None and result.get('shards')==[] and not result.get('before_unlock_error'),'R2 cleanup incomplete/unknown')
 need(read(root/'no-placement.json')==dict(no_transaction_or_intent=True,host_foreground_restored=True,original940_passed=True),'no-placement completion missing')
 forbidden=['transaction.json','intent-*.json','directory-created-*.json','placed*.json','candidate-boot-intent.json','candidate-boot-result.json']
 need(not any(list(root.rglob(pattern)) for pattern in forbidden),'prior placement/boot intent exists')
 for tag in ['baseline-r5','no-placement-r5']:
  r=read(root/(tag+'.json'))
  need(r.get('status')=='PASS' and r.get('passed') is True and r.get('mode')=='live-readonly' and r.get('file_count')==940 and r.get('synthetic') is False,'original R5 not actual PASS: '+tag)
  need(r.get('serial')==SERIAL and r.get('current_boot')==r.get('boot_before')==r.get('boot_after')==boot,'R5 boot/serial mismatch')
  need(r['activation']['binding']==q['activation_binding'],'R5 binding differs')
  checks=r['checks'];need(len(checks)==940 and len({x['target'] for x in checks})==940 and all(x['equal'] is True and x['expected']==x['actual'] for x in checks),'R5 incomplete checks')
 records=list((root/'popup-before').glob('*/*/*/record.json'))
 need(len(records)==len(q['popup_keys'])==5 and {read(p)['key'] for p in records}==set(q['popup_keys']),'five popup membership incomplete')
 for p in records:
  r=read(p);need(r['serial']==SERIAL and r['boot_id']==boot and r['status'] in ('captured','foreground_unconfirmed'),'popup identity/status')
  shots=r['screenshots'];need(len(shots)==3 and {x['scheduled_seconds'] for x in shots}=={5,10,20},'popup screenshot set')
  for row in shots:
   f=resolve(row['path']);need(f.is_relative_to(root) and row['captured'] is True and sha(f)==row['sha256'],'popup screenshot missing/drift')
 smoke=read(root/'baseline-hw-zz/smoke-result.json')
 need(smoke.get('passed') is True and smoke.get('serial')==SERIAL and smoke.get('checks') and all(x['ok'] is True for x in smoke['checks']),'HW/ZZ not PASS')
 # Exact CLI completion receipts distinguish real execution from a summary claim.
 receipts={}
 for tag in ['baseline-r5','popup-before','baseline-hw-zz','apply','no-placement-r5']:
  matches=list(root.glob('hook-*/*-'+tag+'.json'));need(len(matches)==1,'missing/duplicate command receipt: '+tag)
  path=matches[0];r=read(path);argv=r['argv'];need(r['finished']>=r['started'] and r['rc'] in ({0,1} if tag=='popup-before' else {2} if tag=='apply' else {0}),'command failed: '+tag)
  program='batch' if tag=='popup-before' else 'smoke' if tag=='baseline-hw-zz' else 'installer' if tag=='apply' else 'r5'
  need(len(argv)>1 and resolve(argv[1])==check(q['programs'][program]),'command program mismatch: '+tag)
  need(path.with_suffix('.stdout').is_file() and path.with_suffix('.stderr').is_file(),'command raw missing')
  receipts[tag]=r
 need(receipts['baseline-r5']['finished']<=receipts['popup-before']['started'] and receipts['popup-before']['finished']<=receipts['baseline-hw-zz']['started'] and receipts['baseline-hw-zz']['finished']<=receipts['apply']['started'] and receipts['apply']['finished']<=receipts['no-placement-r5']['started'],'baseline/cleanup chronology')
 return q,root,boot

def validate(manifest_path,current_request):
 m=read(manifest_path);need(m['schema']=='boat-r5-resume-baseline/v1' and m['synthetic'] is False,'resume schema')
 request=check(m['prior_request']);result=check(m['board_run_result'])
 prior,root,boot=inspect(request,result)
 expected={k:v for k,v in current_request.items() if k not in {'out','resume_after_baseline'}}
 need({k:v for k,v in prior.items() if k!='out'}==expected,'request differs beyond new output/resume binding')
 need(resolve(current_request['out'])!=root and not resolve(current_request['out']).is_relative_to(root),'fresh independent run required')
 need(m['boot_id']==boot and m['serial']==SERIAL,'resume identity')
 need(files(root)==m['files'],'historical baseline/raw file set or SHA changed')
 return dict(schema='boat-r5-resumed-baseline/v1',prior_request=m['prior_request'],manifest=pin(manifest_path),serial=SERIAL,boot_id=boot,baseline_reused=True,visual_acceptance=False,device_calls=0)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--prior-request',type=Path,required=True);ap.add_argument('--board-run-result',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 try:
  q,root,boot=inspect(a.prior_request,a.board_run_result);need(not a.out.exists(),'fresh output required')
  m=dict(schema='boat-r5-resume-baseline/v1',synthetic=False,serial=SERIAL,boot_id=boot,prior_request=pin(a.prior_request),board_run_result=pin(a.board_run_result),files=files(root))
  a.out.mkdir(parents=True);mp=a.out/'resume-baseline.json';mp.write_text(json.dumps(m,indent=2)+'\n')
  q=dict(q,out=portable(a.out/'run'),resume_after_baseline=pin(mp));validate(mp,q)
  (a.out/'request.json').write_text(json.dumps(q,indent=2)+'\n')
  print(json.dumps(dict(status='PREPARED_NOT_AUTHORIZED',request=pin(a.out/'request.json'),device_calls=0)));return 0
 except (OSError,ValueError,KeyError,TypeError) as e:print('REFUSE '+str(e));return 2
if __name__=='__main__':raise SystemExit(main())
