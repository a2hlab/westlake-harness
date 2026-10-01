#!/usr/bin/env python3
"""Compare a rebuilt native candidate with the DEPLOYED binary it replaces: strings it drops or adds.

    deployed_strings_diff.py <candidate.so> [--deployed <path> | --name <libx.so>] [--allow-add S ...] [--allow-drop S ...]

Exit 1 when the candidate drops a printable string the deployed binary has, or adds one not allowed.

2026-10-01 23:3x: U10's libnativeloader policy (621caec4) was rebuilt on a reproduced "baseline" (0048d7d3) whose baked
system-library table had 4 entries; the deployed U9 binary (fb9dc937) had 5 -- libsoundpool.so. Exports 7/7 and
abi_diff --calls passed because they compared the candidate with the reproduced baseline, so the dropped table entry
reached the boards and OpenCamera / fd-app / fd-plus died in SoundPool.<clinit> ("absent from the adapter manifest").
Baked tables are data, invisible to export / call diffs; a string diff against the deployed bytes sees them.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lab_paths  # noqa: E402

DEFAULT_GENERATION = 'westlake-generation-u9-j10g-238ffc14'


def readelf():
    tools = sorted((Path.home() / 'Library/Android/sdk/ndk').glob('*/toolchains/llvm/prebuilt/*/bin/llvm-readelf'))
    return str(tools[-1]) if tools else 'llvm-readelf'


def strings(path):
    """Strings of the read-only data sections only: code bytes and symbol tables would drown the signal (an unstripped
    candidate carries symbol names a stripped deployed binary lacks)."""
    out = set()
    for section in ('.rodata', '.data.rel.ro'):
        text = subprocess.run([readelf(), '-p', section, str(path)], capture_output=True, text=True).stdout
        out |= {m.group(1) for m in re.finditer(r'^\s*\[\s*[0-9a-f]+\]\s+(.{4,})$', text, re.M)}
    # .data.rel.ro holds pointers whose bytes sometimes print (cx-bms 2026-10-02 00:04 on appspawn-x: "....~...~").
    # Keep strings that look like text: mostly identifier / path / format characters and at least one letter.
    textish = re.compile(r'[A-Za-z0-9_./+%:\[\]{}()=, -]')
    return {x for x in out if re.search('[A-Za-z]', x) and sum(1 for c in x if textish.match(c)) >= 0.9 * len(x)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('candidate')
    ap.add_argument('--deployed', help='deployed binary path')
    ap.add_argument('--name', help=f'library name to look up in $WORKSPACES/{DEFAULT_GENERATION}')
    ap.add_argument('--allow-add', nargs='*', default=[])
    ap.add_argument('--allow-drop', nargs='*', default=[])
    args = ap.parse_args()
    deployed = args.deployed
    if not deployed:
        name = args.name or Path(args.candidate).name
        hits = sorted(p for p in (lab_paths.workspaces() / DEFAULT_GENERATION).rglob(name) if p.is_file())
        if not hits:
            sys.exit(f'no deployed {name} in {DEFAULT_GENERATION}; pass --deployed')
        deployed = hits[0]
    old, new = strings(deployed), strings(args.candidate)
    dropped = sorted(old - new - set(args.allow_drop))
    added = sorted(new - old - set(args.allow_add))
    print(f'deployed {deployed}\ncandidate {args.candidate}')
    for s in dropped:
        print(f'DROPPED {s!r}')
    for s in added:
        print(f'ADDED   {s!r}')
    print(f'{len(dropped)} dropped, {len(added)} added (after allow lists)')
    return 1 if dropped or added else 0


if __name__ == '__main__':
    sys.exit(main())
