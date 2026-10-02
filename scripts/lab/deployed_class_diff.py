#!/usr/bin/env python3
"""Compare a rebuilt JAR with the DEPLOYED JAR it replaces: classes it drops, adds, or changes the shape of.

    deployed_class_diff.py <candidate.jar> --deployed <path>          # explicit deployed copy
    deployed_class_diff.py <candidate.jar> --name adapter-mainline-stubs.jar [--generation <dir>]
                           [--allow-add Lx/Y; ...] [--allow-drop ...] [--frozen]

Exit 1 when the candidate drops a class the deployed JAR has, changes a deployed class's superclass or interfaces, or
adds a class not allowed. --name REFUSES when the generation holds two different copies of that JAR: pick the one the
board runs (--deployed), do not let a glob pick it. --frozen also checks the classes knowledge/frozen/frozen.json names.

2026-10-02: T8's adapter-mainline-stubs (255aad61) was patched from the generation's native-payload underlay
(beb369a1), not the JAR the boards run (framework/, f3bcc9d7). rb / t4b / G1 / G2 all passed -- they compare the
candidate with an image reference, not with the deployed JAR -- and the outer loop signed "T8 ready". cx-t0's DEX
check at packaging found tagsoup Parser back to a 2-file stub (FZ-007), android.net.ssl.SSLSockets gone (FZ-008) and
NetworkInfo$State gone: deploying it would have removed two frozen APIs and broken the OkHttp path T8 was for.
JAR twin of deployed_strings_diff.py (U10 libsoundpool).
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import lab_paths  # noqa: E402

DEFAULT_GENERATION = 'westlake-generation-u9-j10g-238ffc14'


def dexdump():
    tools = sorted((Path.home() / 'Library/Android/sdk/build-tools').glob('*/dexdump'))
    return str(tools[-1]) if tools else 'dexdump'


def sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_dexdump(text):
    """`dexdump -l plain` text -> {descriptor: (superclass, sorted interfaces)}."""
    out, cur, section = {}, None, ''
    for line in text.splitlines():
        m = re.match(r"\s*Class descriptor\s*:\s*'(.+)'", line)
        if m:
            cur, section = m.group(1), ''
            out[cur] = ['', []]
            continue
        if cur is None:
            continue
        m = re.match(r"\s*Superclass\s*:\s*'(.+)'", line)
        if m:
            out[cur][0] = m.group(1)
            continue
        m = re.match(r'\s*(Interfaces|Static fields|Instance fields|Direct methods|Virtual methods)\s*-', line)
        if m:
            section = m.group(1)
            continue
        m = re.match(r"\s*#\d+\s*:\s*'(L[^']+;)'", line)
        if m and section == 'Interfaces':
            out[cur][1].append(m.group(1))
    return {k: (v[0], tuple(sorted(v[1]))) for k, v in out.items()}


def classes(jar):
    """{descriptor: (superclass, sorted interfaces)} over every classesN.dex in the JAR."""
    out = {}
    with zipfile.ZipFile(jar) as z, tempfile.TemporaryDirectory() as tmp:
        for entry in sorted(n for n in z.namelist() if re.fullmatch(r'classes\d*\.dex', n)):
            dex = Path(tmp) / entry
            dex.write_bytes(z.read(entry))
            out.update(parse_dexdump(subprocess.run([dexdump(), '-l', 'plain', str(dex)],
                                                    capture_output=True, text=True).stdout))
    return out


def frozen_classes():
    """Class descriptors named in knowledge/frozen/frozen.json api text (e.g. android.net.ssl.SSLSockets)."""
    path = REPO / 'knowledge/frozen/frozen.json'
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    rows = data if isinstance(data, list) else (data.get('frozen') or data.get('entries') or [])
    out = {}
    for row in rows:
        api = row.get('api', '') if isinstance(row, dict) else ''
        for dotted in re.findall(r'\b((?:[a-z][a-z0-9_]*\.){2,}[A-Z][A-Za-z0-9_$]*)', api):
            out['L' + dotted.replace('.', '/') + ';'] = row.get('id', '?')
    return out


def pick_deployed(name, generation):
    copies = sorted(p for p in generation.rglob(name) if p.is_file())
    if not copies:
        sys.exit(f'no deployed {name} in {generation.name}; pass --deployed')
    shas = {}
    for p in copies:
        shas.setdefault(sha(p), []).append(p)
    if len(shas) > 1:
        lines = '\n'.join(f'   {h[:8]}  {p.relative_to(generation)}' for h, ps in shas.items() for p in ps)
        sys.exit(f'REFUSE: {generation.name} holds {len(shas)} different copies of {name}:\n{lines}\n'
                 f'pick the copy the board runs (its on-board sha256) with --deployed; T8 2026-10-02 patched the wrong one')
    return copies[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('candidate')
    ap.add_argument('--deployed')
    ap.add_argument('--name')
    ap.add_argument('--generation', help=f'default $WORKSPACES/{DEFAULT_GENERATION}')
    ap.add_argument('--allow-add', nargs='*', default=[], help='descriptors or package prefixes (Lcom/x/)')
    ap.add_argument('--allow-drop', nargs='*', default=[], help='descriptors or package prefixes (Lcom/x/)')
    ap.add_argument('--allow-reshape', nargs='*', default=[], help='descriptors or prefixes (Lcom/x/) an intended change reshapes')
    ap.add_argument('--frozen', action='store_true')
    args = ap.parse_args()
    deployed = args.deployed
    if not deployed:
        generation = Path(args.generation) if args.generation else lab_paths.workspaces() / DEFAULT_GENERATION
        deployed = pick_deployed(args.name or Path(args.candidate).name, generation)
    old, new = classes(deployed), classes(args.candidate)
    print(f'deployed  {deployed}  ({sha(deployed)[:12]}, {len(old)} classes)')
    print(f'candidate {args.candidate}  ({sha(args.candidate)[:12]}, {len(new)} classes)')
    def allowed(c, allow):  # exact descriptor, or a package prefix ending in '/'
        return any(c == a or (a.endswith('/') and c.startswith(a)) for a in allow)
    dropped = sorted(c for c in set(old) - set(new) if not allowed(c, args.allow_drop))
    added = sorted(c for c in set(new) - set(old) if not allowed(c, args.allow_add))
    reshaped = sorted(c for c in set(old) & set(new) if old[c] != new[c] and not allowed(c, args.allow_reshape))
    for c in dropped:
        print(f'DROPPED  {c}')
    for c in reshaped:
        print(f'RESHAPED {c}: super {old[c][0]} -> {new[c][0]}; interfaces {list(old[c][1])} -> {list(new[c][1])}')
    for c in added:
        print(f'ADDED    {c}')
    bad_frozen = []
    if args.frozen:
        for c, fid in sorted(frozen_classes().items()):
            if c in old and (c not in new or old[c] != new[c]):
                bad_frozen.append(c)
                print(f'FROZEN   {fid} {c} is {"gone" if c not in new else "reshaped"} in the candidate')
    print(f'{len(dropped)} dropped, {len(reshaped)} reshaped, {len(added)} added (after allow lists)'
          + (f', {len(bad_frozen)} frozen class(es) broken' if args.frozen else ''))
    return 1 if dropped or reshaped or added or bad_frozen else 0


if __name__ == '__main__':
    sys.exit(main())
