#!/usr/bin/env python3
"""version-bindings checker + negative-test runner for api_version_bindings.

Usage:
  check_version_bindings.py <version-bindings.json>   # validate the real table
  check_version_bindings.py --negative <dir>          # mutate a temp copy three
      ways (missing path, wrong SHA, duplicate frozen id); each MUST exit
      nonzero and the original file must stay untouched.
"""
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SHA_RE = re.compile(r'[0-9a-f]{64}\Z')
STRENGTHS = {'direct', 'context_only', 'unknown'}


def digest(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


import os
REPO = Path(__file__).resolve().parents[2]
WORKSPACES = Path(os.environ.get('WORKSPACES', str(REPO.parent)))


def resolve(path: str, root: Path) -> Path:
    if path.startswith('$WORKSPACES/'):
        return WORKSPACES / path.removeprefix('$WORKSPACES/')
    return root / path


def validate(doc, root: Path):
    errors = []
    ids = [row.get('frozen_id') for row in doc.get('rows', [])]
    expected = ['FZ-001', 'FZ-002', 'FZ-003', 'FZ-004', 'FZ-005', 'FZ-006', 'FZ-007', 'FZ-008']
    if sorted(ids) != expected:
        errors.append(f'frozen coverage mismatch: {sorted(ids)} != {expected}')
    seen = set()
    for row in doc.get('rows', []):
        rid = row.get('frozen_id', '<missing>')
        if rid in seen:
            errors.append(f'{rid}: duplicate frozen id')
        seen.add(rid)
        if row.get('binding_strength') not in STRENGTHS:
            errors.append(f'{rid}: bad binding_strength')
        for f in ('apk_evidence', 'artifacts', 'sources', 'platform_identity'):
            if not isinstance(row.get(f), list):
                errors.append(f'{rid}: {f} must be a list')
        for s in row.get('sources', []):
            path, sha = s.get('path', ''), s.get('sha256', '')
            if not path or not SHA_RE.fullmatch(sha):
                errors.append(f'{rid}: invalid source entry')
                continue
            try:
                actual = digest(resolve(path, root))
                if actual != sha:
                    errors.append(f'{rid}: SHA drift {path}')
            except OSError as e:
                errors.append(f'{rid}: missing source {path}: {e}')
        if row.get('binding_strength') == 'direct':
            live = [pi for pi in row.get('platform_identity', []) if pi.get('kind') == 'same_run_live']
            if not live:
                errors.append(f"{rid}: direct requires at least one same_run_live platform identity")
            if not row.get('sources'):
                errors.append(f"{rid}: direct with empty sources rejected")
            for pi in row.get('platform_identity', []):
                if pi.get('kind') == 'same_run_live' and not (pi.get('source') and pi.get('evidence') and pi.get('run')):
                    errors.append(f"{rid}: same_run_live identity needs source+evidence+run linkage keys")
        for pi in row.get('platform_identity', []):
            if row.get('binding_strength') == 'direct' and pi.get('kind') != 'same_run_live':
                errors.append(f"{rid}: direct requires same-run live evidence, got kind={pi.get('kind')}")
            if pi.get('kind') == 'planned' and row.get('binding_strength') == 'direct':
                errors.append(f"{rid}: planned version masquerading as direct")
            if pi.get('kind') == 'different_run_context' and row.get('binding_strength') == 'direct':
                errors.append(f"{rid}: cross-run context masquerading as direct")
        for a in row.get('artifacts', []):
            if not a.get('artifact') or not a.get('sha256'):
                errors.append(f'{rid}: artifact entry needs artifact+sha256')
        for v in row.get('apk_evidence', []):
            if not v.get('apk') or not v.get('level'):
                errors.append(f'{rid}: apk entry needs apk+level')
    return errors


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--negative':
        src = Path(sys.argv[2])
        doc = json.loads(src.read_text())
        results = {}
        original_bytes = src.read_bytes()  # snapshot BEFORE any mutation
        with tempfile.TemporaryDirectory() as td:
            # a: missing path
            d = json.loads(json.dumps(doc)); d['rows'][0]['sources'][0]['path'] = 'does/not/exist.json'
            p = Path(td) / 'a.json'; p.write_text(json.dumps(d))
            r = subprocess.run([sys.executable, __file__, str(p)], capture_output=True, text=True)
            results['missing_path_nonzero'] = r.returncode != 0
            # b: wrong sha
            d = json.loads(json.dumps(doc)); d['rows'][1]['sources'][0]['sha256'] = '0' * 64
            p = Path(td) / 'b.json'; p.write_text(json.dumps(d))
            r = subprocess.run([sys.executable, __file__, str(p)], capture_output=True, text=True)
            results['wrong_sha_nonzero'] = r.returncode != 0
            # c: duplicate frozen id
            d = json.loads(json.dumps(doc)); d['rows'][2]['frozen_id'] = d['rows'][1]['frozen_id']
            p = Path(td) / 'c.json'; p.write_text(json.dumps(d))
            r = subprocess.run([sys.executable, __file__, str(p)], capture_output=True, text=True)
            results['duplicate_id_nonzero'] = r.returncode != 0
            # d: planned masquerading as direct
            d = json.loads(json.dumps(doc))
            for row in d['rows']:
                if row.get('platform_identity') and row['platform_identity'][0].get('kind') == 'planned':
                    row['binding_strength'] = 'direct'; break
            p = Path(td) / 'd.json'; p.write_text(json.dumps(d))
            r = subprocess.run([sys.executable, __file__, str(p)], capture_output=True, text=True)
            results['planned_as_direct_nonzero'] = r.returncode != 0
            # e0: direct with empty sources
            d = json.loads(json.dumps(doc)); d['rows'][0]['binding_strength'] = 'direct'
            d['rows'][0]['platform_identity'] = [{'kind': 'same_run_live', 'source': 'x', 'evidence': 'y', 'run': 'z'}]
            d['rows'][0]['sources'] = []
            p = Path(td) / 'e0.json'; p.write_text(json.dumps(d))
            r = subprocess.run([sys.executable, __file__, str(p)], capture_output=True, text=True)
            results['direct_empty_sources_nonzero'] = r.returncode != 0
            # e1: direct with empty platform_identity
            d = json.loads(json.dumps(doc)); d['rows'][0]['binding_strength'] = 'direct'
            d['rows'][0]['platform_identity'] = []
            p = Path(td) / 'e1.json'; p.write_text(json.dumps(d))
            r = subprocess.run([sys.executable, __file__, str(p)], capture_output=True, text=True)
            results['direct_empty_platform_nonzero'] = r.returncode != 0
            # e: cross-run context masquerading as direct
            d = json.loads(json.dumps(doc))
            for row in d['rows']:
                if row.get('platform_identity') and row['platform_identity'][0].get('kind') == 'different_run_context':
                    row['binding_strength'] = 'direct'; break
            p = Path(td) / 'e.json'; p.write_text(json.dumps(d))
            r = subprocess.run([sys.executable, __file__, str(p)], capture_output=True, text=True)
            results['crossrun_as_direct_nonzero'] = r.returncode != 0
            results['original_untouched'] = src.read_bytes() == original_bytes  # compared AFTER all
        ok = all(results.values())
        print(json.dumps({'negative': results, 'all_pass': ok}))
        return 0 if ok else 1
    src = Path(sys.argv[1])
    root = REPO  # sources use repo-relative or $WORKSPACES/westlake-harness/... paths
    doc = json.loads(src.read_text())
    errors = validate(doc, root)
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(json.dumps({'rows': len(doc['rows']), 'ok': True}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
