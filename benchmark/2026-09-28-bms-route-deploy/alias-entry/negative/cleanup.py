"""VM only: remove just the newly created B5 fixture and its empty library directory."""
from pathlib import Path
import sys,json
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root.parents[1]/'batch'));import bms_batch as b
out=Path.home()/'a2hlab/board/b5-negative-cleanup-5ea';out.mkdir(exist_ok=False)
f=json.loads((root/'installation.json').read_text());pkg=f['fixture']['package']
board=b.Board(f['serial'],'/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',out/'commands');board.ready()
assert b.cold_stop(board,pkg,f['bms']['uid'],out)
rc,text=board.shell('bm uninstall -n '+pkg,required=False,timeout=120);assert rc==0 and 'success' in text.lower(),text
_,all_bundles=board.shell('bm dump -a');assert pkg not in all_bundles
board.shell('rmdir /system/app/org.a2hlab.b5aliasnegative/lib/armeabi-v7a /system/app/org.a2hlab.b5aliasnegative/lib /system/app/org.a2hlab.b5aliasnegative; rm -f /data/local/tmp/b5-alias-20260928/negative.apk')
_,digest=board.shell('sha256sum /system/android/framework/oh-adapter-runtime.jar /proc/13161/root/system/android/framework/oh-adapter-runtime.jar /data/app/el1/bundle/public/org.wikipedia/android/base.apk /data/app/el1/bundle/public/com.example.helloworld/android/base.apk')
b.save(root/'cleanup.json',{'serial':board.serial,'boot_id':board.boot,'uninstall_output':text,'bundle_absent':True,'fixture_library_dir_removed':True,'runtime_and_original_apks_after':digest,'vm_evidence':str(out)})
print('fixture uninstalled; alias overlay retained; original APK hashes recorded')
