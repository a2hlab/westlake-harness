#!/usr/bin/env python3
"""Print a read-only shell for cc-video; this program never invokes transport."""
import argparse
import re
import shlex
from pathlib import Path
from prepare_data import RT

PROTECTED=('/system/lib64','/data/local/tmp/asx','/data/local/tmp/asx/lib',
           '/data/local/tmp/asx/lib/arm64-v8a','/data/local/tmp/asx/webview-t-lib')

def render(boot,parent,birth,host,hostbirth):
    assert re.fullmatch('[0-9a-f-]{36}',boot)
    assert all(type(x) is int and x>0 for x in (parent,birth,host,hostbirth))
    def identity(pid,b,uid):
        return f'''r=$(cat /proc/{pid}/stat); z=${{r##*) }}; set -- $z
test "${{20}}" = {b}; test "$1" != Z; test "$1" != X
u=$(sed -n 's/^Uid:[[:space:]]*//p' /proc/{pid}/status); set -- $u
test "$1:$2:$3:$4" = {uid}:{uid}:{uid}:{uid}
test "$(sed -n 's/^TracerPid:[[:space:]]*//p' /proc/{pid}/status)" = 0
'''
    guard=f'test "$(cat /proc/sys/kernel/random/boot_id)" = {shlex.quote(boot)}\n'+identity(parent,birth,0)+identity(host,hostbirth,20011206)
    s='set -eu\n'+guard+f'echo T34_BOOT_BEFORE={boot}\n'
    s+=f'echo P_STAT_BEFORE; cat /proc/{parent}/stat\necho H_STAT_BEFORE; cat /proc/{host}/stat\n'
    for path in (RT,RT+'/lib',RT+'/lib/arm64-v8a',RT+'/webview-t-lib',*PROTECTED):
        q=shlex.quote(path)
        s+=f'echo DIRECTORY={q}\nif [ -e {q} ] || [ -L {q} ]; then stat -L -c %d:%i {q}; readlink -f {q}; else echo ABSENT; fi\n'
    for path in ('/system/lib64/libOpenSLES.so',RT+'/liblog.so',RT+'/libandroid_native_network_compat.so'):
        s+=f'sha256sum {shlex.quote(path)}\n'
    for rel in ('run.sh','liboh_adapter_bridge.so','lib/arm64-v8a/libmffmpeg.so','lib/arm64-v8a/libttmplayer.so','webview-t-lib/libwebview_bionic_shim.so'):
        s+=f'echo PRIVATE={shlex.quote(rel)}\nstat -L -c %d:%i {shlex.quote(RT+"/"+rel)} /proc/{parent}/root/data/local/tmp/asx/{rel}\nsha256sum /proc/{parent}/root/data/local/tmp/asx/{rel}\n'
    s+=f'echo P_WID; strings /proc/{parent}/environ | sed -n "s/^WL_PARENT_ID=//p"\n'
    s+=f'echo P_MNT; readlink /proc/{parent}/ns/mnt\n'
    s+='echo DEBUG_GET_BEGIN\nset +e\nparam get debug.ttplayer.log.enable\nprc=$?\nset -e\necho DEBUG_GET_RC=$prc\n'
    s+=f'echo P_STAT_AFTER; cat /proc/{parent}/stat\necho H_STAT_AFTER; cat /proc/{host}/stat\n'+guard+f'echo T34_BOOT_AFTER={boot}\n'
    return s

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--boot',required=True)
    for k in ('parent','birth','host','hostbirth'):p.add_argument('--'+k,type=int,required=True)
    a=p.parse_args();print(render(a.boot,a.parent,a.birth,a.host,a.hostbirth),end='')
