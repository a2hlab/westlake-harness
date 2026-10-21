#!/usr/bin/env python3
"""Re-hash every crosswalk reference and expected input against the main repository (read-only).
Exit 1 on any drift, missing reference, or a status that upgrades the recorded verification scope."""
import argparse, hashlib, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(); ap.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[2])
root = ap.parse_args().source_root.resolve()
c = json.loads((HERE / 'crosswalk.json').read_text()); bad = []; n = 0
def chk(rel, want):
    global n
    p = root / rel
    if not p.is_file() or p.is_symlink(): bad.append(('missing', rel)); return
    if hashlib.sha256(p.read_bytes()).hexdigest() != want: bad.append(('sha_drift', rel))
    n += 1
for rel, want in c['expected_input_sha256'].items(): chk(rel, want)
for r in c['rows']:
    for g in ('source', 'build', 'evidence'):
        for x in r[g]: chk(x['path'], x['sha256'])
    for path, st in r['observed_status'].items():
        if path not in [e['path'] for e in r['evidence']]: bad.append(('status_path', path))
need = {'DRAFT-G08-ZIP-COMMENT': ['NOT_STARTED', 'NOT_TESTED_WITH_PATCH'], 'DRAFT-G13-DEVICE-WINDOW': ['not executed as of receipt'],
        'DRAFT-T35-WHITESCREEN': ['INFERRED'], 'DRAFT-T36-R4C-CANDIDATE': ['NOT_DEPLOYED', 'NOT fixed'], 'DRAFT-T38-WINDOW': ['UNVALIDATED'],
        'DRAFT-G09-LIBINSTALLS-BUILD': ['not deployed as of receipt']}
rows = {r['id']: r for r in c['rows']}
for rid, words in need.items():
    for w in words:
        if w not in rows[rid]['status']: bad.append(('scope_upgraded', rid, w))
if any(r['frozen'] for r in c['rows']): bad.append(('frozen',))
if any('not authorized' in r['status'] or 'not authorized' in r['deployment'] for r in c['rows']): bad.append(('authorization_misstated',))
if 'as of the cited receipt' not in c.get('status_semantics', ''): bad.append(('status_semantics_missing',))
if 'Boat' not in c['not_substituted']: bad.append(('boat_substitution_note',))
gaps = json.loads((HERE / 'gaps.json').read_text())
if not any(g['row'] == '*' for g in gaps): bad.append(('authoritative_table_gap_missing',))
print(json.dumps({'source_root_head_recorded': c['source_root_head'], 'refs_checked': n, 'rows': len(c['rows']), 'gaps': len(gaps), 'problems': bad}))
sys.exit(1 if bad else 0)
