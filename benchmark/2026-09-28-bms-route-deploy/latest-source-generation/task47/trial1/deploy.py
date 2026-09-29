"""Run in VM, locked 5ea only. Stage, switch and roll back one whole generation."""
from pathlib import Path
import hashlib,json,sys,tarfile,time
assert len(sys.argv)==2 and sys.argv[1] in ('up','down'), 'usage: deploy_generation.py up|down'
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R.parent.parent/'batch'))
import bms_batch as b
ROOT=R.parents[3];P=ROOT/'bms/src/.work/b6-real-work/adapter/framework/appspawn-x/security_specialization/stock_child_plugin'
v=json.loads((R/'generation-verification.json').read_text());assert v['status']=='PASS'
closure=json.loads((R/'closure.json').read_text());assert closure['passed']
assert json.loads((R/'closure-negatives.json').read_text())['passed']
gen=v['route_a_input_generation_sha256'];serial='5ea34a4500000000000000001123012c'
remote='/data/local/tmp/b6-generation-'+gen[:12];route='/system/lib64/westlake/route-a/'+gen
out=Path.home()/'a2hlab/board'/('b6-task47-'+gen[:12]);out.mkdir(parents=True,exist_ok=True)
state=out/'deployment.json'
board=b.Board(serial,str(Path(__file__).resolve().parents[4].parent/'westlake-inputs/tools/hdc_mac.sh'),'mac '+str(Path(__file__).resolve().parents[4].parent/'westlake-inputs/tools/board_note.sh'),'cx-t0',out/('commands-'+sys.argv[1]+'-'+str(time.time_ns())))
board.ready();assert board.boot=='56e521b3-858f-4fbf-8e35-daec29525c93'
baseline={'/system/bin/appspawn-x':'1f6cf53be7b3225a6d0a2b5f66278c32f5d9f5f99a0f56ece3f57a630db4d908','/system/lib64/appspawn/libwestlake_android_child.z.so':'0976dee89c0464cd6aeaf7d4c3c4afd1466926b7d69dc8e01d4910f92bf12e40','/system/android/framework/oh-adapter-runtime.jar':'250958dc3f133b67fb38c5da3caf81714fd6958e2247556e327d917b1f0d3146'}
def hashes(paths):
 _,text=board.shell('sha256sum '+' '.join(paths));return {l.split()[-1]:l.split()[0] for l in text.splitlines()}
def parents():
 _,text=board.shell('ps -A -o PID,PPID,UID,NAME');return [r for r in b.processes(text) if r['name']=='appspawn-x']
def stop():
 for pkg in ['org.wikipedia','com.example.helloworld','com.a2hlab.bridge.zigzag']:
  _,text=board.shell('bm dump -n '+pkg);uid=b.parse_bundle(text,pkg)['uid'];assert b.cold_stop(board,pkg,uid,out,'stop-'+pkg+'-'+str(time.time_ns()))
 assert all(r['uid']==0 for r in parents()),'other appspawn children still live'
 board.shell('begetctl stop_service appspawn-x')
 for _ in range(20):
  if not parents():return
  time.sleep(.2)
 raise RuntimeError('appspawn parent did not stop')
def start(expected):
 board.shell('begetctl start_service appspawn-x')
 for _ in range(30):
  rows=parents()
  if len(rows)==1 and rows[0]['uid']==0:
   pid=rows[0]['pid'];time.sleep(1)
   if any(x['pid']==pid for x in parents()):
    assert hashes([f'/proc/{pid}/exe'])[f'/proc/{pid}/exe']==expected
    _,socket_before=board.shell("stat -c '%a:%u:%g:%C' /dev/unix/socket/AppSpawnX")
    expected_socket='660:0:6005:u:object_r:appspawn_socket:s0'
    if socket_before!=expected_socket:
     board.shell('chown 0:6005 /dev/unix/socket/AppSpawnX && chmod 0660 /dev/unix/socket/AppSpawnX && chcon u:object_r:appspawn_socket:s0 /dev/unix/socket/AppSpawnX')
    _,socket_after=board.shell("stat -c '%a:%u:%g:%C' /dev/unix/socket/AppSpawnX")
    assert socket_after==expected_socket
    b.save(out/('socket-identity-'+str(pid)+'.json'),{'before':socket_before,'after':socket_after})
    return pid
  time.sleep(.2)
 raise RuntimeError('new appspawn parent not stable')
