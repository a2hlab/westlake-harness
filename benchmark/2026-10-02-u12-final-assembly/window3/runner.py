"""Use the reviewed hooks unchanged with isolated approved window configuration."""
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import window_hook,dispatch
window_hook.H=HERE
dispatch.H=HERE
# verify() delegates back to its CLI on VM; preserve this approved configuration.
original_vm=window_hook.vm
def configured_vm(command):
    if len(command)>1 and str(command[1])==str(Path(window_hook.__file__).resolve()):
        command=[command[0],HERE/"runner.py","hook",*command[2:]]
    return original_vm(command)
window_hook.vm=configured_vm
mode=sys.argv.pop(1)
if mode=='dispatch':dispatch.main()
elif mode=='hook':window_hook.main()
else:raise SystemExit('unknown approved runner mode')
