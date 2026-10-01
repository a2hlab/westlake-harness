#!/usr/bin/env python3
"""Land a lane's deliverable into master from its landing-paths.txt; the outer loop only reads the result.

    land.py <lane-worktree> <landing-paths.txt relative to the worktree> -m "<one-line message>" [--allow-gates]
    land.py <lane-worktree> <landing-paths.txt> -m x --preflight     # lane-side: path / size gates, copies nothing

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
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(os.environ.get('LAND_REPO') or Path(__file__).resolve().parents[2])
ALLOWED = ('benchmark/', 'scripts/', 'specs/', 'tools/spec-checks/tests/', 'knowledge/smoke/')
GATED = ('knowledge/gates/', 'knowledge/frozen/')
DOCS = {'README.md', '.octos/KNOWLEDGE-DIGEST.md', '.octos/OPS-RUNBOOK.md'}
MAX_BYTES = 1024 * 1024


def lab_env():
    """Gates run with the lab venv first on PATH (androguard etc.), as the lanes ran them (env.md: westlake-inputs/venv)."""
    env = dict(os.environ)
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import lab_paths
        venv = lab_paths.inputs() / 'venv/bin'
        if venv.is_dir():
            env['PATH'] = f'{venv}:{env.get("PATH", "")}'
    except Exception:
        pass
    return env


ENV = lab_env()
PY = next((str(Path(d) / 'python') for d in ENV.get('PATH', '').split(':')[:1] if (Path(d) / 'python').exists()),
          sys.executable)


def sh(cmd, **kw):
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, env=ENV, **kw)


def read_paths(worktree, listing, allow_gates):
    out, errors = [], []
    for raw in Path(listing if Path(listing).is_absolute() else worktree / listing).read_text().splitlines():
        p = raw.strip()
        if not p or p.startswith('#'):
            continue
        if ' (' in p or '\t' in p:
            errors.append(f'annotated line (one path per line; mark references to run dirs / sources with a leading #): {p}'); continue
        if p.startswith('/') or '..' in Path(p).parts:
            errors.append(f'not a safe relative path: {p}'); continue
        if p in DOCS:
            errors.append(f'{p} must not be copied whole (it would drop master lines); put its new lines in documentation.json'); continue
        if p.startswith(GATED) and not allow_gates:
            errors.append(f'gate/frozen registry needs --allow-gates (outer approval): {p}'); continue
        if not p.startswith(ALLOWED + (GATED if allow_gates else ())):
            errors.append(f'outside allowed prefixes: {p}'); continue
        if not (worktree / p).exists():
            errors.append(f'missing in worktree: {p}'); continue
        out.append(p)
    return out, errors


def cited_evidence():
    """Every string in the gate / frozen registries: approved rows cite their evidence files by repo path."""
    out = []

    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, str):
            out.append(o)
    for reg in sorted((REPO / 'knowledge').glob('*/*.json')):
        if reg.parent.name in ('gates', 'frozen'):
            try:
                walk(json.loads(reg.read_text(encoding='utf-8')))
            except ValueError:
                pass
    return out


def expand(worktree, paths):
    files = []
    for p in paths:
        src = worktree / p
        files += [str(f.relative_to(worktree)) for f in sorted(src.rglob('*')) if f.is_file()] if src.is_dir() else [p]
    return sorted(set(files))


DATA_SUFFIXES = {'.csv', '.tsv', '.json', '.jsonl', '.md'}
HOME_PATH = re.compile(r'/Users/[^/\s"\',]+/')


def home_paths_in_data(worktree, files):
    """Lane-written tables that carry this Mac's home paths. check_user_paths.py exempts data suffixes because raw
    recorded evidence may hold paths, but a lane's own CSV/JSON should cite runs as $WORKSPACES/... (2026-10-01: one
    lane wrote absolute /Users paths into three deliverables in one evening although each dispatch asked otherwise)."""
    out = []
    for f in files:
        if Path(f).suffix in DATA_SUFFIXES:
            n = len(HOME_PATH.findall((worktree / f).read_text(errors='replace')))
            if n:
                out.append((f, n))
    return out


def empty_csvs(worktree, files):
    """CSV deliverables with a header and no data rows. Not refused (an empty scan result is legitimate), but printed:
    2026-10-01 20:13 a lane reported "30 keys / 38 rows" over a CSV that held only its header."""
    out = []
    for f in files:
        if f.endswith('.csv'):
            lines = [l for l in (worktree / f).read_text(errors='replace').splitlines() if l.strip()]
            if len(lines) <= 1:
                out.append(f)
    return out


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
        # an entry may span lines ("## heading\nbody"): it is present if its whole text already is (2026-10-01 a
        # documentation.json listed and also passed with --docs inserted a two-line entry twice)
        new = [ln for ln in lines if ln not in rows and ln not in text]
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
    ap.add_argument('--docs', type=Path, help='documentation.json kept outside the worktree (in addition to listed ones)')
    ap.add_argument('--no-commit', action='store_true', help='run everything, then leave the result staged')
    ap.add_argument('--allow-large', action='store_true', help='land files over 1 MiB (outer-reviewed)')
    ap.add_argument('--preflight', action='store_true',
                    help='lane-side check: listing, size and user-path gates on the worktree files; copies nothing')
    ap.add_argument('--allow-drop-lines', action='store_true',
                    help='overwrite a master .md even though master has lines the lane copy lacks (outer-reviewed)')
    ap.add_argument('--allow-home-paths', action='store_true',
                    help='preflight: accept /Users/<name>/ inside data files (raw recorded evidence only)')
    args = ap.parse_args(argv)
    wt = args.worktree.expanduser().resolve()
    if not args.preflight and sh(['git', 'status', '--porcelain', '--untracked-files=no']).stdout.strip():
        sys.exit('master has uncommitted tracked changes; land onto a clean tree')
    paths, errors = read_paths(wt, args.listing, args.allow_gates)
    if errors:
        sys.exit('REFUSE:\n  ' + '\n  '.join(errors))
    files = expand(wt, paths)
    if args.preflight:
        # retro 18 (2026-10-01): lane build scripts carried hard-coded /Users/<name> paths four times in one evening and
        # were only caught when the outer loop landed them; lanes run this before reporting (the global git hooks path
        # is not ours to change, so no pre-commit hook).
        big = [f for f in files if (wt / f).stat().st_size > MAX_BYTES]
        lab = Path(__file__).resolve().parent
        r = subprocess.run([sys.executable, str(lab / 'check_user_paths.py'), '--root', str(wt), '--exceptions',
                            str(lab.parents[1] / 'knowledge/gates/user-path-exceptions.json'), *files],
                           capture_output=True, text=True)
        hits = [l for l in r.stdout.splitlines() if l.startswith('USER-PATH')]
        for f in big:
            print(f'TOO LARGE {f} ({(wt / f).stat().st_size // 1024} KiB)')
        for h in hits:
            print(h[:220])
        homes = [] if args.allow_home_paths else home_paths_in_data(wt, files)
        for f in empty_csvs(wt, files):
            print(f'EMPTY-CSV {f} (header only -- make sure the numbers you report come from a non-empty table)')
        for f, n in homes:
            print(f'HOME-PATH-IN-DATA {f} x{n} (write $WORKSPACES/... or a repo-relative path; raw recorded evidence: '
                  f'--allow-home-paths)')
        ok = not big and r.returncode == 0 and not homes
        print(f'preflight {"OK" if ok else "FAILED"}: {len(files)} files, {len(big)} too large, {len(hits)} user-path '
              f'hit(s), {len(homes)} data file(s) with home paths')
        return 0 if ok else 1
    # AGENTS: large binaries and raw logs stay out of the repo (2026-10-01: a listing carried a 76k-line run hilog as
    # "evidence"); land an excerpt with original line numbers and cite the run directory instead.
    big = [f for f in files if (wt / f).stat().st_size > MAX_BYTES and not args.allow_large]
    if big:
        sys.exit(f'REFUSE: over {MAX_BYTES // 1024} KiB (land an excerpt, cite the run dir; --allow-large if reviewed):\n  '
                 + '\n  '.join(f'{f} ({(wt / f).stat().st_size // 1024} KiB)' for f in big))
    listing_path = Path(args.listing) if Path(args.listing).is_absolute() else wt / args.listing
    listing_sha = hashlib.sha256(listing_path.read_bytes()).hexdigest()
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
    # 2026-10-01: the N10b smoke-marker rebuild rewrote batch-u8-native-gate.json in place, the file the approved
    # 342198db exception rows cite as evidence; landing it would have swapped the evidence under approved rows.
    cites = cited_evidence() if overwritten else []
    pinned = [rel for rel in overwritten if any(rel in s for s in cites)]
    if pinned:
        sys.exit('REFUSE: approved gate/frozen rows cite these files as evidence; land the new version under a new '
                 'name instead of overwriting:\n  ' + '\n  '.join(pinned))
    # 2026-10-01 19:31: a lane re-landed a README-style .md from its worktree and silently erased the outer loop's
    # reading appended to master's copy in between. A prose file must not lose master lines on overwrite.
    lost = {}
    for rel in overwritten:
        # a file only ever written by landings from this same worktree is the lane's own document: its rewrite may
        # drop its old lines (20:41 a lane's legitimate design.md rewrite was refused); master edits make it shared
        history = sh(['git', 'log', '--format=%s', '--', rel]).stdout.splitlines()
        if history and all(f'landed from {wt.name}' in s for s in history):
            continue
        if rel.endswith('.md'):
            mine = set((wt / rel).read_text(errors='replace').splitlines())
            gone = [l for l in (REPO / rel).read_text(errors='replace').splitlines() if l.strip() and l not in mine]
            if gone:
                lost[rel] = gone
    if lost and not args.allow_drop_lines:
        sys.exit('REFUSE: overwriting would drop lines master has and the lane copy lacks (merge them into the lane '
                 'file first, or --allow-drop-lines if reviewed):\n  ' +
                 '\n  '.join(f'{rel}: {len(g)} line(s), e.g. {g[0][:100]!r}' for rel, g in lost.items()))
    for f in empty_csvs(wt, files):
        print(f'EMPTY-CSV {f} (header only; check the lane report does not cite rows from it)')
    docs =[p for p in files if p.endswith('documentation.json')]
    failures = []
    try:
        for rel in created + overwritten:
            (REPO / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(wt / rel, REPO / rel)
        touched = []
        for d in docs:
            touched += insert_docs(doc_changes(json.loads((REPO / d).read_text())))
        if args.docs:
            touched += insert_docs(doc_changes(json.loads(args.docs.read_text())))
        r = sh([sys.executable, 'scripts/lab/check_user_paths.py', *files, *touched])
        if r.returncode:
            hits = [l for l in r.stdout.splitlines() if l.startswith('USER-PATH')][:5]
            failures.append('user-paths: ' + r.stdout.strip().splitlines()[-1] + ''.join('\n    ' + h[:200] for h in hits))
        r = sh([sys.executable, 'scripts/lab/check_frozen.py'])
        if r.returncode:
            failures.append('frozen: ' + r.stdout.strip()[-300:])
        for t in [f for f in files if Path(f).name.startswith('test_') and f.endswith('.py')]:
            r = sh([PY, t], timeout=600)
            if r.returncode:
                failures.append(f'{t}: ' + (r.stdout + r.stderr).strip()[-300:])
        for t in [f for f in files if f.startswith('tools/spec-checks/tests/') and f.endswith('.rs')]:
            r = subprocess.run(['cargo', 'test', '--test', Path(t).stem], cwd=REPO / 'tools/spec-checks',
                               capture_output=True, text=True, timeout=900, env=ENV)
            if r.returncode:
                failures.append(f'cargo {Path(t).stem}: ' + (r.stdout + r.stderr).strip()[-300:])
        if failures:
            raise RuntimeError('gates failed')
        sh(['git', 'add', '-f', *files, *touched])
        # 2026-10-01 21:22: a lane had already landed the same listing itself; `git commit` then exits 1 with its
        # "nothing to commit" on stdout and an empty stderr, which printed a bare "commit failed:".
        if not args.no_commit and sh(['git', 'diff', '--cached', '--quiet']).returncode == 0:
            commit = sh(['git', 'rev-parse', '--short', 'HEAD']).stdout.strip()
            print(f'ALREADY LANDED: master {commit} already has these {len(files)} files byte for byte; nothing to commit')
            return 0
        if not args.no_commit:
            head = subprocess.run(['git', '-C', str(wt), 'rev-parse', '--short', 'HEAD'], capture_output=True,
                                  text=True).stdout.strip()
            c = sh(['git', 'commit', '-q', '-m', f'{args.message} (landed from {wt.name}@{head}, '
                                                f'{len(files)} files, listing {listing_sha[:12]})'])
            if c.returncode:
                raise RuntimeError('commit failed: ' + (c.stdout + c.stderr).strip()[-300:])
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
