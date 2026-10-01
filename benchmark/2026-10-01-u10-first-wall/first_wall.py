#!/usr/bin/env python3
"""Parameterized first-wall table (generalizes u9_first_wall.py, #90).

Per non-lit key in a sign-off: family / cause / first_fatal, from the run_index rows matching a runtime_fp and a
run-name substring. Optionally joins a U10-coverage map (U9 only) and/or diffs against a previous first-wall table.

    first_wall.py [--runtime FP] [--run-pattern SUBSTR] [--signoff PATH] [--run-index PATH]
                  [--label LABEL] [--out DIR] [--compare-to PREV-first-wall.json]

Defaults reproduce the U9 table (commit c671f4fc8): --runtime a8cb9a5a45a6 --run-pattern approved-j10g
--signoff .../2026-10-01-u9-sweep/outer-signoff.json --label u9.

--compare-to PREV.json: after building the current (e.g. U10) table, classify each key vs PREV (e.g. U9):
  unchanged (same family+cause), moved (non-lit in both, family/cause changed -> shows the new wall),
  disappeared (non-lit in prev, now lit -> wall gone), new-wall (lit in prev, now non-lit -> regression).
Writes <label>-vs-<prevlabel>-diff.{json,md}.
"""
import argparse, json, re, sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/lab'))
try:
    import lab_paths; WS = lab_paths.workspaces()
except Exception:
    WS = Path(__file__).resolve().parents[3]   # fallback: .../workspaces

# U9->U10 coverage (only meaningful for --label u9; the task's U10 fix set).
U10_COVERAGE = {
    'libstdc++': {'toutiao'},
    'libjnigraphics': {'aegis', 'fd-android', 'fd-binaryeye', 'fd-droidify', 'fd-gallery', 'fd-k9', 'fd-tusky',
                       'wikipedia', 'cv2-com-armanmaurya-archiv', 'cv2-de-markusfisch-android-shadereditor'},
    'strerror_r': {'fd-fennec_fdroid', 'firefox'},
    'OpenSLES': {'mindustry'},
    'J10f': {'cv2-com-stoutner-privacybrowser-standard', 'cv2-timur-webrtc-check', 'fd-tutanota'},
    'Predicate': {'cv2-com-nbossard-packlist'},
}


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


def coverage(key, label):
    if label != 'u9':
        return None
    for fix, keys in U10_COVERAGE.items():
        if key in keys:
            return fix
    return None


def verdicts(signoff):
    d = json.loads(Path(signoff).read_text())
    keys = d.get('keys', {})
    return ({e['key']: e['verdict'] for e in keys} if isinstance(keys, list)
            else {k: v['verdict'] for k, v in keys.items()})


def build(runtime, run_pattern, signoff, run_index, label):
    verdict = verdicts(signoff)
    rows_by_key = {}
    with open(run_index, encoding='utf-8', errors='replace') as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get('runtime_fp') == runtime and run_pattern in (row.get('run', '') or ''):
                rows_by_key.setdefault(row['key'], row)   # first match per key
    results = []
    for key, v in verdict.items():
        if v.startswith('lit'):
            continue
        row = rows_by_key.get(key)
        if not row:
            results.append({'key': key, 'verdict': v, 'family': 'no-run', 'cause': '', 'first_fatal': '',
                            'u10_covered': None})
            continue
        results.append({'key': key, 'verdict': v, 'family': family(row),
                        'cause': (row.get('cause') or '')[:200], 'first_fatal': (row.get('first_fatal') or '')[:200],
                        'u10_covered': coverage(key, label)})
    return verdict, results


