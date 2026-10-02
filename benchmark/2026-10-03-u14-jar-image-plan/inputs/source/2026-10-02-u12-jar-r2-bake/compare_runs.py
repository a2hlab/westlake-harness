#!/usr/bin/env python3
"""Two U12 bakes, 27 files each: byte-identical except the registered boot.art backtrace field.

    compare_runs.py [--out gates/repro-27.txt]

Exceptions come from knowledge/gates/image-provenance-exceptions.json (status approved), never from this script:
T7D-REPRO-BACKTRACE-001 allows boot.art bytes inside [file_offset_start, file_offset_end_exclusive) -- the
sun.nio.ch.PendingFuture.CANCELLED backtrace word that differs run to run with identical tools, inputs and argv.
Any other differing byte or file fails.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import lab_paths  # noqa: E402

BAKE = lab_paths.inputs() / 'generations/u12r2-v1/bake'
REGISTRY = REPO / 'knowledge/gates/image-provenance-exceptions.json'
EXCEPTION_ID = 'T7D-REPRO-BACKTRACE-001'


def exception():
    def find(o):
        if isinstance(o, dict):
            if o.get('id') == EXCEPTION_ID:
                return o
            for v in o.values():
                r = find(v)
                if r:
                    return r
        elif isinstance(o, list):
            for v in o:
                r = find(v)
                if r:
                    return r
        return None
    e = find(json.loads(REGISTRY.read_text()))
    assert e and e.get('status') == 'approved', f'{EXCEPTION_ID} missing or not approved in {REGISTRY}'
    obj = e['object']
    return obj['file'], int(obj['file_offset_start'], 16), int(obj['file_offset_end_exclusive'], 16)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE / 'gates/repro-27.txt'))
    a = ap.parse_args()
    ex_file, lo, hi = exception()
    r1, r2 = BAKE / 'run1', BAKE / 'run2'
    names = sorted(p.name for p in r1.iterdir())
    assert names == sorted(p.name for p in r2.iterdir()) and len(names) == 27, 'run1/run2 file sets differ or != 27'
    lines, bad = [f'# run1 vs run2, {len(names)} files; exception {EXCEPTION_ID}: {ex_file} [{lo:#x}, {hi:#x})'], 0
    for n in names:
        b1, b2 = (r1 / n).read_bytes(), (r2 / n).read_bytes()
        h1, h2 = hashlib.sha256(b1).hexdigest(), hashlib.sha256(b2).hexdigest()
        if b1 == b2:
            lines.append(f'SAME       {n} {h1}')
            continue
        diff = [i for i in range(min(len(b1), len(b2))) if b1[i] != b2[i]] if len(b1) == len(b2) else None
        inside = diff is not None and n == ex_file and all(lo <= i < hi for i in diff)
        lines.append(f'{"EXCEPTION " if inside else "DIFF       "}{n} run1 {h1} run2 {h2} size {len(b1)}/{len(b2)} '
                     f'offsets {[hex(i) for i in diff] if diff is not None else "size-mismatch"}')
        bad += 0 if inside else 1
    lines.append(f'VERDICT: {"PASS" if bad == 0 else "FAIL"} ({sum(l.startswith("SAME") for l in lines)} identical, '
                 f'{sum(l.startswith("EXCEPTION") for l in lines)} within the registered exception, {bad} other)')
    Path(a.out).write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines[-3:]))
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
