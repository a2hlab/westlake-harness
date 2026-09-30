"""VM-only test-fixture setup for this baseline's pure-Java native namespace fallback."""
from pathlib import Path
import sys,json
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root.parents[1]/'batch'));import bms_batch as b
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts/lab'));import lab_paths  # <repo>/scripts/lab
out=Path.home()/'a2hlab/board/b5-negative-library-dir-5ea';out.mkdir(exist_ok=False)
board=b.Board('5ea34a4500000000000000001123012c',str(lab_paths.tools()/'hdc_mac.sh'),'mac '+str(lab_paths.tools()/'board_note.sh'),'cx-t0',out/'commands');board.ready()
path='/system/app/org.a2hlab.b5aliasnegative'
_,before=board.shell('ls -ldZ /system/app; test ! -e '+path+'; cat /proc/self/mountinfo')
(out/'before.txt').write_text(before)
command='set -e; test ! -e '+path+'; mkdir -p '+path+'/lib/armeabi-v7a; chmod 0755 '+path+' '+path+'/lib '+path+'/lib/armeabi-v7a; chcon -R u:object_r:system_file:s0 '+path+'; ls -ldZ '+path+'/lib/armeabi-v7a'
rc,text=board.shell(command,required=False);b.save(root/'library-dir.json',{'command':command,'return_code':rc,'output':text,'vm_evidence':str(out),'reason':'First negative trial exited on nonexistent pure-Java nativeLibraryDir before class loading; create only the fixture directory, no libraries or APK changes.'});print(rc,text);assert rc==0
