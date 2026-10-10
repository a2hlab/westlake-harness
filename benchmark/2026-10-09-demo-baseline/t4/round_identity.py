#!/usr/bin/env python3
"""Read-only t3 U13 identity gate plus one same post-reboot boot across all windows."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--round', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    configuration = json.loads((a.round / 'round.json').read_text())
    rc = subprocess.run([sys.executable, str(HERE.parent / 't3/verify_identity.py'), '--out', str(a.out), '--serial', configuration['serial']]).returncode
    if rc:
        return rc
    result = json.loads((a.out / 'identity.json').read_text())
    assert result['passed'] and result['unique_identity_paths'] == 319 and not result['diff']
    boot = result['boot_after']
    assert boot != configuration['boot_before_reboot'], 'not a post-reboot round'
    pin = a.round / 'observed-post-reboot-boot.json'
    if pin.exists():
        assert json.loads(pin.read_text())['boot_id'] == boot, 'boot changed during the regression round'
    else:
        with pin.open('x') as f:
            json.dump({'boot_id': boot}, f)
    print(json.dumps({'passed': True, 'paths': 319, 'diff': {}, 'boot_id': boot}))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
