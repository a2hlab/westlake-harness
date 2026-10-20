#!/usr/bin/env python3
"""#46: rebuild liboh_adapter_bridge.so with one recompiled oh_mediacodec_shim.cpp (#36 rule).

Reuses the exact compile flags and link line of out-ability38/native-stack (the build that
produced the deployed bridge e4ab5de6), swapping only the mediacodec object.
usage: build_bridge_mc.py <westlake-src-root|-> <out-dir>
  '-' relinks the untouched object set (reproducibility check).
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

BASE = Path('/home/zhaoyue/a2hlab/ws/out-ability38/native-stack/artifacts.json')
ORIG_OBJ = ('/home/dspfac/a2hlab/source-closure/verify/out-touch21/fd/bridge15/objects/'
            'westlake_framework_core_jni_oh_mediacodec_shim.cpp.o')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


src_root, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
art = json.loads(BASE.read_text())
cmds = {c['label']: c['command'] for c in art['commands']}
compile_cmd = cmds['compile-oh_input_bridge.cpp']
link_cmd = list(cmds['link-bridge'])

for obj, want in art['reused_objects'].items():
    if sha(obj) != want:
        sys.exit(f'reused object changed since e4ab5de6: {obj}')

obj = ORIG_OBJ
if src_root != '-':
    src = Path(src_root) / 'framework/core/jni/oh_mediacodec_shim.cpp'
    obj = str(out / 'oh_mediacodec_shim.cpp.o')
    cc = []
    for a in compile_cmd:
        if a.endswith('/framework/window/jni/oh_input_bridge.cpp'):
            a = str(src)
        elif a.endswith('oh_input_bridge.cpp.o'):
            a = obj
        elif a.endswith('oh_input_bridge.cpp.o.d'):
            a = obj + '.d'
        cc.append(a)
    assert str(src) in cc and obj in cc, 'compile command shape changed'
    subprocess.run(cc, check=True)
    print('object', sha(obj), obj)

lib = str(out / 'liboh_adapter_bridge.so')
link_cmd = [obj if a == ORIG_OBJ else a for a in link_cmd]
link_cmd[link_cmd.index('-o') + 1] = lib
subprocess.run(link_cmd, check=True)
print('bridge', sha(lib), lib)
