from pathlib import Path
import sys,time,json
R=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(R/'benchmark/2026-09-28-bms-route-deploy/batch'))
import bms_batch as b
out=Path.home()/'a2hlab/board/b6-task52-installer';out.mkdir(parents=True,exist_ok=True)
tools=R.parent/'westlake-inputs/tools'
board=b.Board('5ea34a4500000000000000001123012c',str(tools/'hdc_mac.sh'),'mac '+str(tools/'board_note.sh'),'cx-t0',out/('commands-'+str(time.time_ns())))
board.ready()
paths=['/system/lib64/libapk_installer.so','/system/lib64/platformsdk/libapk_installer.so']
old='184d40a56a9116ab87d079413ba31d92e3d45c86a2f9b1088ffc97725ec650f9'
new='675536e8a43ac747cbffc0e130d5681ba7bcf2bd3fd305f3d0d357ca797a793d'
artifact=R.parent/'westlake-harness-label/benchmark/2026-09-28-bms-label-resolve/staging-kit/libapk_installer.b3-build.so'
assert b.sha(artifact)==new
_,before=board.shell('sha256sum '+' '.join(paths));assert all(x.split()[0]==old for x in before.splitlines())
_,ps=board.shell('ps -A -o PID,PPID,UID,NAME');pid=[x['pid'] for x in b.processes(ps) if x['name']=='foundation'];assert len(pid)==1
_,deps=board.shell('ls -l /system/lib64/libc++_shared.so /system/lib64/chipset-sdk-sp/libshared_libz.z.so')
(out/'before.txt').write_text(before+'\n'+ps+'\n'+deps)
remote='/data/local/tmp/b6-task52-installer-backup'
board.shell('test ! -e '+remote+' && mkdir '+remote)
for i,p in enumerate(paths):
 backup=remote+'/'+str(i)+'.so';board.shell('cp -p '+p+' '+backup)
 _,v=board.shell('sha256sum '+backup);assert v.split()[0]==old
 board.receive(backup,out/('original-'+str(i)+'.so'))
board.send(artifact,remote+'/new.so')
_,v=board.shell('sha256sum '+remote+'/new.so');assert v.split()[0]==new
for p in paths:
 temp=p+'.b23-new'
 board.shell('test ! -e '+temp+' && cp '+remote+'/new.so '+temp+' && chown 0:0 '+temp+' && chmod 0755 '+temp+' && chcon u:object_r:system_lib_file:s0 '+temp+' && mv '+temp+' '+p)
_,v=board.shell('sha256sum '+' '.join(paths));assert all(x.split()[0]==new for x in v.splitlines())
board.shell('sync')
board.shell('begetctl stop_service foundation')
time.sleep(2)
board.shell('begetctl start_service foundation')
newpid=None
for _ in range(25):
 time.sleep(1)
 _,ps=board.shell('ps -A -o PID,PPID,UID,NAME');rows=[x['pid'] for x in b.processes(ps) if x['name']=='foundation']
 if len(rows)==1 and rows!=pid:newpid=rows[0];break
assert newpid
allpaths=paths+[f'/proc/{newpid}/root'+p for p in paths]
_,v=board.shell('sha256sum '+' '.join(allpaths));assert len(v.splitlines())==4 and all(x.split()[0]==new for x in v.splitlines())
(out/'after.txt').write_text(v)
_,v=board.shell(f'cat /proc/{newpid}/maps');(out/'foundation-maps.txt').write_text(v)
time.sleep(15)
board.shell('power-shell wakeup');board.shell('uitest uiInput keyEvent Home',required=False)
image=b.capture(board,remote+'/desktop.jpeg',out/'desktop.jpeg')
b.save(out/'result.json',{'boot_id':board.boot,'before_pid':pid[0],'foundation_pid':newpid,'old_sha256':old,'new_sha256':new,'backup':remote,'root_mount_preserved':'rw','four_hashes_verified':True,'screenshot':image})
print(json.dumps({'foundation_pid':newpid,'out':str(out),'screenshot':image},indent=2))
