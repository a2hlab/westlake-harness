#!/usr/bin/env python3
"""Land a lane's deliverable into master from its landing-paths.txt; the outer loop only reads the result.

    land.py <lane-worktree> <landing-paths.txt relative to the worktree> -m "<one-line message>" [--allow-gates]

Why: codex lanes run in the workspace-write sandbox, which keeps every `.git` path read-only even when it is listed
in sandbox_workspace_write.writable_roots (tested 2026-10-01: writable root .octos -> write OK, .git -> "Operation
not permitted"); a lane worktree's index lives in <main>/.git/worktrees/<name>/, so `git add` there always fails.
Rather than give lanes danger-full-access, lanes hand over landing-paths.txt and this script lands it.

Steps (any failure rolls the copy back and commits nothing):
  1. every listed path exists in the worktree, is relative, has no '..', and sits under an allowed prefix
     (benchmark/, scripts/, specs/, tools/spec-checks/tests/, knowledge/smoke/); knowledge/gates/ and
     knowledge/frozen/ need --allow-gates (outer approval);
  2. copy into master; identical files are skipped, tracked files that differ are overwritten and reported;
  3. documentation.json lines (either {"README.md": [...], ".octos/KNOWLEDGE-DIGEST.md": [...]} or
     {"changes": [{"path": ..., "lines": [...]}]}) are inserted exactly once: README rows after the last bold
     benchmark row, DIGEST / RUNBOOK lines appended;
  4. gates: user-path gate on the landed files, check_frozen.py, every landed test_*.py, every landed
     tools/spec-checks/tests/*.rs via cargo test --test;
  5. git add + commit on master; print a paste-ready summary line for the board.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(os.environ.get('LAND_REPO') or Path(__file__).resolve().parents[2])
ALLOWED = ('benchmark/', 'scripts/', 'specs/', 'tools/spec-checks/tests/', 'knowledge/smoke/')
GATED = ('knowledge/gates/', 'knowledge/frozen/')
DOCS = {'README.md', '.octos/KNOWLEDGE-DIGEST.md', '.octos/OPS-RUNBOOK.md'}


def sh(cmd, **kw):
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, **kw)


def read_paths(worktree, listing, allow_gates):
    out, errors = [], []
    for raw in (worktree / listing).read_text().splitlines():
        p = raw.strip()
        if not p or p.startswith('#'):
            continue
        if p.startswith('/') or '..' in Path(p).parts:
            errors.append(f'not a safe relative path: {p}'); continue
        if p.startswith(GATED) and not allow_gates:
            errors.append(f'gate/frozen registry needs --allow-gates (outer approval): {p}'); continue
        if not p.startswith(ALLOWED + (GATED if allow_gates else ())):
            errors.append(f'outside allowed prefixes: {p}'); continue
        if not (worktree / p).exists():
            errors.append(f'missing in worktree: {p}'); continue
        out.append(p)
    return out, errors


def expand(worktree, paths):
    files = []
    for p in paths:
        src = worktree / p
        files += [str(f.relative_to(worktree)) for f in sorted(src.rglob('*')) if f.is_file()] if src.is_dir() else [p]
    return sorted(set(files))


def doc_changes(doc):
    if 'changes' in doc:
        return [(c['path'], c['lines']) for c in doc['changes']]
    return [(k, v) for k, v in doc.items() if k in DOCS]


def insert_docs(changes):
    touched = []
    for path, lines in changes:
        if path not in DOCS:
            raise SystemExit(f'documentation.json names a non-doc path: {path}')
        f = REPO / path
        text = f.read_text(encoding='utf-8')
        rows = text.split('\n')
        new = [ln for ln in lines if ln not in rows]
        if not new:
            continue
        if path == 'README.md':
            idx = max(i for i, l in enumerate(rows) if l.startswith('| **`benchmark/'))
            rows[idx + 1:idx + 1] = new
            f.write_text('\n'.join(rows), encoding='utf-8')
        else:
            f.write_text(text.rstrip('\n') + '\n' + '\n'.join(new) + '\n', encoding='utf-8')
        touched.append(path)
    return touched


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('worktree', type=Path)
    ap.add_argument('listing')
    ap.add_argument('-m', '--message', required=True)
    ap.add_argument('--allow-gates', action='store_true')
    ap.add_argument('--no-commit', action='store_true', help='run everything, then leave the result staged')
    args = ap.parse_args(argv)
    wt = args.worktree.expanduser().resolve()
    if sh(['git', 'status', '--porcelain', '--untracked-files=no']).stdout.strip():
        sys.exit('master has uncommitted tracked changes; land onto a clean tree')
    paths, errors = read_paths(wt, args.listing, args.allow_gates)
    if errors:
        sys.exit('REFUSE:\n  ' + '\n  '.join(errors))
    files = expand(wt, paths)
    listing_sha = hashlib.sha256((wt / args.listing).read_bytes()).hexdigest()
    created, overwritten = [], []
    for rel in files:
        dst = REPO / rel
        if dst.exists():
            if dst.read_bytes() == (wt / rel).read_bytes():
                continue
            tracked = sh(['git', 'ls-files', '--error-unmatch', rel]).returncode == 0
            if tracked:
                overwritten.append(rel)
        else:
            created.append(rel)
    docs = [p for p in files if p.endswith('documentation.json')]
    failures = []
    try:
        for rel in created + overwritten:
            (REPO / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(wt / rel, REPO / rel)
        touched = []
        for d in docs:
            touched += insert_docs(doc_changes(json.loads((REPO / d).read_text())))
        r = sh([sys.executable, 'scripts/lab/check_user_paths.py', *files, *touched])
        if r.returncode:
            failures.append('user-paths: ' + r.stdout.strip().splitlines()[-1])
        r = sh([sys.executable, 'scripts/lab/check_frozen.py'])
        if r.returncode:
            failures.append('frozen: ' + r.stdout.strip()[-300:])
        for t in [f for f in files if Path(f).name.startswith('test_') and f.endswith('.py')]:
            r = sh([sys.executable, t], timeout=600)
            if r.returncode:
                failures.append(f'{t}: ' + (r.stdout + r.stderr).strip()[-300:])
        for t in [f for f in files if f.startswith('tools/spec-checks/tests/') and f.endswith('.rs')]:
            r = subprocess.run(['cargo', 'test', '--test', Path(t).stem], cwd=REPO / 'tools/spec-checks',
                               capture_output=True, text=True, timeout=900)
            if r.returncode:
                failures.append(f'cargo {Path(t).stem}: ' + (r.stdout + r.stderr).strip()[-300:])
        if failures:
            raise RuntimeError('gates failed')
        sh(['git', 'add', '-f', *files, *touched])
        if not args.no_commit:
            head = subprocess.run(['git', '-C', str(wt), 'rev-parse', '--short', 'HEAD'], capture_output=True,
                                  text=True).stdout.strip()
            c = sh(['git', 'commit', '-q', '-m', f'{args.message} (landed from {wt.name}@{head}, '
                                                f'{len(files)} files, listing {listing_sha[:12]})'])
            if c.returncode:
                raise RuntimeError('commit failed: ' + c.stderr.strip()[-300:])
        commit = sh(['git', 'rev-parse', '--short', 'HEAD']).stdout.strip()
        print(f'LANDED {commit}: {len(files)} files ({len(created)} new, {len(overwritten)} overwritten), '
              f'docs {touched or "none"}, listing sha256 {listing_sha[:12]}; user-paths 0, frozen 0, '
              f'tests {sum(1 for f in files if Path(f).name.startswith("test_"))} py + '
              f'{sum(1 for f in files if f.endswith(".rs"))} cargo OK')
        return 0
    except Exception as exc:
        for rel in created:
            (REPO / rel).unlink(missing_ok=True)
        for rel in overwritten + sorted(DOCS):
            if (REPO / rel).exists():
                sh(['git', 'checkout', '--', rel])
        sh(['git', 'reset', '-q'])
        print('NOT LANDED: ' + str(exc) + ('\n  ' + '\n  '.join(failures) if failures else ''), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
