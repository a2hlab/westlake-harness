#!/usr/bin/env python3
"""Demo-only adapter: install once, then master bms_batch launch-only captures.
No runtime replacement. Empty first screens get no_tap_map and no tree/input.
"""
import argparse,hashlib,importlib.util,json,os,shlex,sys,time,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',str(HERE.parents[3])))
MASTER=WS/'westlake-harness'
sp=importlib.util.spec_from_file_location('master_batch',MASTER/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py');b=importlib.util.module_from_spec(sp);sp.loader.exec_module(b)

def tier_seconds(entries, path, expected_sha):
 raw=Path(path).read_bytes()
 if not expected_sha or hashlib.sha256(raw).hexdigest()!=expected_sha:raise ValueError('approved shot tier SHA drift')
 rows={r['key']:r for r in json.loads(raw)['apps']};seconds=[]
 for entry in entries:
  row=rows.get(entry['key'])
  if not row or row.get('apk_sha256')!=entry['apk_sha256'] or row.get('package')!=entry['package']:raise ValueError('shot tier pinned app mismatch: '+entry['key'])
  value=row['screenshot_seconds']
  if value not in (10,20):raise ValueError('invalid shot tier')
  seconds.append(value)
 return max(seconds)

def launch_args(argv, seconds=20):
 out=[];i=0
 while i<len(argv):
  arg=argv[i]
  if arg=='--reinstall':i+=1;continue
  if arg=='--shots':out+=['--shots','5,'+str(seconds)];i+=2;continue
  out.append(arg);i+=1
 if '--launch-only' not in out:out+=['--launch-only']
 out+=['--wait',str(seconds)]
 return out

def install_one(board,app,root,out,remote):
 out.mkdir(parents=True);r={'key':app['key'],'package':app['package'],'serial':board.serial,'status':'started','screenshots':[],'review':'pending_review','install_only':True}
 try:
  resolved=b.resolve_input(root,app);r.update({k:v for k,v in resolved.items() if k!='apk'})
  _,dump=board.shell('bm dump -n '+shlex.quote(app['package']),required=False)
  try:old=b.parse_bundle(dump,app['package'])
  except b.AppFailure:old=None
  if old and old.get('queryable') and not b.cold_stop(board,app['package'],old['uid'],out,'pre-install'):
   raise b.BatchStop('existing app could not be stopped')
  board.shell('mkdir -p '+shlex.quote(remote));apk=remote+'/original.apk';board.send(resolved['apk'],apk)
  _,read=board.shell('sha256sum '+shlex.quote(apk))
  if not read.split() or read.split()[0]!=resolved['apk_sha256']:raise b.AppFailure('staged APK SHA mismatch')
  rc,text=board.shell('bm install -r -p '+shlex.quote(apk),required=False,timeout=180);(out/'install.txt').write_text(text)
  r['install']={'return_code':rc,'success_text':b.bm_success(rc,text,'install'),'output':str(out/'install.txt')}
  if rc or not r['install']['success_text']:raise b.AppFailure('install failed: '+text.strip())
  rc,dump=board.shell('bm dump -n '+shlex.quote(app['package']),required=False);(out/'bundle.txt').write_text(dump);r['bms']=b.parse_bundle(dump,app['package'])
  if rc or not r['bms']['queryable']:raise b.AppFailure('BMS readback failed')
  if not b.cold_stop(board,app['package'],r['bms']['uid'],out,'post-install'):raise b.BatchStop('post-install cleanup refused')
  r['status']='installed'
 except b.BatchStop as e:r.update(status='batch_interrupted',error=str(e));raise
 except (b.AppFailure,OSError,ValueError,KeyError) as e:r.update(status='app_failed',error=str(e))
 finally:r['finished_at']=time.time();b.save(out/'record.json',r)
 return r


def install_ability_overrides(pins):
 original=b.desktop_launch
 def launch(board,app,remote,out,record,pages=10):
  pin=pins.get(record['key'])
  if not pin:return original(board,app,remote,out,record,pages)
  if any(app.get(k)!=pin[k] for k in ['package','apk_sha256']) or app.get('launch_activity')!=pin['ability'] or not record['bms']['queryable'] or record['bms']['desktop_activity']!=pin['ability']:raise b.AppFailure('pinned ability identity mismatch')
  raw=(out/'bundle.txt').read_text();bundle=json.loads(raw[raw.index('{'):])
  abilities=[a for m in bundle['hapModuleInfos'] for a in m.get('abilityInfos',[]) if a.get('name')==pin['ability']]
  if len(abilities)!=1 or abilities[0].get('enabled') is not True or abilities[0].get('visible') is not True:raise b.AppFailure('one enabled visible pinned ability required')
  record.update(launch_method='ability-fallback',clicked=False,aa_start_attempted=True,fallback_reason='outer-authorized: exact desktop icon absent in capture-01')
  rc,text=board.shell('aa start -b '+shlex.quote(pin['package'])+' -a '+shlex.quote(pin['ability']),required=False)
  (out/'aa-start.txt').write_text(text);wall=time.time();mono=time.monotonic()
  record.update(aa_start_rc=rc,aa_start_output=text,aa_start_returned_at=wall,clicked_at=wall,click_monotonic=mono,capture_clock_origin='aa-start-success-return');b.save(out/'record.json',record)
  if rc!=0 or 'start ability successfully' not in text.lower():raise b.AppFailure('ability start unsuccessful: '+text)
  board.shell('power-shell timeout -o 86400000',required=False)
 b.desktop_launch=launch
 return original

def main(argv=None):
 argv=list(sys.argv[1:] if argv is None else argv)
 mode=os.environ.get('DEMO_T3_MODE','launch')
 if mode=='launch':
  # The current plans remain t20. Only an outer-approved later plan may set 10.
  seconds=int(os.environ.get('DEMO_T3_SECONDS','20'))
  entries=b.load_apps(Path(argv[argv.index('--manifest')+1]),'all',argv[argv.index('--keys')+1])
  index=json.loads(Path(os.environ['DEMO_INSTALL_INDEX']).read_text())
  for entry in entries:
   proof=index.get(entry['key'])
   if not proof or proof.get('apk_sha256')!=entry['apk_sha256'] or not proof.get('success'):
    root=Path(argv[argv.index('--out')+1])/time.strftime('%Y%m%dT%H%M%S')/'61b0657200000000000000000324012c';folder=root/entry['key'];folder.mkdir(parents=True)
    r=dict(entry,status='app_failed',error='Install-once failed or unverified; do not launch stale installed bytes',install=proof,screenshots=[],finished_at=time.time(),review='pending_review')
    b.save(folder/'record.json',r);b.save(root/'summary.json',{'records':[r]});b.write_facts(root);return 1
  tiers=os.environ.get('DEMO_SHOT_TIERS')
  if tiers:seconds=tier_seconds(entries,tiers,os.environ.get('DEMO_SHOT_TIERS_SHA'))
  pins=json.loads(os.environ.get('DEMO_ABILITY_PINS','{}'))
  if pins:install_ability_overrides(pins)
  rc=b.main(launch_args(argv,seconds))
  if '--out' in argv:
   root=Path(argv[argv.index('--out')+1]);manifest=Path(argv[argv.index('--manifest')+1]);entries={a['key']:a for a in json.loads(manifest.read_text())['apps']}
   for p in root.glob('*/*/*/record.json'):
    r=json.loads(p.read_text());a=entries.get(r['key'],{})
    if a.get('needs_first_tap'):r['demo_interaction']={'status':'no_tap_map','actions':[],'tree_read':False,'authority':'outer ACK(91) 2026-10-09 21:55'}
    r['demo_capture_seconds']=seconds;b.save(p,r)
  return rc
 ap=argparse.ArgumentParser();ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--input-root',type=Path,required=True);ap.add_argument('--keys',required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--serial',required=True);ap.add_argument('--lane',required=True);ap.add_argument('--stop-new-keys-at',type=float);a,extra=ap.parse_known_args(argv)
 if a.serial!='61b0657200000000000000000324012c':raise SystemExit('61b only')
 run_id=time.strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8];root=a.out/run_id/a.serial;root.mkdir(parents=True);commands=root/'commands';commands.mkdir()
 board=b.Board(a.serial,'hdc',str(WS/'westlake-inputs/tools/board_note.sh'),a.lane,commands);board.ready();settings=b.preflight(board,root);b.runtime_fingerprint(board,root);b.boot_image_fingerprint(board,root);entries=b.load_apps(a.manifest,'all',a.keys);records=[]
 try:
  for i,app in enumerate(entries):
   if a.stop_new_keys_at is not None and time.time()>=a.stop_new_keys_at:break
   records.append(install_one(board,app,a.input_root,root/app['key'],f'/data/local/tmp/demo-install-{run_id}/{app["key"]}'))
   b.save(root/'summary.json',{'records':records,'review':'pending_review'});print(app['key'],records[-1]['status'],flush=True)
 finally:
  b.save(root/'summary.json',{'records':records,'review':'pending_review'});b.write_facts(root)
 return 0 if all(r['status']=='installed' for r in records) else 1
if __name__=='__main__':raise SystemExit(main())
