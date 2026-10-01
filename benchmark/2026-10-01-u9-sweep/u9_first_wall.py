#!/usr/bin/env python3
"""U9 first-wall table: non-lit keys' family/cause/first_fatal, joined with U10 coverage.

Dispatch (ACK(90) 2026-10-01T20:28:16): sign-off from u9-sweep/outer-signoff.json, run_index rows with
runtime_fp=a8cb9a5a45a6 and run containing approved-j10g; per non-lit key: family, cause, first_fatal, U10 coverage.
"""
import json, re, sys
from pathlib import Path
from collections import defaultdict

import sys; sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/lab')); import lab_paths; WS = lab_paths.workspaces()
SIGNOFF = WS/'westlake-harness/benchmark/2026-10-01-u9-sweep/outer-signoff.json'
OUT = Path(__file__).resolve().parent

def family(row):
    cause, fatal = row.get('cause') or '', row.get('first_fatal') or ''
    m = re.search(r'([\w.$]+(?:Exception|Error))', cause)
    if m:
        return 'java:' + m.group(1).split('.')[-1]
    if 'JNI DETECTED' in fatal:
        return 'native:jni-abort'
    if re.search(r'Fatal signal|Reason:Signal|exit with signal', fatal):
        return 'native:signal'
    if 'System.exit' in fatal:
        return 'exit-without-java-chain'
    return 'other-fatal' if fatal else 'no-fatal'

# U10 coverage map (from the task: libstdc++, libjnigraphics, abort visibility, strerror_r, OpenSLES facade, J10f WebSettings defaults, Predicate)
U10_COVERAGE = {
    'libstdc++': {'keys': {'toutiao'}, 'reason': 'libstdc++.so in shared SONAME set'},
    'libjnigraphics': {'keys': {'aegis', 'fd-android', 'fd-binaryeye', 'fd-droidify', 'fd-gallery', 'fd-k9', 'fd-tusky', 'wikipedia', 'cv2-com-armanmaurya-archiv', 'cv2-de-markusfisch-android-shadereditor'}, 'reason': 'libjnigraphics.so in shared SONAME set'},
    'abort-visibility': {'keys': set(), 'reason': 'abort visibility'},
    'strerror_r': {'keys': {'fd-fennec_fdroid', 'firefox'}, 'reason': 'strerror_r shim'},
    'OpenSLES': {'keys': {'mindustry'}, 'reason': 'OpenSLES facade'},
    'J10f': {'keys': {'cv2-com-stoutner-privacybrowser-standard', 'cv2-timur-webrtc-check', 'fd-tutanota'}, 'reason': 'J10f WebSettings defaults'},
    'Predicate': {'keys': {'cv2-com-nbossard-packlist'}, 'reason': 'Predicate stub'},
}

def u10_covered(key, fam):
    """Is this key's wall covered by a U10 fix?"""
    for fix, info in U10_COVERAGE.items():
        if key in info['keys']:
            return fix
    return None

def main():
    # Load sign-off
    d = json.loads(SIGNOFF.read_text())
    keys = d.get('keys', {})
    if isinstance(keys, list):
        verdict = {e['key']: e['verdict'] for e in keys}
    else:
        verdict = {k: v['verdict'] for k, v in keys.items()}
    
    # Read run_index for U9 rows
    run_index = []
    with open(WS/'westlake-inputs/run-index/index.jsonl', encoding='utf-8', errors='replace') as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                if row.get('runtime_fp') == 'a8cb9a5a45a6' and 'approved-j10g' in row.get('run', ''):
                    run_index.append(row)
    
    # Per non-lit key: family, cause, first_fatal, U10 coverage
    results = []
    for key, v in verdict.items():
        if v.startswith('lit'):
            continue
        # Find the row in run_index
        row = None
        for r in run_index:
            if r['key'] == key:
                row = r
                break
        if not row:
            results.append({'key': key, 'verdict': v, 'family': 'no-run', 'cause': '', 'first_fatal': '', 'u10_covered': None})
            continue
        fam = family(row)
        cause = row.get('cause') or ''
        fatal = row.get('first_fatal') or ''
        covered = u10_covered(key, fam)
        results.append({
            'key': key,
            'verdict': v,
            'family': fam,
            'cause': cause[:200],
            'first_fatal': fatal[:200],
            'u10_covered': covered,
        })
    
    # Write JSON
    with open(OUT / 'u9-first-wall.json', 'w') as f:
        json.dump({'schema': 'u9-first-wall-v1', 'entries': results}, f, indent=2, ensure_ascii=False)
    
    # Write MD
    fam_counts = defaultdict(int)
    for r in results:
        fam_counts[r['family']] += 1
    with open(OUT / 'u9-first-wall.md', 'w') as f:
        f.write('# U9 first-wall table (non-lit keys)\n\n')
        f.write(f"Total non-lit keys: {len(results)}\n\n")
        f.write('| Key | Verdict | Family | Cause | First Fatal | U10 Covered |\n')
        f.write('|---|---|---|---|---|---|\n')
        for r in results:
            f.write(f"| {r['key']} | {r['verdict']} | {r['family']} | {r['cause'][:60]} | {r['first_fatal'][:60]} | {r['u10_covered'] or 'no'} |\n")
        f.write(f"\n## Family counts\n\n")
        for fam, count in sorted(fam_counts.items(), key=lambda x: -x[1]):
            f.write(f'- {fam}: {count}\n')
    
    print(f"u9-first-wall.json written: {len(results)} keys")
    print(f"u9-first-wall.md written")
    print(f"family counts: {dict(fam_counts)}")
    
    # Anchor checks
    kitchenowl = [r for r in results if r['key'] == 'fd-kitchenowl']
    toutiao = [r for r in results if r['key'] == 'toutiao']
    print(f"\nanchor fd-kitchenowl first_fatal contains SIGABRT: {any('SIGABRT' in r['first_fatal'] for r in kitchenowl)}")
    print(f"anchor toutiao cause contains UnsatisfiedLinkError or Boolean: {any('UnsatisfiedLinkError' in r['cause'] or 'Boolean' in r['cause'] for r in toutiao)}")

if __name__ == '__main__':
    main()
