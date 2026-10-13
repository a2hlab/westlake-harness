#!/usr/bin/env python3
"""Original collector recording/consumer ABI preview only. Stops before snapshot conversion."""
import copy,hashlib,importlib.util,json,os,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',str(HERE.parents[2])))
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def expand(p):return Path(str(p).replace('$WORKSPACES',str(WS)))
def checked(ref):
 p=expand(ref['path']);assert sha(p)==ref['sha256'];return p
def load(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class StopBeforeSnapshot(Exception):pass

def main():
 plan=read(HERE/'collector.readonly.disabled.json');inputs=read(HERE/'inputs.json')
 for ref in plan['programs'].values():checked(ref)
 groups=read(checked(plan['groups']));manifest=read(checked(plan['manifest']))
 names=[a['package'] for a in manifest['apps'] if a.get('install') is not False]+plan['extra_packages']
 assert len(names)==len(set(names))==130
 expected=read(HERE/'expected-files.actual-derived.json');assert len(expected)==824 and set(expected)=={p for rows in groups.values() for p in rows}
 observed_path=checked(inputs['live954_observation']);ob=read(observed_path)
 live=read(checked(inputs['live954']));assert live['mode']=='live-readonly' and live['status']=='PASS' and live['file_count']==954
 actual={r['target']:r['actual'] for r in live['checks']};assert set(expected)<=set(actual) and all(actual[p]==h for p,h in expected.items())
 bycommand={}
 for row in ob['commands']:
  assert row['transport_rc']==row['remote_rc']==0
  ref=row['stdout'];raw=observed_path.parent/ref['path'];assert sha(raw)==ref['sha256']
  bycommand.setdefault(row['command'],[]).append(raw.read_bytes())
 collector_path=checked(plan['programs']['collector']);sys.path.insert(0,str(collector_path.parent))
 collector=load(collector_path,'original_v2_collector_recording')
 commands=[];package_paths=[]
 def runner(argv,**kwargs):
  # No process/device call: record actual original argv generation using real prior raw observations.
  assert argv[1:4]==['-t',plan['serial'],'shell']
  cmd=argv[4].split('; seal_read_rc=',1)[0];commands.append(cmd)
  if cmd.startswith('sha256sum '):
   paths=cmd.split()[1:];assert set(paths)<=set(actual)
   raw=('\n'.join(actual[p]+'  '+p for p in paths)+'\n').encode()
  else:
   assert cmd in bycommand,cmd
   raw=bycommand[cmd][-1]
   if cmd.startswith('bm dump -n '):
    identity=collector.adapter.bundle_identity(raw.decode().replace('\r',''),cmd[len('bm dump -n '):]);package_paths.append(identity['apk_path'])
  return SimpleNamespace(returncode=0,stdout=raw.rstrip()+b'\nSEAL_READ_RC=0\n',stderr=b'')
 def disabled_convert(_):raise StopBeforeSnapshot('Recording intentionally ends before any snapshot/errors object is generated')
 collector.adapter.convert=disabled_convert
 with tempfile.TemporaryDirectory(prefix='OFFLINE_RECORDING_NO_LIVE_CAPTURE-') as tmp:
  target=Path(tmp)/'recording'
  try:collector.collect(plan['serial'],groups,names,target,hdc='OFFLINE_NO_DEVICE_EXECUTABLE',runner=runner)
  except StopBeforeSnapshot:pass
  else:raise AssertionError('preview did not stop before snapshot')
  assert not (target/'snapshot.json').exists()
  # The original function has no synthetic arg; simulated capture is private and never admitted/landed.
  private=read(target/'capture.json');private['synthetic']=True;private['mode']='OFFLINE_RECORDING_ONLY_NOT_LIVE';(target/'capture.json').write_text(json.dumps(private))
 assert len(set(package_paths))==130 and len(set(expected)|set(package_paths))==954
 assert commands[0]==commands[-1]=='cat /proc/sys/kernel/random/boot_id'
 assert sum(c.startswith('bm dump -n ') for c in commands)==130 and sum(c.startswith('sha256sum ') for c in commands)==48
 assert len(commands)==181 and all(c.startswith(('cat /proc/sys/kernel/random/boot_id','bm dump -n ','sha256sum ','param get const.ohos.fullname')) for c in commands)
 builder=load(checked(plan['programs']['build_seal']),'original_v2_overlay_checker')
 overlays=read(HERE/'overlays.pending.json')
 route=next(r for r in overlays['items'] if r['id']=='toutiao-route-b')
 historical=read(checked(route['source']))
 assert historical['boot_id']=='9f5af7c8-d359-4c25-99c6-63206b50cf0a' and route['source']['sha256']=='858990f658cbbb44ff00ce7970f6a334b37e227a99d063f25d917d59103c050a'
 assert route['rollback']['sha256']=='5ab07faf40a7c0efdf8263d403700fa28a0e8b62b7262532ba456f4246daeb51';checked(route['rollback'])
 boat=next(r for r in overlays['items'] if r['id']=='boatattack');rollback=read(checked(boat['rollback']))
 disabled=read(checked(rollback['source_plan_disabled']));enabled=read(checked(rollback['actual_plan_enabled']))
 assert {k for k in set(disabled)|set(enabled) if disabled.get(k)!=enabled.get(k)}=={'execution_enabled'}
 assert disabled['execution_enabled'] is False and enabled['execution_enabled'] is True
 for ref in rollback['backup_objects']:checked(ref)
 assert len(rollback['backup_objects'])==28
 assert plan['host_only_new_capture_output'].endswith('/outer/final61b-seal-capture-v2')
 assert 'final61b-approved-execution/final-seal-capture-v2' not in plan['host_only_new_capture_output']
 try:builder.overlay_check(overlays)
 except ValueError as exc:pending_reason=str(exc)
 else:raise AssertionError('pending admission unexpectedly structurally admitted')
 # An in-memory shape-only pin tests existing ABI. It never creates an admitted overlay or snapshot.
 shape=copy.deepcopy(overlays)
 for row in shape['items']:
  f=HERE/('routeb487-admission.pending.json' if row['id']=='toutiao-route-b' else 'boat18-admission.pending.json')
  row['admission']={'path':str(f),'sha256':sha(f)}
 files,hosts=builder.overlay_check(shape)
 assert len(files)==505 and set(files)==set(groups['overlays']) and files=={p:expected[p] for p in groups['overlays']}
 assert set(hosts)==set(plan['extra_packages'])
 for name in ['routeb487-admission.pending.json','boat18-admission.pending.json']:
  d=read(HERE/name);assert d['admitted'] is False and d['approved_by'] is None and d['actual_reviewer'] is None
 result={'status':'ORIGINAL_COLLECTOR_AND_CONSUMER_INTERFACE_READY_DISABLED','recorded_original_collector_device_argv':len(commands),'device_calls_executed':0,'original_code_imports_only':True,'actual_new_capture':None,'snapshot_created':False,'errors_array_created':False,'package_names':130,'unique_file_targets':824,'unique_hashed_targets':954,'hash_batches_20':48,'overlay_members':505,'RouteB_members':487,'Boat_members':18,'pending_admission_refused':pending_reason,'shape_only_overlay_check':'PASS_ABI_NOT_ADMISSION','actual_outer_admission':None,'simulated_capture_retained':False,'commands':commands}
 print(json.dumps({k:v for k,v in result.items() if k!='commands'}));return result
if __name__=='__main__':main()
