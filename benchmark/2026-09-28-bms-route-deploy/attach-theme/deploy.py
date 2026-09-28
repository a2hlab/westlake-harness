"""VM only: lock/boot/hash guards, complete 27-file cohort, two reversible mounts."""
from pathlib import Path
import sys,json,tarfile,hashlib
r=Path(__file__).resolve().parent;sys.path.insert(0,str(r.parent/'batch'));import bms_batch as b
out=Path.home()/'a2hlab/board/b6-deploy-5ea';out.mkdir(exist_ok=False)
board=b.Board('5ea34a4500000000000000001123012c','/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',out/'commands');board.ready()
id=json.loads((r/'identity.json').read_text());assert board.boot==id['boot_id']
fw=json.loads((r/'build-framework.json').read_text());boot=json.loads((r/'build-boot.json').read_text())
assert boot['return_code']==0 and len(boot['outputs'])==27 and set(boot['oat_versions'].values())=={'230'}
_,old=board.shell('sha256sum /system/android/framework/framework.jar /system/android/framework/oh-adapter-runtime.jar /system/android/framework/arm64/boot-framework.oat')
assert [x.split()[0] for x in old.splitlines()]==[fw['original_sha256'],'250958dc3f133b67fb38c5da3caf81714fd6958e2247556e327d917b1f0d3146','0ff275fa856c9a7e404b3e03460aa3b514268e9ee8a3910e0549f0750cc2d7c0']
_,maps=board.shell(f'cat /proc/{id["parent_pid"]}/maps');assert '/libart.so' not in maps,'parent already owns an ART VM; stop for cohort strategy review'
_,mounts=board.shell('cat /proc/self/mountinfo; ls -l /system/android/framework/boot.art');(out/'before-mounts.txt').write_text(mounts)
_,oldboot=board.shell('sha256sum /system/android/framework/arm64/boot*');(out/'old-boot-sha256.txt').write_text(oldboot)
archive=out/'b6-cohort.tar'
with tarfile.open(archive,'w') as tar:
 tar.add(fw['output'],arcname='framework.jar')
 for name in sorted(boot['outputs']):tar.add(Path(boot['vm_output'])/name,arcname='arm64/'+name)
remote='/data/local/tmp/b6-context-20260928';board.shell('test ! -e '+remote+'; mkdir -p '+remote)
board.send(str(archive),remote+'/cohort.tar');_,digest=board.shell('sha256sum '+remote+'/cohort.tar');assert digest.split()[0]==b.sha(archive)
board.shell('set -e; cd '+remote+'; tar -xf cohort.tar; chmod 0755 arm64; chmod 0644 framework.jar arm64/*; chcon -R u:object_r:system_file:s0 framework.jar arm64')
_,hashes=board.shell('sha256sum '+remote+'/framework.jar '+remote+'/arm64/boot*')
expected={'framework.jar':fw['output_sha256'],**boot['outputs']}
assert {Path(x.split()[1]).name:x.split()[0] for x in hashes.splitlines()}==expected
for pkg in ['org.wikipedia','com.example.helloworld','com.a2hlab.bridge.zigzag']:
 _,dump=board.shell('bm dump -n '+pkg);uid=b.parse_bundle(dump,pkg)['uid'];assert b.cold_stop(board,pkg,uid,out,pkg)
board.shell('set -e; mount --bind '+remote+'/framework.jar /system/android/framework/framework.jar; mount --bind '+remote+'/arm64 /system/android/framework/arm64')
_,after=board.shell('sha256sum /system/android/framework/framework.jar /system/android/framework/arm64/boot*')
assert {Path(x.split()[1]).name:x.split()[0] for x in after.splitlines()}==expected
rollback='umount /system/android/framework/arm64; umount /system/android/framework/framework.jar; sha256sum /system/android/framework/framework.jar /system/android/framework/arm64/boot-framework.oat /system/android/framework/oh-adapter-runtime.jar'
rec={'serial':board.serial,'boot_id':board.boot,'parent_pid':id['parent_pid'],'parent_had_no_art_vm':True,'remote':remote,'old_framework_hash':fw['original_sha256'],'expected_files':expected,'shell_after':after,'vm_evidence':str(out),'rollback':rollback,'child_load_verified':False}
b.save(r/'deployment.json',rec);print('B6 framework + complete oat230 cohort mounted; requires child verification')
