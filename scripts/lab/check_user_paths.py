#!/usr/bin/env python3
"""Refuse absolute paths tied to a user's home in tracked scripts (user rule 2026-09-30).

    check_user_paths.py [--root <repo>] [--exceptions knowledge/gates/user-path-exceptions.json] [path...]

Scans `git ls-files` of the repo (or only the given paths), skipping documentation/data files
(.md .json .jsonl .txt .csv .log .tsv .xml .html and images) and binaries; a symlink is checked by its
target. Every `/Users/<name>` or `/home/<name>` that is not part of a longer path word (so
/storage/Users/... is not a home) is a hit. Scripts resolve such places instead: WORKSPACES (lab_paths.sh /
lab_paths.py), $HOME / Path.home(), the script's own location, or an env var.

Strict by default (AGENTS.md 做事方式 5): the gate logic does not change; loosening means adding an entry to
the exception table, tightening means deleting one. Each entry has `pattern`, `reason`, `evidence`:
  - pattern starting with "/": an allowed absolute path prefix (e.g. the original author's build path);
    optional `files`: fnmatch globs limiting where that prefix is allowed;
  - otherwise: an fnmatch glob over repo-relative file paths (e.g. recorded evidence) -- the whole file is
    exempt.
Prints file:line for every hit not covered and exits 1; exit 2 if the exception table is malformed.
"""
import argparse
import fnmatch
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
SKIP_SUFFIXES = {'.md', '.json', '.jsonl', '.txt', '.csv', '.log', '.tsv', '.xml', '.html', '.htm',
                 '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.ico', '.pdf'}
NAME = r'[A-Za-z0-9_][A-Za-z0-9_.@-]*'
HIT = re.compile(r'(?<![A-Za-z0-9_.])/(?:Users|home)/' + NAME +
                 # an agent session scratchpad (…/claude-<uid>/-Users-<name>-…): user-named and gone after the session
                 r'|(?<![A-Za-z0-9_.])/(?:private/)?tmp/claude-\d+/')
WORDCHAR = re.compile(r'[A-Za-z0-9_.@-]')


def repo_root(start):
    try:
        out = subprocess.run(['git', '-C', str(start), 'rev-parse', '--show-toplevel'],
                             capture_output=True, text=True, check=True).stdout.strip()
        return pathlib.Path(out)
    except (OSError, subprocess.CalledProcessError):
        return None


def load_exceptions(path):
    data = json.loads(pathlib.Path(path).read_text())
    entries = data['exceptions'] if isinstance(data, dict) else data
    problems = []
    for i, e in enumerate(entries):
        for k in ('pattern', 'reason', 'evidence'):
            if not isinstance(e.get(k), str) or not e[k].strip():
                problems.append(f'exception #{i}: missing {k}')
        files = e.get('files', [])
        if isinstance(files, str):
            e['files'] = files = [files]
        if files and not str(e.get('pattern', '')).startswith('/'):
            problems.append(f'exception #{i}: `files` only applies to a path-prefix pattern')
    return entries, problems


def prefix_allowed(line, start, entries, rel):
    for e in entries:
        p = e['pattern']
        if not p.startswith('/') or not line.startswith(p, start):
            continue
        end = start + len(p)
        if not p.endswith('/') and end < len(line) and WORDCHAR.match(line[end]):
            continue                                  # prefix .../a/b must not allow .../a/bc
        if e.get('files') and not any(fnmatch.fnmatchcase(rel, g) for g in e['files']):
            continue
        return True
    return False


def file_exempt(rel, entries):
    return any(not e['pattern'].startswith('/') and fnmatch.fnmatchcase(rel, e['pattern']) for e in entries)


def scan_text(rel, text, entries):
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        for m in HIT.finditer(line):
            if not prefix_allowed(line, m.start(), entries, rel):
                hits.append((rel, n, m.group(0), line.strip()))
    return hits


def scan(root, rels, entries):
    hits = []
    for rel in rels:
        if pathlib.PurePosixPath(rel).suffix.lower() in SKIP_SUFFIXES or file_exempt(rel, entries):
            continue
        p = root / rel
        if p.is_symlink():
            hits += scan_text(rel, '-> ' + str(p.readlink()), entries)
            continue
        if not p.is_file():
            continue
        raw = p.read_bytes()
        if b'\0' in raw[:8192]:
            continue                                   # binary
        hits += scan_text(rel, raw.decode('utf-8', 'replace'), entries)
    return hits


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--root', type=pathlib.Path)
    ap.add_argument('--exceptions', type=pathlib.Path)
    ap.add_argument('paths', nargs='*', help='repo-relative paths to scan (default: git ls-files)')
    args = ap.parse_args(argv)
    root = (args.root or repo_root(HERE) or repo_root(pathlib.Path.cwd()) or HERE.parents[1]).resolve()
    table = args.exceptions or root / 'knowledge/gates/user-path-exceptions.json'
    try:
        entries, problems = load_exceptions(table)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'user-paths: cannot read exception table {table}: {exc}', file=sys.stderr)
        return 2
    if problems:
        print('\n'.join('user-paths: ' + p for p in problems), file=sys.stderr)
        return 2
    if args.paths:
        rels = [str(pathlib.Path(p).resolve().relative_to(root)) if pathlib.Path(p).is_absolute() else p
                for p in args.paths]
    else:
        rels = subprocess.run(['git', '-C', str(root), 'ls-files', '-z'], capture_output=True,
                              check=True).stdout.decode('utf-8', 'replace').split('\0')
        rels = [r for r in rels if r]
    hits = scan(root, rels, entries)
    for rel, n, path, line in hits:
        print(f'USER-PATH {rel}:{n}: {path}  | {line[:160]}')
    print(f'user-paths: {len(rels)} files, {len(entries)} exceptions, {len(hits)} violation(s)'
          + ('' if not hits else ' -- use WORKSPACES/$HOME/script-relative paths, or add a reviewed exception'))
    return 1 if hits else 0


if __name__ == '__main__':
    raise SystemExit(main())
