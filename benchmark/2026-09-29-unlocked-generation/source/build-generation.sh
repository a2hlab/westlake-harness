#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
export ROUTE_A_PROJECT_ROOT=$ROOT
export WESTLAKE_GENERATION_ROOT=$ROOT/.work/product-tls-generation
export WESTLAKE_ROUTE_A_BASE_PROVIDER_ROOT=$ROOT/rebuilt-provider-base
export WESTLAKE_LIBCXX_HAS_NATIVE_COMPAT=1
PLUGIN=$ROOT/adapter/framework/appspawn-x/security_specialization/stock_child_plugin
export LD_LIBRARY_PATH=$WESTLAKE_GENERATION_ROOT/frozen/toolchain/runtime
python3 - "$ROOT" <<'PY'
from pathlib import Path
import subprocess,hashlib,re,sys
root=Path(sys.argv[1]);plugin=root/'adapter/framework/appspawn-x/security_specialization/stock_child_plugin'
f=plugin/'r45_adapter_identity.env';t=f.read_text()
for prefix,name in [('WLAR_ADAPTER_BRIDGE','liboh_adapter_bridge.so'),('WLAR_ANDROID_RUNTIME','liboh_android_runtime.so')]:
 p=root/'adapter/frozen/r45-dynamic-roots'/name
 sha=hashlib.sha256(p.read_bytes()).hexdigest()
 notes=subprocess.check_output([str(root/'.work/product-tls-generation/frozen/toolchain/bin/llvm-readelf'),'-n',str(p)],text=True)
 bid=re.search(r'Build ID: ([0-9a-f]+)',notes).group(1)
 for key,value in [('SHA256_HEX',sha),('BUILD_ID_HEX',bid)]:t=re.sub(prefix+'_'+key+'=.*',prefix+'_'+key+'='+value,t)
f.write_text(t)
PY
python3 "$PLUGIN/generate_source_closure.py"
python3 "$PLUGIN/generate_route_a_inputs.py"
set -a
source "$PLUGIN/r45_adapter_identity.env"
set +a
exec bash -x "$PLUGIN/build_route_a_generation_in_container.sh"
