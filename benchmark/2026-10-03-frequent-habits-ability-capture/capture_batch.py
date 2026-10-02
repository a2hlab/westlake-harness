"""Authorized one-key fallback; all install/capture/cleanup uses master bms_batch."""
import importlib.util,json,sys,time
from pathlib import Path
H=Path(__file__).resolve().parent;W=H.parents[2];M=W/'westlake-harness'
p=M/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'
sys.path.insert(0,str(p.parent));spec=importlib.util.spec_from_file_location('master_bms_batch',p)
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
original=b.desktop_launch
PIN='3b6cb46847c99fb82537e7fa3f0527f4443c544fa8a8839588c5ce32e368b446'
def fallback(board,app,remote,out,record,pages=10):
 try:return original(board,app,remote,out,record,pages)
 except b.AppFailure as exc:
  if str(exc)!='exact desktop icon absent across searched pages':raise
  if not (record['key']=='cv2-com-frequent-habits' and app['package']=='com.frequent.habits' and app['apk_sha256']==PIN and app['launch_activity']=='com.example.MainActivity' and record['bms']['queryable'] and record['bms']['desktop_activity']=='com.example.MainActivity'):raise b.AppFailure('ability fallback identity gate refused') from exc
  raw=(out/'bundle.txt').read_text();bundle=json.loads(raw[raw.index('{'):])
  abilities=[a for m in bundle['hapModuleInfos'] for a in m.get('abilityInfos',[]) if a.get('name')=='com.example.MainActivity']
  if len(abilities)!=1 or abilities[0].get('enabled') is not True or abilities[0].get('visible') is not True:raise b.AppFailure('ability fallback requires one enabled visible pinned ability') from exc
  record.update(launch_method='ability-fallback',clicked=False,aa_start_attempted=True,fallback_reason=str(exc),launch_wrapper_sha256=b.hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
  b.save(out/'record.json',record)
  rc,text=board.shell('aa start -b com.frequent.habits -a com.example.MainActivity',required=False)
  (out/'aa-start.txt').write_text(text)
  returned_wall=time.time();returned_monotonic=time.monotonic()
  record.update(aa_start_rc=rc,aa_start_output=text,aa_start_returned_at=returned_wall,aa_start_return_monotonic=returned_monotonic,click_monotonic=returned_monotonic,clicked_at=returned_wall,capture_clock_origin='aa-start-success-return')
  b.save(out/'record.json',record)
  if rc!=0:raise b.AppFailure('ability fallback aa start nonzero: '+str(rc))
  # Same last-input screen timeout reset as desktop_launch, without label selection.
  board.shell('power-shell timeout -o 86400000',required=False)
b.desktop_launch=fallback
if __name__=='__main__':raise SystemExit(b.main())
