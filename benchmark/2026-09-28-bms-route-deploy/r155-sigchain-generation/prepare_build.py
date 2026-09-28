"""Extract the original two build stages; never rebuild any provider."""
from pathlib import Path
import shutil
R=Path(__file__).resolve().parents[3];W=R/'bms/src/.work/b6-r155';P=W/'project/adapter/framework/appspawn-x/security_specialization/stock_child_plugin';O=P/'out/route-a-generation'
oldgen='74e6f75976087d7890088b29c08482f17573a588fa5857cb6ca39264838ce16d'
for p in ['providers','pass1/provider','pass2/provider','logs']: (O/p).mkdir(parents=True,exist_ok=True)
for f in (W/'live'/oldgen).glob('*.so'):
 if f.name=='libwestlake_android_runtime_provider.so':
  for pas in ['pass1','pass2']:shutil.copy2(f,O/pas/'provider'/f.name)
 else:shutil.copy2(f,O/'providers'/f.name)
# Link-only frozen libraries supplied by the previously recovered closure.
current=R/'bms/src/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/frozen'
for f in current.rglob('*'):
 target=P/'frozen'/f.relative_to(current)
 if f.is_file() and not target.exists():target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,target)
t=(P/'build_target_in_container.sh').read_text()
preamble=t[:t.index('for input in')]
script=preamble+f'GENERATION_SHA={oldgen}\nPLUGIN_BUILD_ID_HEX=${{GENERATION_SHA:0:40}}\n'
script+=t[t.index('mkdir -p "$OUT/pass1"'):t.index('\nbuild_pass pass1\n')]
script=script[:script.index('    local plugin_sha')]+'}\n'
# SDK lacks private dlns declarations; force the existing ABI declaration only.
script=script.replace('-std=c11 \\', '-std=c11 -include '+str(W/'build-declarations.h')+' \\')
(W/'build-declarations.h').write_text('#include <linux/limits.h>\n#include "'+str(R/'bms/src/adapter/framework/app-native-loader/include/oh_dlns_abi.h')+'"\n')
script+='\nbuild_pass pass1\nbuild_pass pass2\ncmp "$OUT/pass1/libwestlake_android_child.z.so" "$OUT/pass2/libwestlake_android_child.z.so"\n'
(W/'build-child.sh').write_text(script)
h=(P/'build_route_a_generation_in_container.sh').read_text()
host=h[:h.index('for identity_name in')]
host+=f'GENERATION_SHA={oldgen}\nPLUGIN_BUILD_ID_HEX=${{GENERATION_SHA:0:40}}\nPLUGIN_SHA256=$(sha256sum "$PLUGIN/out/target/pass1/libwestlake_android_child.z.so" | cut -d " " -f1)\n'
host+=h[h.index('record()'):h.index('\nINCLUDES=(',h.index('record()'))]
host+=h[h.index('HOST_INCLUDES=('):h.index('\nbuild_stock_host pass1\n')]
host+='\nbuild_stock_host pass1\nbuild_stock_host pass2\ncmp "$OUT/pass1/host/appspawn-x-stock" "$OUT/pass2/host/appspawn-x-stock"\n'
(W/'build-host.sh').write_text(host)
print(P)