def rollback(d):
 stop()
 for target in reversed(d['mounted']):board.shell('umount '+target)
 assert hashes(list(d['before']))==d['before']
 d['rollback_parent']=start(baseline['/system/bin/appspawn-x']);d['rolled_back']=True;b.save(state,d)
 b.save(R/'deployment.json',d)
if sys.argv[1]=='down':
 d=json.loads(state.read_text());assert not d.get('rolled_back');rollback(d);print('whole generation rolled back',d['rollback_parent']);sys.exit()
assert sys.argv[1]=='up' and not state.exists()
baseline.update({'/system/android/lib64/liboh_adapter_bridge.so':'84695d62f515cfec6bb317c959ec55b1d5085bf82303f792a764cf549a22267a','/system/android/lib64/liboh_android_runtime.so':'9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db','/system/lib64/chipset-sdk-sp/libc++.so':'9466fb0d933689533bdf4b4962907f3e0c0970be278bd6ccf703ffa2aea838a6'})
assert hashes(list(baseline))==baseline
payload={}
for f in (P/'out/route-a-generation/providers').glob('*.so'):payload['route/'+f.name]=f
payload['route/libwestlake_android_runtime_provider.so']=P/'out/route-a-generation/libwestlake_android_runtime_provider.so'
payload['runtime/appspawn-x']=P/'out/route-a-generation/appspawn-x-stock'
payload['runtime/libwestlake_android_child.z.so']=P/'out/target/libwestlake_android_child.z.so'
assert b.sha(payload['runtime/appspawn-x'])==v['stock_host_sha256']
assert b.sha(payload['runtime/libwestlake_android_child.z.so'])==v['child_plugin_sha256']
assert b.sha(payload['route/libsigchain.so'])=='6d5d5538ff45c057208186f5cb74b9b5c2402d693aa2756a99327fd4b9f8c400'
for name,path in payload.items():
 member=closure['members'][Path(name).name]
 assert b.sha(path)==member['sha256'], 'artifact changed after closure audit: '+name
pack=ROOT/'bms/src/.work/b6-generation.tar'
with tarfile.open(pack,'w') as t:
 for name,p in payload.items():t.add(p,arcname=name)
board.shell('test ! -e '+remote+' && test ! -e '+route+' && mkdir '+remote)
board.send(pack,remote+'/payload.tar');board.shell('tar -xf '+remote+'/payload.tar -C '+remote)
staged=hashes([remote+'/'+n for n in payload]);assert staged=={remote+'/'+n:b.sha(p) for n,p in payload.items()}
board.shell('find '+remote+' -type f -exec chmod 0644 {} \\; && chmod 0755 '+remote+'/runtime/appspawn-x && chcon -R u:object_r:system_file:s0 '+remote)
mappings=[(remote+'/route',route)]
# Original providers and native roots remain untouched; aliases of the two replaced
# providers must follow the new generation when present.
for name in ['libsigchain.so','libwestlake_android_runtime_provider.so']:
 for directory in ['/system/android/lib64','/system/lib64']:
  target=directory+'/'+name
  rc,_=board.shell('test -f '+target,required=False)
  if rc==0:mappings.append((remote+'/route/'+name,target))
mappings += [(remote+'/runtime/libwestlake_android_child.z.so','/system/lib64/appspawn/libwestlake_android_child.z.so'),(remote+'/runtime/appspawn-x','/system/bin/appspawn-x')]
assert len({t for _,t in mappings})==len(mappings)

before=hashes([t for _,t in mappings[1:]]+list(baseline))
d={'serial':serial,'boot_id':board.boot,'generation':gen,'remote':remote,'before':before,'mounted':[],'payload_sha256':{n:b.sha(p) for n,p in payload.items()},'rolled_back':False}
b.save(state,d)
stop()
try:
 board.shell('mkdir '+route+' && chcon u:object_r:system_file:s0 '+route)
 for source,target in mappings:
  board.shell('mount --bind '+source+' '+target);d['mounted'].append(target);b.save(state,d)
 d['parent_pid']=start(v['stock_host_sha256'])
 d['after']=hashes([t for _,t in mappings[1:]])
 _,maps=board.shell(f'cat /proc/{d["parent_pid"]}/maps');(out/'parent-maps.txt').write_text(maps)
 b.save(state,d);b.save(R/'deployment.json',d);print('whole generation active',gen,d['parent_pid'])
except BaseException:
 rollback(d)
 raise
