#!/usr/bin/env python3
"""Merge donor-compiled members into the DEPLOYED adapter-mainline-stubs smali, adding only what the deployed class lacks.

    merge_smali.py <deployed smali dir> <donor smali dir> <members.tsv> [--report out.json]

members.tsv (tab separated, '#' comments):
    member  <Lclass;>  <name(proto)ret | name:type>    a member the deployed class lacks and the donor must supply
    support <Lclass;>  <name(proto)ret | name:type>    a helper member the added members need (fields, ctors, <clinit>)
    newclass <Lclass;>                                  a class absent from the deployed jar, copied whole

Every deployed method and field stays byte-identical in smali: the donor's copies of existing members are dropped.
Refuses (exit 1) when the donor adds a member that is not listed, when a listed member is not supplied, when a
listed member already exists (the jar changed under the list), when the donor brings a class that is neither
deployed nor listed as newclass, or when both sides have a <clinit> (static init cannot be merged blindly).
"""
import argparse
import json
import re
import sys
from pathlib import Path

METHOD = re.compile(r'^\.method\s+(?:[\w-]+\s+)*?(\S+\(.*?\)\S+)\s*$', re.M)
FIELD = re.compile(r'^\.field\s+(?:[\w-]+\s+)*?(\S+:\S+?)(?:\s*=.*)?$', re.M)
CLASS = re.compile(r'^\.class\s+(?:[\w-]+\s+)*?(L\S+;)\s*$', re.M)


def blocks(text):
    """-> ({method sig: block text}, {field sig: line text}) for one smali file."""
    methods = {}
    for m in re.finditer(r'^\.method\b.*?^\.end method\s*$', text, re.M | re.S):
        sig = METHOD.match(m.group(0).split('\n', 1)[0]).group(1)
        methods[sig] = m.group(0)
    fields = {}
    for m in re.finditer(r'^\.field\b.*?$(?:\n(?:    .*\n)*?\.end field)?', text, re.M):
        sig = FIELD.match(m.group(0).split('\n', 1)[0]).group(1)
        fields[sig] = m.group(0)
    return methods, fields


def load(root):
    out = {}
    for p in Path(root).rglob('*.smali'):
        text = p.read_text()
        out[CLASS.search(text).group(1)] = (p, text)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('deployed')
    ap.add_argument('donor')
    ap.add_argument('members')
    ap.add_argument('--report')
    args = ap.parse_args()
    want, support, newclass = set(), set(), set()
    for line in Path(args.members).read_text().splitlines():
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        parts = line.split('\t')
        if parts[0] == 'newclass':
            newclass.add(parts[1])
        else:
            (want if parts[0] == 'member' else support).add((parts[1], parts[2]))
    deployed, donor = load(args.deployed), load(args.donor)
    errors, added, copied = [], [], []
    for cls, (dpath, dtext) in sorted(donor.items()):
        if cls not in deployed:
            if cls not in newclass:
                errors.append(f'donor class {cls} is neither deployed nor listed as newclass')
                continue
            target = Path(args.deployed) / dpath.relative_to(args.donor)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(dtext)
            copied.append(cls)
            continue
        bpath, btext = deployed[cls]
        bm, bf = blocks(btext)
        dm, df = blocks(dtext)
        new_m = {s: b for s, b in dm.items() if s not in bm}
        new_f = {s: b for s, b in df.items() if s not in bf}
        for sig in list(new_m) + list(new_f):
            if (cls, sig) not in want and (cls, sig) not in support:
                errors.append(f'{cls}->{sig} added by the donor but not listed')
        if '<clinit>()V' in new_m and '<clinit>()V' in bm:
            errors.append(f'{cls}: both deployed and donor have <clinit>')
        if not new_m and not new_f:
            continue
        text = btext.rstrip('\n') + '\n'
        if new_f:
            field_text = '\n\n'.join(new_f.values())
            last = list(re.finditer(r'^\.field\b.*$', text, re.M))
            at = last[-1].end() if last else re.search(r'^\.source .*$', text, re.M).end()
            text = text[:at] + '\n\n' + field_text + text[at:]
        text += '\n' + '\n\n'.join(new_m.values()) + '\n'
        bpath.write_text(text)
        added += [(cls, s) for s in list(new_m) + list(new_f)]
    for cls, sig in sorted(want):
        if cls in deployed and sig in set().union(*(d.keys() for d in blocks(deployed[cls][1]))):
            errors.append(f'{cls}->{sig} listed as missing but the deployed class already has it')
        elif (cls, sig) not in added:
            errors.append(f'{cls}->{sig} listed but the donor did not supply it')
    for cls in sorted(newclass - set(copied)):
        errors.append(f'newclass {cls} listed but the donor has no such class')
    report = {'added_members': [f'{c}->{s}' for c, s in sorted(added)], 'new_classes': sorted(copied),
              'errors': errors}
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=1) + '\n')
    print(f'merged {len(added)} member(s) into {len({c for c, _ in added})} deployed class(es); '
          f'{len(copied)} new class(es); {len(errors)} error(s)')
    for e in errors:
        print('  ERROR', e)
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
