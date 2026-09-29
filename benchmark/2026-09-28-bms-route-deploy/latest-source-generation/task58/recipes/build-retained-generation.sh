#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
cd "$ROOT"
export ROUTE_A_PROJECT_ROOT=$ROOT
export WESTLAKE_GENERATION_ROOT=$ROOT/.work/product-tls-generation
export WESTLAKE_ROUTE_A_BASE_PROVIDER_ROOT=$ROOT/rebuilt-provider-base
export WESTLAKE_LIBCXX_HAS_NATIVE_COMPAT=1
PLUGIN=$ROOT/adapter/framework/appspawn-x/security_specialization/stock_child_plugin
export LD_LIBRARY_PATH=$WESTLAKE_GENERATION_ROOT/frozen/toolchain/runtime
python3 - "$ROOT" <<'PYGUARD'
from pathlib import Path
import hashlib,re,subprocess,sys
r=Path(sys.argv[1]);p=r/'adapter/framework/appspawn-x/security_specialization/stock_child_plugin';env=(p/'r45_adapter_identity.env').read_text()
for prefix,name in [('WLAR_ADAPTER_BRIDGE','liboh_adapter_bridge.so'),('WLAR_ANDROID_RUNTIME','liboh_android_runtime.so')]:
 f=r/'adapter/frozen/r45-dynamic-roots'/name
 assert re.search(prefix+'_SHA256_HEX=(.*)',env).group(1)==hashlib.sha256(f.read_bytes()).hexdigest()
 notes=subprocess.check_output([str(r/'.work/product-tls-generation/frozen/toolchain/bin/llvm-readelf'),'-n',str(f)],text=True)
 assert re.search(prefix+'_BUILD_ID_HEX=(.*)',env).group(1)==re.search(r'Build ID: ([0-9a-f]+)',notes).group(1)
print('PASS actual dynamic-root SHA and Build-ID pins')
PYGUARD
python3 "$PLUGIN/generate_source_closure.py"
python3 "$PLUGIN/generate_route_a_inputs.py"
python3 "$PLUGIN/generate_source_closure.py" --verify
python3 "$PLUGIN/generate_route_a_inputs.py" --verify
(cd "$PLUGIN/out/route-a-generation/providers" && sha256sum -c "$ROOT/retained-providers.sha256")
set -a
source "$PLUGIN/r45_adapter_identity.env"
set +a
bash "$ROOT/build-retained-generation-inner.sh"
(cd "$PLUGIN/out/route-a-generation/providers" && sha256sum -c "$ROOT/retained-providers.sha256")
