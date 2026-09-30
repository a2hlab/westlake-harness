#!/usr/bin/env python3
"""Rebuild one registration-order object with the original frozen N4 recipe."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
P=Path(__file__).resolve().parent;R=P.parents[2]
old=R/'bms/src/.work/n4-native/runtime';out=R/'bms/src/.work/n4-registration-order'
source_view=R/'bms/src/.work/n4-native/frozen-source-view'
assert source_view.is_dir()
out.mkdir(exist_ok=True)
shutil.copytree(old/'runtime-objects',out/'runtime-objects',dirs_exist_ok=True)
for item in (out/'runtime-objects').glob('*.o'): item.touch()
(out/'runtime-objects/AndroidRuntime.o').unlink()
recipe=(old/'recipe.sh').read_text().replace(str(R/'benchmark/2026-09-30-n4-native/src/AndroidRuntime.cpp'),str(P/'AndroidRuntime.cpp'))
(out/'recipe.sh').write_text(recipe)
driver=(old/'driver.sh').read_text().replace(str(old),str(out)).replace('--source-root '+str(R)+'\n','--source-root '+str(source_view)+'\n')
(out/'driver.sh').write_text(driver)
env=os.environ.copy();env.update(N3B_SOURCE=str(R/'benchmark/2026-09-30-n3b-webview/src/webview_publication.cpp'),N3B_WITH_PUBLICATION='1')
subprocess.run(['bash',str(out/'driver.sh')],env=env,check=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
changed=[p.name for p in (old/'runtime-objects').glob('*.o') if sha(p)!=sha(out/'runtime-objects'/p.name)]
assert changed==['AndroidRuntime.o'],changed
print(sha(out/'runtime-out/liboh_android_runtime.so'))
