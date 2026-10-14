#!/usr/bin/env python3
"""Prepare a NEW BoatAttack checkout and optionally run the original Unity editor method.
Large project build is explicit --run; this closeout only exercises --help.
Signing secrets are inherited environment values and never written into receipts.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
REVISION = 'dfaa9ef49a727c54c58ac1da0c5375760b0b6e8a'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkout', required=True, type=Path, help='new independent upstream clone at pinned revision')
    p.add_argument('--out', required=True, type=Path, help='new output and raw-log directory')
    p.add_argument('--unity', type=Path, help='Unity2020.3.23f1 executable, required with --run')
    p.add_argument('--run', action='store_true')
    a = p.parse_args()
    tree = a.checkout.resolve()
    revision = subprocess.check_output(['git', '-C', str(tree), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != REVISION:
        p.error('wrong upstream revision')
    # Never modify an existing dirty project; caller must supply a clean independent checkout.
    if subprocess.check_output(['git', '-C', str(tree), 'status', '--porcelain']).strip():
        p.error('checkout is not clean')
    if a.run and (not a.unity or any(not os.environ.get(x) for x in ['BOAT_KEYSTORE', 'BOAT_KEY_ALIAS', 'BOAT_KEYSTORE_PASS'])):
        p.error('--run needs --unity and signing environment; no bundled credentials')
    out = a.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    # Equivalent to original build-a.sh camera edit, now an explicit auditable patch.
    subprocess.run(['git', '-C', str(tree), 'apply', '--check', str(ROOT / 'camera-priority.patch')], check=True)
    subprocess.run(['git', '-C', str(tree), 'apply', str(ROOT / 'camera-priority.patch')], check=True)
    for name in ['manifest.json', 'packages-lock.json']:
        if (tree / 'Packages' / name).read_bytes() != (ROOT / 'Packages' / name).read_bytes():
            raise ValueError('upstream package lock differs: ' + name)
    editor = tree / 'Assets/Editor/BuildBoatAttackAndroid.cs'
    if editor.exists():
        raise ValueError('editor entry already exists')
    editor.parent.mkdir(exist_ok=True); shutil.copyfile(ROOT / 'editor/BuildBoatAttackAndroid.cs', editor)
    receipt = {'schema': 'boat-project-build/v1', 'upstream_revision': revision,
               'unity_version_required': '2020.3.23f1 (c5d91304a876)',
               'large_build_executed': a.run, 'exact_historical_apk_claim': False,
               'status': 'PREPARED_NOT_BUILT', 'rc': None}
    if a.run:
        argv = [str(a.unity.resolve()), '-batchmode', '-quit', '-projectPath', str(tree),
                '-buildTarget', 'Android', '-executeMethod', 'BuildBoatAttackAndroid.Build',
                '-logFile', str(out / 'unity-editor.log')]
        env = dict(os.environ, BOAT_APK_OUT=str(out / 'boat-attack-a.apk'))
        with (out / 'stdout.txt').open('wb') as so, (out / 'stderr.txt').open('wb') as se:
            done = subprocess.run(argv, env=env, stdout=so, stderr=se, check=False)
        rc = done.returncode if done.returncode else (0 if (out / 'boat-attack-a.apk').is_file() else 2)
        receipt.update(rc=rc, producer_rc=done.returncode, status='NEW_BUILD_PASS' if rc == 0 else 'BUILD_FAILED')
        receipt['argv'] = [x.replace(str(tree), '$CHECKOUT').replace(str(out), '$OUT').replace(str(a.unity.resolve()), '$UNITY') for x in argv]
        receipt['unity_sha256'] = hashlib.sha256(a.unity.read_bytes()).hexdigest()
        for name in ['stdout.txt', 'stderr.txt', 'unity-editor.log', 'boat-attack-a.apk']:
            file = out / name
            if file.exists(): receipt[name] = hashlib.sha256(file.read_bytes()).hexdigest()
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt['rc'] or 0


if __name__ == '__main__':
    sys.exit(main())