def write_table(out, label, results):
    out = Path(out)
    (out / f'{label}-first-wall.json').write_text(
        json.dumps({'schema': 'first-wall-v2', 'label': label, 'entries': results}, indent=2, ensure_ascii=False))
    fam_counts = defaultdict(int)
    for r in results:
        fam_counts[r['family']] += 1
    with open(out / f'{label}-first-wall.md', 'w') as f:
        f.write(f'# {label} first-wall table (non-lit keys)\n\nTotal non-lit keys: {len(results)}\n\n')
        f.write('| Key | Verdict | Family | Cause | First Fatal | U10 Covered |\n|---|---|---|---|---|---|\n')
        for r in results:
            f.write(f"| {r['key']} | {r['verdict']} | {r['family']} | {r['cause'][:60]} | {r['first_fatal'][:60]} | {r['u10_covered'] or 'no'} |\n")
        f.write('\n## Family counts\n\n')
        for fam, c in sorted(fam_counts.items(), key=lambda x: -x[1]):
            f.write(f'- {fam}: {c}\n')
    return fam_counts


def compare(cur_label, cur_results, prev_path, out):
    prev = json.loads(Path(prev_path).read_text())
    prev_label = prev.get('label', 'prev')
    prev_nl = {e['key']: e for e in prev['entries']}
    cur_nl = {e['key']: e for e in cur_results}
    rows = []
    for key in sorted(set(prev_nl) | set(cur_nl)):
        p, c = prev_nl.get(key), cur_nl.get(key)
        if p and not c:
            cls, detail = 'disappeared', f'{prev_label} {p["family"]} -> now lit'
        elif c and not p:
            cls, detail = 'new-wall', f'lit in {prev_label} -> now {c["family"]}: {c["cause"][:80]}'
        else:
            same = (p['family'] == c['family'] and p['cause'][:120] == c['cause'][:120])
            if same:
                cls, detail = 'unchanged', c['family']
            else:
                cls, detail = 'moved', f'{p["family"]} ({p["cause"][:50]}) -> {c["family"]} ({c["cause"][:50]})'
        rows.append({'key': key, 'class': cls, 'prev_family': (p or {}).get('family'),
                     'cur_family': (c or {}).get('family'), 'detail': detail})
    out = Path(out)
    (out / f'{cur_label}-vs-{prev_label}-diff.json').write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    counts = defaultdict(int)
    for r in rows:
        counts[r['class']] += 1
    FOCUS = ['toutiao', 'fd-meet', 'firefox', 'fd-fennec_fdroid', 'cv2-com-nbossard-packlist', 'fd-tutanota']
    with open(out / f'{cur_label}-vs-{prev_label}-diff.md', 'w') as f:
        f.write(f'# {cur_label} vs {prev_label} first-wall diff (per key)\n\n')
        f.write('class: unchanged | moved (-> new wall) | disappeared (now lit) | new-wall (regression)\n\n')
        f.write(f'counts: {dict(counts)}\n\n')
        f.write('## Focus keys\n\n| Key | Class | Detail |\n|---|---|---|\n')
        for k in FOCUS:
            r = next((x for x in rows if x['key'] == k), None)
            f.write(f"| {k} | {r['class'] if r else 'n/a'} | {r['detail'] if r else '(not in either table)'} |\n")
        f.write('\n## All keys\n\n| Key | Class | Detail |\n|---|---|---|\n')
        for r in rows:
            f.write(f"| {r['key']} | {r['class']} | {r['detail']} |\n")
    return counts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--runtime', default='a8cb9a5a45a6')
    ap.add_argument('--run-pattern', default='approved-j10g')
    ap.add_argument('--signoff', default=str(WS / 'westlake-harness/benchmark/2026-10-01-u9-sweep/outer-signoff.json'))
    ap.add_argument('--run-index', default=str(WS / 'westlake-inputs/run-index/index.jsonl'))
    ap.add_argument('--label', default='u9')
    ap.add_argument('--out', default='.')
    ap.add_argument('--compare-to', default=None, help='a previous <label>-first-wall.json to diff against')
    a = ap.parse_args(argv)
    verdict, results = build(a.runtime, a.run_pattern, a.signoff, a.run_index, a.label)
    fam = write_table(a.out, a.label, results)
    print(f'{a.label}-first-wall.{{json,md}} written: {len(results)} non-lit keys; families={dict(fam)}')
    if a.compare_to:
        counts = compare(a.label, results, a.compare_to, a.out)
        print(f'{a.label}-vs-diff written: {dict(counts)}')


if __name__ == '__main__':
    main()
