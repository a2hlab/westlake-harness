"""VM-only locked JAR overlay with a pinned baseline and explicit rollback."""
from pathlib import Path
import json,sys
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root.parent/'batch'));import bms_batch as b
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'scripts/lab'));import lab_paths  # <repo>/scripts/lab
out=Path.home()/'a2hlab/board/b5-alias-deploy-5ea';out.mkdir(exist_ok=False)
build=json.loads((root/'build-result.json').read_text())
board=b.Board('5ea34a4500000000000000001123012c',str(lab_paths.tools()/'hdc_mac.sh'),'mac '+str(lab_paths.tools()/'board_note.sh'),'cx-t0',out/'commands')
board.ready();target='/system/android/framework/oh-adapter-runtime.jar';remote='/data/local/tmp/b5-alias-20260928'
_,before=board.shell('sha256sum '+target)
assert before.split()[0]==build['baseline_sha256'],before
board.receive(target,out/'baseline.jar')
assert b.sha(out/'baseline.jar')==build['baseline_sha256']
_,mounts=board.shell('cat /proc/self/mountinfo');(out/'mountinfo-before.txt').write_text(mounts)
board.shell('mkdir -p '+remote);board.send(build['output'],remote+'/oh-adapter-runtime.jar')
_,check=board.shell('sha256sum '+remote+'/oh-adapter-runtime.jar');assert check.split()[0]==build['output_sha256']
board.shell('chmod 0644 '+remote+'/oh-adapter-runtime.jar; chcon u:object_r:system_file:s0 '+remote+'/oh-adapter-runtime.jar; mount --bind '+remote+'/oh-adapter-runtime.jar '+target)
_,after=board.shell('sha256sum '+target+' /proc/13161/root'+target);assert len(after.splitlines())==2 and all(line.split()[0]==build['output_sha256'] for line in after.splitlines()),after
rollback='umount '+target+'; sha256sum '+target
(out/'rollback.txt').write_text(rollback+'\n')
receipt={'serial':board.serial,'boot_id':board.boot,'before':before,'after':after,'build':build,'rollback':rollback,'original_backup':str(out/'baseline.jar'),'vm_evidence':str(out)}
(root/'deployment.json').write_text(json.dumps(receipt,indent=2)+'\n');print('overlay verified in shell and AppSpawnX root')
