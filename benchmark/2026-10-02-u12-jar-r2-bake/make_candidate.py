#!/usr/bin/env python3
"""U12 JAR-layer candidate list for the outer loop: runtime, stubs and the 27-file boot image, with board targets.

    make_candidate.py

Reads the persisted artifacts in $WORKSPACES/westlake-inputs/generations/u12r2-v1/ (runtime jar, stubs jar, bake/run1
image, bake/jars9, bake logs) and the unified state's identities (T8 receipt = the board image; v3 bundle jars), and
writes candidate.json (+ the same in u12r2-v1/candidate.json) and candidate-image.csv (27 rows: target path, U12 SHA,
board SHA, changed). Fails when a persisted file does not match the SHA this round recorded.
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import lab_paths  # noqa: E402

GEN = lab_paths.inputs() / 'generations'
U12 = GEN / 'u12r2-v1'
V3 = GEN / 'u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle/framework'
T8 = GEN / 't8-rebake-effective'
FW = '/system/android/framework'
RUNTIME_SHA = '0482c9b13fbc6ab5bce3902807eb7972736463b772773fde276cae679ce9bd4f'
STUBS_SHA = '615b8bbecaa7b07fa27d40d25bd13eb6dfb33e6ec6bc7660bc2fc9aeaff1e610'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    runtime, stubs = U12 / 'oh-adapter-runtime-u12r2.jar', U12 / 'adapter-mainline-stubs-u12.jar'
    assert sha(runtime) == RUNTIME_SHA, 'runtime jar drifted'
    assert sha(stubs) == STUBS_SHA, 'stubs jar drifted'
    board_img = dict(reversed(l.split()) for l in (T8 / 'receipt/image-sha256.txt').read_text().splitlines())
    rows = []
    for f in sorted((U12 / 'bake/run1').iterdir()):
        h = sha(f)
        rows.append({'target': f'{FW}/arm64/{f.name}', 'u12_sha256': h, 'board_sha256': board_img[f.name],
                     'changed': 'yes' if h != board_img[f.name] else 'no'})
    assert len(rows) == 27
    with open(HERE / 'candidate-image.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    jars = {}
    for line in (U12 / 'bake/jar-sha256.txt').read_text().splitlines():
        h, n = line.split()
        jars[n] = h
    cand = {
        'name': 'U12 JAR layer (runtime U12 r2 + stubs U12 S1+S2 + boot image re-baked for the stubs)',
        'replace': [
            {'target': f'{FW}/oh-adapter-runtime.jar', 'u12_sha256': RUNTIME_SHA,
             'board_sha256': sha(V3 / 'oh-adapter-runtime.jar'), 'source': str(runtime).replace(str(lab_paths.workspaces()), '$WORKSPACES'),
             'deploy': 'runtime PathClassLoader jar: single-file replacement'},
            {'target': f'{FW}/adapter-mainline-stubs.jar', 'u12_sha256': STUBS_SHA,
             'board_sha256': sha(V3 / 'adapter-mainline-stubs.jar'), 'source': str(stubs).replace(str(lab_paths.workspaces()), '$WORKSPACES'),
             'deploy': 'boot class path jar: only together with the 27-file image below (G1 swap)'},
        ],
        'image': {'dir': str(U12 / 'bake/run1').replace(str(lab_paths.workspaces()), '$WORKSPACES'),
                  'changed': sum(r['changed'] == 'yes' for r in rows), 'unchanged': sum(r['changed'] == 'no' for r in rows),
                  'files': 'candidate-image.csv'},
        'unchanged_boot_jars': {n: h for n, h in jars.items() if n != 'adapter-mainline-stubs.jar'},
        'superseded': {'stubs U12 r2 00b30467 (android.net members + S1 + S2)': 'not a candidate (outer 2026-10-02: drop the 8 android.net classes / 138 members)',
                       'stubs U12 r1 3a12918a': 'not a candidate', 'runtime U12 r1 3bca82c5': 'not a candidate'},
        'gates': {'deployed_class_diff stubs vs 2f365a75': 'gates/class-diff-stubs-u12.txt (rc=0)',
                  'deployed_class_diff runtime vs 5ae3dd29': '../2026-10-02-u12-java-walls/gates/gate-u12r2.txt (rc=0; outer re-ran --deployed: 0 drop/0 reshape/10 add/0 frozen)',
                  'repro 2 bakes': 'gates/repro-27.txt (26 identical + boot.art inside T7D-REPRO-BACKTRACE-001)',
                  'rb': 'gates/gate-rb.txt', 't4b': 'gates/gate-t4b.txt', 'G1/G2': 'gates/gate-g1g2.txt'},
        'logs': 'u12r2-v1/bake/logs/ (bake-runN.session.log teed live on the Mac; dex2oat-runN.log full dex2oat output teed on hw248)',
    }
    for out in (HERE / 'candidate.json', U12 / 'candidate.json'):
        out.write_text(json.dumps(cand, indent=1) + '\n')
    print(f"image: {cand['image']['changed']} changed / {cand['image']['unchanged']} unchanged; runtime {RUNTIME_SHA[:12]}, stubs {STUBS_SHA[:12]}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
