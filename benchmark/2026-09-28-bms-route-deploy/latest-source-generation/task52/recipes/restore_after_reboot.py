from pathlib import Path
import sys,json,time
R=Path(__file__).resolve().parents[5];sys.path.insert(0,str(R/'benchmark/2026-09-28-bms-route-deploy/batch'))
import bms_batch as b
W=R/'bms/src/.work/b6-task52';out=Path.home()/'a2hlab/board/b6-task52-installer/reboot';out.mkdir(parents=True,exist_ok=True)
tools=R.parent/'westlake-inputs/tools';board=b.Board('5ea34a4500000000000000001123012c',str(tools/'hdc_mac.sh'),'mac '+str(tools/'board_note.sh'),'cx-t0',out/('commands-'+str(time.time_ns())));board.ready()
assert board.boot=='42f125dc-5d9e-405e-91b4-0f9e929c3c5f'
mounts=[]
for line in (W/'rollback/shell-mountinfo.txt').read_text().splitlines():
 f=line.split()
 if f[4].startswith('/system') and (f[3].startswith('/pr03-74e6-portable/') or f[3].startswith('/zigzag-apk-lightup/') or f[3].startswith('/local/tmp/b5-alias-')):mounts.append(('/data'+f[3],f[4]))
assert len(mounts)==17,len(mounts)
_,ps=board.shell('ps -A -o PID,PPID,UID,NAME');assert not [x for x in b.processes(ps) if x['name']=='appspawn-x']
_,info=board.shell('cat /proc/self/mountinfo; getenforce');(out/'before.txt').write_text(info)
existing=[('/data'+l.split()[3],l.split()[4]) for l in info.splitlines() if len(l.split())>6 and l.split()[4] in {t for s,t in mounts}]
assert existing==mounts[:7],existing
remaining=mounts[7:]
for s,t in mounts:board.shell('test -e '+s)
expected={
'/system/bin/appspawn-x':'1f6cf53be7b3225a6d0a2b5f66278c32f5d9f5f99a0f56ece3f57a630db4d908',
'/system/lib64/appspawn/libwestlake_android_child.z.so':'0976dee89c0464cd6aeaf7d4c3c4afd1466926b7d69dc8e01d4910f92bf12e40',
'/system/android/framework/oh-adapter-runtime.jar':'250958dc3f133b67fb38c5da3caf81714fd6958e2247556e327d917b1f0d3146',
'/system/android/lib64/liboh_adapter_bridge.so':'84695d62f515cfec6bb317c959ec55b1d5085bf82303f792a764cf549a22267a'}
final_sources={t:s for s,t in mounts}
for t,digest in expected.items():
 _,v=board.shell('sha256sum '+final_sources[t]);assert v.split()[0]==digest
board.shell('begetctl stop_service appspawn-x')
for s,t in remaining:board.shell('mount --bind '+s+' '+t)
_,v=board.shell('sha256sum '+' '.join(expected));assert {l.split()[1]:l.split()[0] for l in v.splitlines()}==expected
(out/'baseline-hashes.txt').write_text(v)
board.shell('begetctl start_service appspawn-x');time.sleep(2)
_,ps=board.shell('ps -A -o PID,PPID,UID,NAME');parents=[x['pid'] for x in b.processes(ps) if x['name']=='appspawn-x' and x['uid']==0];assert len(parents)==1
_,socket=board.shell("stat -c '%a:%u:%g:%C' /dev/unix/socket/AppSpawnX")
if socket!='660:0:6005:u:object_r:appspawn_socket:s0':board.shell('chown 0:6005 /dev/unix/socket/AppSpawnX && chmod 0660 /dev/unix/socket/AppSpawnX && chcon u:object_r:appspawn_socket:s0 /dev/unix/socket/AppSpawnX')
pids=[x['pid'] for x in b.processes(ps) if x['name']=='foundation'];assert len(pids)==1
paths=['/system/lib64/libapk_installer.so','/system/lib64/platformsdk/libapk_installer.so'];paths += [f'/proc/{pids[0]}/root'+p for p in paths]
_,v=board.shell('sha256sum '+' '.join(paths));assert len(v.splitlines())==4 and all(l.split()[0]=='675536e8a43ac747cbffc0e130d5681ba7bcf2bd3fd305f3d0d357ca797a793d' for l in v.splitlines());(out/'installer-hashes.txt').write_text(v)
board.shell('power-shell wakeup');board.shell('uitest uiInput keyEvent Home');board.shell('uitest uiInput swipe 600 1700 600 300');time.sleep(2);board.shell('uitest uiInput keyEvent Home');time.sleep(2)
screen=b.capture(board,'/data/local/tmp/b6-task52-installer-backup/desktop-reboot.jpeg',out/'desktop.jpeg')
b.save(out/'result.json',{'boot_id':board.boot,'parent':parents[0],'foundation':pids[0],'mounts':mounts,'baseline_hashes':expected,'installer_four_hashes':True,'screenshot':screen})
print(json.dumps({'boot':board.boot,'parent':parents[0],'foundation':pids[0],'screen':screen},indent=2))
