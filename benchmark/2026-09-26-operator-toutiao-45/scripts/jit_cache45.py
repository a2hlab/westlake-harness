"""Install and run the JIT cache pre-spawn hook in the app parent's namespace."""
import pathlib

def prepare_jit_cache(dev, send, runtime, parent=None):
    hook = pathlib.Path(__file__).resolve().parents[2] / '2026-09-26-operator-jit-50/scripts/prepare_jit50.sh'
    send(hook, runtime + '/prepare_jit50.sh')
    dev('chmod 644 ' + runtime + '/prepare_jit50.sh')
    if parent is None:
        return
    result = dev('/bin/nsenter -t ' + str(int(parent)) + ' -m -- /system/bin/sh /data/local/tmp/asx/prepare_jit50.sh')
    if '20010053:20010053:700 nonsymlink=1' not in result:
        raise RuntimeError('JIT cache pre-spawn preparation failed: ' + result)
    return result
