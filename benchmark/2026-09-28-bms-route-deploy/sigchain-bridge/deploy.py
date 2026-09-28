"""VM, 5ea only. One reversible bind mount after symbol and identity gates."""
from pathlib import Path
import json,sys
r=Path(__file__).resolve().parent;sys.path.insert(0,str(r.parent/'batch'));import bms_batch as b
from symbol_gate import check
s=json.loads((r/'symbol-gate.json').read_text());assert check(s['required'],s['new_exports'])['deploy_allowed'];assert not s['probe'];assert b.sha(s['new_path'])==s['new_sha256']
out=Path.home()/'a2hlab/board/b6-musl-deploy-5ea';out.mkdir(exist_ok=False)
board=b.Board('5ea34a4500000000000000001123012c','/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',out/'commands');board.ready()
identity=json.loads((r/'bindings.json').read_text());assert board.boot==identity['boot_id']
route='/system/lib64/westlake/route-a/74e6f75976087d7890088b29c08482f17573a588fa5857cb6ca39264838ce16d';target=route+'/libsigchain.so'
_,ps=board.shell('ps -A -o PID,PPID,UID,NAME');parents=[x for x in b.processes(ps) if x['name']=='appspawn-x' and x['uid']==0];assert len(parents)==1;parent=parents[0]['pid']
_,maps=board.shell(f'cat /proc/{parent}/maps');assert '/libart.so' not in maps and '/libsigchain.so' not in maps,'parent preloaded ART: requires explicit restart strategy'
files=[target,route+'/libart.so','/system/android/framework/framework.jar','/system/android/framework/arm64/boot-framework.oat','/system/android/framework/oh-adapter-runtime.jar']
_,before=board.shell('sha256sum '+' '.join(files));expected=[s['old_sha256'],s['libart_sha256'],'3e106350d882cd1f2f6d71c3cc4e9f124412d16f50a2dcb160007c34e6dde9af','0ff275fa856c9a7e404b3e03460aa3b514268e9ee8a3910e0549f0750cc2d7c0','250958dc3f133b67fb38c5da3caf81714fd6958e2247556e327d917b1f0d3146'];assert [x.split()[0] for x in before.splitlines()]==expected
_,mounts=board.shell('cat /proc/self/mountinfo');(out/'before-mounts.txt').write_text(mounts)
remote='/data/local/tmp/b6-musl-20260928';board.shell('test ! -e '+remote+' && mkdir '+remote)
board.send(s['new_path'],remote+'/libsigchain.so');_,sha=board.shell('sha256sum '+remote+'/libsigchain.so');assert sha.split()[0]==s['new_sha256']
board.shell('chmod 0644 '+remote+'/libsigchain.so; chcon u:object_r:system_file:s0 '+remote+'/libsigchain.so')
for pkg in ['org.wikipedia','com.example.helloworld','com.a2hlab.bridge.zigzag']:
 _,dump=board.shell('bm dump -n '+pkg);uid=b.parse_bundle(dump,pkg)['uid'];assert b.cold_stop(board,pkg,uid,out,pkg)
board.shell('mount --bind '+remote+'/libsigchain.so '+target)
_,after=board.shell('sha256sum '+' '.join(files));expected[0]=s['new_sha256'];assert [x.split()[0] for x in after.splitlines()]==expected
b.save(r/'deployment.json',{'serial':board.serial,'boot_id':board.boot,'parent_pid':parent,'parent_preloaded_art':False,'parent_restarted':False,'target':target,'remote':remote,'before':before,'after':after,'expected':dict(zip(files,expected)),'new_sha256':s['new_sha256'],'rollback':'umount '+target,'vm_evidence':str(out)})
print('mounted production musl bridge; child verification pending')
