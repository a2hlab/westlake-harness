#!/usr/bin/env python3
import json,shutil,subprocess
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[1];W=R.parent
src=W/'westlake-generation-v3-74d1d6d4';dst=W/'westlake-generation-v3-bad-sha'
if not dst.exists():subprocess.run(['cp','-Rc',str(src),str(dst)],check=True)
m=json.loads((dst/'package.json').read_text());m['files']['payload/android/lib64/liboh_adapter_bridge.so']='0'*64;(dst/'package.json').write_text(json.dumps(m,indent=2)+'\n')
cmd=['orb','-m','a2hlab','bash','-lc','/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh -t 5ea34a4500000000000000001123012c shell sha256sum /system/android/lib64/liboh_adapter_bridge.so /system/bin/appspawn-x']
before=subprocess.check_output(cmd,text=True)
r=subprocess.run([str(R/'scripts/lab/deploy_generation.sh'),'5ea34a4500000000000000001123012c',str(dst),'--replace','/system/android/lib64/liboh_adapter_bridge.so'],capture_output=True,text=True)
after=subprocess.check_output(cmd,text=True)
result={'returncode':r.returncode,'before':before,'after':after,'output':r.stdout+r.stderr,'rejected_before_device_io':r.returncode!=0 and 'package SHA mismatch: payload/android/lib64/liboh_adapter_bridge.so' in r.stderr,'unchanged':before==after}
(E/'negative-package.json').write_text(json.dumps(result,indent=2)+'\n')
assert result['rejected_before_device_io'] and result['unchanged'];print('PASS wrong-SHA rejected before device I/O; board hashes unchanged')
