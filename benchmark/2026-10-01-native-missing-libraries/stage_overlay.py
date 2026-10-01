"""Stage only pinned new payloads; no package manifest, deployment or ready claim."""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path

from collect import PINS, verify

HERE = Path(__file__).resolve().parent


def overlay(workspaces, destination):
    if destination.exists():
        raise ValueError('Overlay destination must not exist')
    receipts = json.loads((HERE / 'facade-build.json').read_text())
    for name, pin in receipts['sources'].items():
        verify((HERE / name).read_bytes(), pin)
    alias = workspaces / '01.OH61AOSP16/real-work/.state/build-oh-component-hw248/m1-route-a-generation-20260825-r109c-zlib-global/route-a-generation/pass1/zlib/libz.so'
    provider = workspaces / 'westlake-generation-u8-j9-t7e/native/payload/android/lib64/libshared_libz.z.so'
    payloads = {
        'payload/android/lib64/westlake_native/libz.so': (alias.read_bytes(), PINS['alias']),
        'payload/android/lib64/westlake_native/libshared_libz.z.so': (provider.read_bytes(), PINS['zlib']),
        'payload/android/lib64/westlake_audio/libOpenSLES.so':
            (base64.b64decode((HERE / 'facade.so.b64').read_bytes(), validate=False), receipts['artifact_sha256']),
    }
    for data, pin in payloads.values():
        verify(data, pin)
    destination.mkdir(parents=True)
    for relative, (data, pin) in payloads.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    receipt = dict(status='overlay-only-not-deployable', files={name: pin for name, (data, pin) in payloads.items()},
        native_gates_pending=True, host_and_loader_rebuild_required=True,
        forbidden_root_alias='payload/android/lib64/libz.so',
        required_manifest_changes='cx-t0 must merge files/live_hashes and rebuild the identity-bound N1/N2 sidecars; no old exception carries automatically')
    (destination / 'overlay.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspaces', type=Path, default=Path(os.environ.get('WORKSPACES', HERE.parents[2])))
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    print(json.dumps(overlay(arguments.workspaces, arguments.output), indent=2))
