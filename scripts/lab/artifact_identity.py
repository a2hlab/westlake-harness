#!/usr/bin/env python3
"""Say whether a local binary is the one deployed in the unified state, before anyone reasons from it.

    artifact_identity.py <file>... [--expected PATH]

For each file: its sha256, and which deployed board path (if any) carries exactly that hash in the unified
state's expected-run map (default: U7, benchmark/2026-10-01-u7-prospective/v1/expected-run.json). A file whose
name matches a deployed path but whose hash does not is reported as NOT DEPLOYED, with the deployed hash.

EVO-0053 and three more the same night (2026-10-01 07:10-08:57): conclusions were drawn from a newer source
tree, from a different build of liboh_adapter_bridge.so whose SHA256SUMS mislabelled it as 84695d62, from
source lines of an older runtime (oh61-v7) than the deployed one (N2 b94f69e4), and from hashes that matched
no file. Run this first; only a DEPLOYED file (and the source its build receipt names) explains board behaviour.
Exit 0 when every file is deployed, 1 otherwise.
"""
import hashlib
import json
import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
DEFAULT = REPO / 'benchmark/2026-10-01-u7-prospective/v1/expected-run.json'


def main(argv):
    args = argv[1:]
    expected = DEFAULT
    if '--expected' in args:
        i = args.index('--expected'); expected = pathlib.Path(args[i + 1]); del args[i:i + 2]
    if not args:
        print(__doc__.strip(), file=sys.stderr); return 2
    exp = json.loads(expected.read_text())
    deployed = {}
    # any {"/board/path": "<64 hex>"} pair anywhere in the JSON counts, so the executor's full 312-identity
    # receipt (child/route-a files included) works as --expected as well as expected-run.json (09:28 cx-t0)
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(k, str) and k.startswith('/') and isinstance(v, str) and len(v) == 64:
                    deployed.setdefault(v, []).append(k)
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(exp)
    by_name = {}
    for paths in deployed.values():
        for p in paths:
            by_name.setdefault(os.path.basename(p), []).append(p)
    rc = 0
    for f in args:
        sha = hashlib.sha256(pathlib.Path(f).read_bytes()).hexdigest()
        if sha in deployed:
            print(f'DEPLOYED     {sha[:12]}  {f}  ->  {", ".join(deployed[sha])}')
            continue
        rc = 1
        name = os.path.basename(f)
        if name in by_name:
            want = {s[:12] for s, ps in deployed.items() for p in ps if p in by_name[name]}
            print(f'NOT DEPLOYED {sha[:12]}  {f}  (deployed {name} is {", ".join(sorted(want))})')
        else:
            print(f'UNKNOWN      {sha[:12]}  {f}  (no deployed file of this name in {expected.name})')
    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv))
