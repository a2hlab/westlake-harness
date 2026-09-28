"""Read-only supplementary sandbox and runtime inspection; run inside VM."""
import sys,json
from pathlib import Path
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root.parent/'batch'))
import bms_batch as b
out=root/'evidence/readback';out.mkdir(exist_ok=True)
board=b.Board('5ea34a4500000000000000001123012c','/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',out/'commands')
board.ready()
board.boot=json.loads((root/'evidence/results.json').read_text())['boot_id']
for pkg in ['com.example.helloworld','org.wikipedia']:
 command=f'''for path in /data/app/android/{pkg} /data/app/el1/bundle/public/{pkg}/android /data/app/el1/100/base/{pkg} /data/app/el1/100/database/{pkg} /data/app/el2/100/base/{pkg} /data/app/el2/100/log/{pkg} /data/app/el2/100/database/{pkg} /data/app/el2/100/sharefiles/{pkg} /data/app/el3/100/base/{pkg} /data/app/el3/100/database/{pkg} /data/app/el4/100/base/{pkg} /data/app/el4/100/database/{pkg}; do echo PATH:$path; stat -c '%a:%u:%g:%C' "$path" 2>&1; done
find /data/app/el1/bundle/public/{pkg} -maxdepth 3 -type f 2>/dev/null
sha256sum /data/app/el1/bundle/public/{pkg}/android/base.apk
true'''
 _,text=board.shell(command);(out/(pkg+'-paths.txt')).write_text(text)
_,text=board.shell('cat /proc/13161/mountinfo; sha256sum /proc/13161/exe /system/lib64/westlake/route-a/*/libwestlake_android_runtime_provider.so /system/android/lib64/liboh_adapter_bridge.so; ls -lZ /dev/unix/socket/AppSpawnX; cat /system/etc/sandbox/appdata-sandbox.json')
(out/'parent-runtime-and-sandbox.txt').write_text(text)
_,text=board.shell('cat /proc/13161/maps; cat /proc/self/mountinfo')
(out/'parent-maps-shell-mounts.txt').write_text(text)
print('supplementary readback complete')
