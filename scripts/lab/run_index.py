#!/usr/bin/env python3
"""Index every bms_batch run directory so past board evidence can be queried instead of re-run.

    run_index.py build [--root DIR ...] [--index FILE]          # scan, write one JSON row per (run, key)
    run_index.py query [--index FILE] [--key K] [--runtime FP] [--where FIELD>N] [--fields a,b,c] [--group FIELD]

Why (user rule 2026-10-01): the bridge/runtime double load and the "unknown sessionId" wall were sitting in run
directories that already existed (probe maps, hilogs) while windows were opened one by one to test hypotheses. With
this index a question like "which keys ever show unknown sessionId, on which runtime" is one query.

A run is a directory holding facts.txt (bms_batch: <run>/<serial>/facts.txt with one <key>/ directory per app).
Per (run, key) row: run (path with $WORKSPACES), serial, runtime_fp, boot_fp, key, alive_t5, alive_t20,
facts_status, child_hilog, unknown_session (count of "getOhNativeWindow: unknown sessionId" in the key's hilog),
first_fatal (first FATAL EXCEPTION / Fatal signal / JNI DETECTED ERROR / Reason:Signal line, trimmed), cause (the
exception text: the deepest 'Caused by' within 60 lines after the first fatal, else the first exception line there;
None when the fatal has no Java chain -- then first_fatal is the native signal / JNI abort line),
install_icon (the installer's ReadIconByManifest line from install-hilog.txt when present), and run-level probe
load counts (probe/child-*-maps.txt: load instances of bridge / runtime / libart / libnativehelper / libandroid, the
activation_smoke counting), and key_loads: the same libraries' load paths in the app's own maps-*.txt when present. Screenshots are not judged here -- verdicts stay with the outer loop's sign-offs.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lab_paths  # noqa: E402

FACT_ROW = re.compile(r'^(\S+)\s+shots \S+\s+alive t5=(\S+) t20=(\S+)\s+child_hilog=(\S+)\s+(\S+)')
# 2026-10-01 (cx-bms): 11 "no first fatal" keys did die -- via the child's main_threw -> System.exit(1), other
# System.exit calls, a skia/hwui ASSERT abort, or APPSPAWN "exit with signal 9"; the first pattern set missed them.
FATAL = re.compile(r'FATAL EXCEPTION|Fatal signal|JNI DETECTED ERROR|Reason:Signal|Unable to start activity|'
                   r'J_invokeStaticMain_main_threw|System\.exit called|ASSERT.{0,40}failed|exit with signal')
UNKNOWN = 'getOhNativeWindow: unknown sessionId'
PROBE_LIBS = ['liboh_adapter_bridge.so', 'liboh_android_runtime.so', 'libart.so', 'libnativehelper.so', 'libandroid.so']


def default_index():
    return lab_paths.inputs() / 'run-index/index.jsonl'


def rel(p, ws):
    s, ws = str(p), Path(ws).resolve()
    return s.replace(str(ws), '$WORKSPACES', 1) if s.startswith(str(ws)) else s


CAUSE = re.compile(r'(Caused by: |^\S*\s*(java|android)\.[\w.$]+(Exception|Error): )')


def scan_hilog(path):
    """unknown-sessionId count, first fatal line, and the exception text (last 'Caused by' of the first fatal
    chain, else the first exception line) -- the fatal line alone ('FATAL EXCEPTION: main') carries no cause."""
    unknown, fatal, cause, chain = 0, None, None, 0
    try:
        with open(path, errors='replace') as fh:
            for line in fh:
                if UNKNOWN in line:
                    unknown += 1
                if fatal is None and FATAL.search(line):
                    fatal = line.strip()[:240]
                    chain = 60
                msg = line.split('[stderr] ', 1)[-1].strip()
                # only inside the first fatal's chain: an exception logged elsewhere is often caught and benign
                # (2026-10-01: a first-exception-anywhere rule grouped 14 keys under a probing ClassNotFoundException,
                # glmark2 and ath0-rpn among them, whose real fatals are native)
                if fatal is not None and chain > 0:
                    if 'Caused by: ' in msg:
                        cause = msg[:240]
                    elif cause is None and re.search(r'(java|android|androidx)\.[\w.$]+(Exception|Error)(: |$)', msg):
                        cause = msg[:240]
                    chain -= 1
    except OSError:
        return None, None, None
    return unknown, fatal, cause


def probe_loads(run_dir):
    """activation_smoke layout: <out>/group-N/<run-id>/<serial>/facts.txt and <out>/probe/child-*-maps.txt."""
    import activation_smoke
    maps = []
    for up in list(Path(run_dir).parents)[:3]:
        maps = sorted((up / 'probe').glob('child-*-maps.txt'))
        if maps:
            break
    if not maps:
        return None
    got = activation_smoke.copies(maps[0].read_text(errors='replace'), PROBE_LIBS)
    return {lib: len(v) for lib, v in got.items()}


def parse_facts(text):
    head = {'runtime_fp': None, 'boot_fp': None}
    rows = {}
    for line in text.splitlines():
        m = re.match(r'^RUNTIME fingerprint=(\w+)', line)
        if m:
            head['runtime_fp'] = m.group(1)
        m = re.match(r'^BOOTIMAGE fingerprint=(\w+)', line)
        if m:
            head['boot_fp'] = m.group(1)
        m = FACT_ROW.match(line)
        if m and not line.startswith(('RUNTIME', 'BOOTIMAGE', 'TOTAL', 'TOOL', 'FROZEN')):
            rows[m.group(1)] = {'alive_t5': m.group(2), 'alive_t20': m.group(3), 'child_hilog': m.group(4),
                                'facts_status': m.group(5)}
    return head, rows


def build(roots, index):
    ws = lab_paths.workspaces()
    n, seen = 0, set()
    index.parent.mkdir(parents=True, exist_ok=True)
    with open(index, 'w') as out:
        for root in roots:
            for facts in sorted(Path(root).resolve().rglob('facts.txt')):
                if '.git' in facts.parts:
                    continue
                run_dir = facts.parent
                head, rows = parse_facts(facts.read_text(errors='replace'))
                run_id = (run_dir.parent.name, run_dir.name)  # <run-id>/<serial>: landed copies repeat it
                if run_id in seen:
                    continue
                seen.add(run_id)
                loads = probe_loads(run_dir) if rows else None
                for key, r in rows.items():
                    kdir = run_dir / key
                    unknown, fatal, cause = scan_hilog(kdir / 'hilog.txt')
                    icon = None
                    if (kdir / 'install-hilog.txt').exists():
                        icon = next((l.strip()[:200] for l in open(kdir / 'install-hilog.txt', errors='replace')
                                     if 'ReadIconByManifest' in l), None)
                    key_loads = None
                    kmaps = sorted(kdir.glob('maps-*.txt'))  # bms_batch keeps each app's maps since 2026-10-01
                    if kmaps:
                        import activation_smoke
                        got = activation_smoke.copies(kmaps[0].read_text(errors='replace'), PROBE_LIBS)
                        key_loads = {lib: [x.split('@')[0] for x in v] for lib, v in got.items() if v}
                    row = dict(run=rel(run_dir, ws), serial=run_dir.name[:8], key=key, **head, **r, key_loads=key_loads,
                               unknown_session=unknown, first_fatal=fatal, cause=cause, install_icon=icon, probe_loads=loads)
                    out.write(json.dumps(row, ensure_ascii=False) + '\n')
                    n += 1
    return n


def matches(row, args):
    if args.key and row['key'] != args.key and not re.search(args.key, row['key']):
        return False
    if args.runtime and row.get('runtime_fp') != args.runtime:
        return False
    for cond in args.where or []:
        m = re.match(r'(\w+)(>=|<=|=|>|<|~)(.*)', cond)
        if not m:
            raise SystemExit(f'bad --where {cond}')
        f, op, v = m.groups()
        x = row.get(f)
        if op == '~':
            if x is None or not re.search(v, str(x)):
                return False
            continue
        if op == '=':
            if str(x) != v:
                return False
            continue
        if x is None:
            return False
        x, v = float(x), float(v)
        if not {'>': x > v, '<': x < v, '>=': x >= v, '<=': x <= v}[op]:
            return False
    return True


def query(args):
    rows = [json.loads(l) for l in open(args.index)]
    rows = [r for r in rows if matches(r, args)]
    if args.group:
        groups = {}
        for r in rows:
            groups.setdefault(str(r.get(args.group)), []).append(r)
        for g, rs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            print(f'{len(rs):5d}  {g}')
        return 0
    fields = (args.fields or 'key,runtime_fp,alive_t20,unknown_session,run').split(',')
    for r in rows:
        print('\t'.join(str(r.get(f)) for f in fields))
    print(f'# {len(rows)} rows', file=sys.stderr)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build')
    b.add_argument('--root', action='append')
    b.add_argument('--index', type=Path, default=None)
    q = sub.add_parser('query')
    q.add_argument('--index', type=Path, default=None)
    q.add_argument('--key')
    q.add_argument('--runtime')
    q.add_argument('--where', action='append', help='FIELD>N, FIELD=V, FIELD~REGEX (repeatable)')
    q.add_argument('--fields')
    q.add_argument('--group')
    args = ap.parse_args(argv)
    args.index = args.index or default_index()
    if args.cmd == 'build':
        ws = lab_paths.workspaces()
        roots = args.root or [str(p) for p in sorted(ws.glob('westlake-harness*/benchmark'))] + \
            [str(p) for p in sorted(ws.glob('_*'))]
        n = build(roots, args.index)
        print(f'indexed {n} (run, key) rows -> {args.index}')
        return 0
    return query(args)


if __name__ == '__main__':
    sys.exit(main())
