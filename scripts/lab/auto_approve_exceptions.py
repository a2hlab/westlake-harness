#!/usr/bin/env python3
"""Auto-approve native-gate exceptions that are identical to already-approved findings; list only the new ones.

    auto_approve_exceptions.py --candidate <report.json> --baseline <report.json> [--baseline ...]
                               [--candidate-manifest <sha prefix>] [--board <abs board.md>] [--apply]

Rule (user, 2026-10-01): an exception whose finding is identical to a finding already approved for an earlier
manifest, with zero new findings, is approved by rule and recorded on the board; only new findings go to the outer
loop for review, one by one. Identity is semantic: the finding JSON minus issue_id / disposition / exception and
minus evidence line numbers and registration sequence indexes (issue_id itself binds the manifest and inputs hashes,
so it always changes; inserting one registration earlier shifts every later sequence number).

A baseline report is any JSON containing a native gate report ({"package_manifest_sha256", "gates": {N1|N2:
{"findings": [...]}}}) whose findings carry disposition EXCEPTED — e.g. a production dry-run of the signed state.
Without --apply nothing is written: the script prints how many findings match and which are new.
With --apply the matched findings are appended to knowledge/gates/native-predeploy-exceptions.json as rows with
approved_by "auto-identical(outer rule 2026-10-01)" and "auto_from" naming the approved source row; the new
findings are written to <candidate dir>/needs-outer-review.json. Exit 0 = nothing new, 3 = new findings remain.
"""
import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REGISTRY = REPO / 'knowledge/gates/native-predeploy-exceptions.json'
AUTO = 'auto-identical(outer rule 2026-10-01)'
VOLATILE = {'issue_id', 'disposition', 'exception'}


def reports(obj):
    if isinstance(obj, dict):
        if isinstance(obj.get('gates'), dict) and 'package_manifest_sha256' in obj and \
                any(isinstance(g, dict) and 'findings' in g for g in obj['gates'].values()):
            yield obj
        for v in obj.values():
            yield from reports(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from reports(v)


def normalize(o):
    if isinstance(o, dict):
        return {k: normalize(v) for k, v in sorted(o.items())
                if k not in VOLATILE and not (k in ('line', 'sequence') and isinstance(v, int))}
    if isinstance(o, list):
        return [normalize(v) for v in o]
    return o


def fingerprint(gate, finding):
    return json.dumps([gate, normalize(finding)], sort_keys=True, ensure_ascii=False)


def pick(path, manifest=None):
    found = list(reports(json.loads(Path(path).read_text())))
    if manifest:
        found = [r for r in found if r['package_manifest_sha256'].startswith(manifest)]
    if not found:
        raise SystemExit(f'no native gate report{" for " + manifest if manifest else ""} in {path}')
    return found[0]


def classify(candidate, baselines, registry_rows):
    approved = {}
    by_id = {(r['package_manifest_sha256'], r['issue_id']): r for r in registry_rows}
    for base in baselines:
        for gate, g in base['gates'].items():
            for f in g.get('findings', []):
                row = by_id.get((base['package_manifest_sha256'], f.get('issue_id')))
                if f.get('disposition') == 'EXCEPTED' and row:
                    approved.setdefault(fingerprint(gate, f), row)
    matched, new = [], []
    for gate, g in candidate['gates'].items():
        for f in g.get('findings', []):
            src = approved.get(fingerprint(gate, f))
            (matched if src else new).append((gate, f, src))
    return matched, new


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--candidate', required=True, type=Path)
    ap.add_argument('--candidate-manifest')
    ap.add_argument('--baseline', required=True, type=Path, action='append')
    ap.add_argument('--board')
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args(argv)
    cand = pick(args.candidate, args.candidate_manifest)
    bases = [pick(b) for b in args.baseline]
    reg = json.loads(REGISTRY.read_text())
    matched, new = classify(cand, bases, reg['exceptions'])
    have = {(r['gate'], r['package_manifest_sha256'], r['issue_id']) for r in reg['exceptions']}
    msha, isha = cand['package_manifest_sha256'], cand['inputs_sha256']
    print(f'candidate {msha[:12]}: {len(matched)} identical to approved findings, {len(new)} new')
    for gate, f, _ in new:
        print(f'  NEW {gate} {f.get("issue_id", "")[:12]} {json.dumps(normalize(f), ensure_ascii=False)[:200]}')
    if not args.apply:
        return 3 if new else 0
    now = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    rel = lambda p: str(Path(p).resolve().relative_to(REPO))
    added = 0
    for gate, f, src in matched:
        if (gate, msha, f['issue_id']) in have:
            continue
        reg['exceptions'].append({
            'gate': gate, 'package_manifest_sha256': msha, 'inputs_sha256': isha, 'issue_id': f['issue_id'],
            'reason': f'Identical to approved finding {src["issue_id"][:12]} of manifest {src["package_manifest_sha256"][:12]} '
                      f'(semantic match, evidence line numbers ignored); approved by the identical-finding rule.',
            'removal_condition': src['removal_condition'],
            'evidence': [rel(args.candidate)] + [rel(b) for b in args.baseline],
            'approved_by': AUTO, 'approved_at': now,
            'auto_from': {'package_manifest_sha256': src['package_manifest_sha256'], 'issue_id': src['issue_id']}})
        added += 1
    REGISTRY.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + '\n')
    review = args.candidate.parent / 'needs-outer-review.json'
    review.write_text(json.dumps({'package_manifest_sha256': msha, 'inputs_sha256': isha,
                                  'new_findings': [dict(f, gate=g) for g, f, _ in new]}, ensure_ascii=False, indent=1))
    msg = (f'ACK(95): {now} 外环(claude) 例外自动审批(规则:与已批发现完全相同即通过):manifest {msha[:12]} 的 '
           f'{len(matched)} 条发现与已批版本逐条相同,自动写入 knowledge/gates/native-predeploy-exceptions.json(新增 {added} 行,'
           f'approved_by={AUTO});**新增发现 {len(new)} 条**待外环逐条审({rel(review)})。')
    print(msg)
    if args.board:
        subprocess.run([str(REPO / 'scripts/lab/board_append.sh'), args.board, msg], check=False)
    return 3 if new else 0


if __name__ == '__main__':
    sys.exit(main())
