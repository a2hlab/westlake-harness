#!/usr/bin/env python3
"""List lane deliverables (landing-paths*.txt in lane worktrees) whose files are not on master yet.

Patrol aid for the outer loop (board R2 2026-10-02 18:50, missed-board-read: a cc-wiki delivery sat 70 min
unreviewed because the patrol read the newest board lines instead of reconciling deliveries against master).
For every listing under <worktree>/benchmark/ touched within --hours, each listed path is compared with the
master copy by content:

  landed        every listed file is byte-identical on master
  master-newer  some file differs, but master committed that path after the lane last wrote it (superseded)
  UNLANDED      some file is missing on master or differs and the lane copy is the newer one
  acked         UNLANDED, but knowledge/gates/unlanded-ack.json names this listing with the same listing SHA
                (deliberately not landed: raw window evidence superseded by an outer sign-off dir, a merge-landed
                inventory, ...). Editing the listing changes its SHA and resurfaces it.

Read-only: never copies, commits or touches a lane tree. Exit 0 always; the last line is `UNLANDED <n>`.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
from lab_paths import workspaces  # noqa: E402

ACK_JSON = REPO / 'knowledge/gates/unlanded-ack.json'


def load_acks(path):
    """{(worktree, listing): listing_sha256}; a missing table means nothing is acked (fail closed)."""
    if not path.is_file():
        return {}
    return {(e['worktree'], e['listing']): e['listing_sha256'] for e in json.loads(path.read_text())['acks']}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def master_commit_time(repo, rel):
    out = subprocess.run(['git', '-C', str(repo), 'log', '-1', '--format=%ct', '--', rel],
                         capture_output=True, text=True).stdout.strip()
    return int(out) if out else None


def listed_paths(listing):
    for line in listing.read_text(errors='replace').splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            yield line


def classify(worktree, listing, repo):
    missing, newer_lane, newer_master, same = [], [], [], 0
    for rel in listed_paths(listing):
        lane = worktree / rel
        mast = repo / rel
        if not lane.is_file():
            continue  # the lane's own listing names a file it no longer has; land.py would refuse it anyway
        if not mast.is_file():
            missing.append(rel)
            continue
        if sha(lane) == sha(mast):
            same += 1
            continue
        ct = master_commit_time(repo, rel)
        (newer_master if ct is not None and ct >= lane.stat().st_mtime else newer_lane).append(rel)
    if missing or newer_lane:
        status = 'UNLANDED'
    elif newer_master:
        status = 'master-newer'
    else:
        status = 'landed'
    return {'status': status, 'same': same, 'missing': missing, 'lane_newer': newer_lane,
            'master_newer': newer_master}


def lane_worktrees(ws, repo):
    for d in sorted(ws.glob('westlake-harness-*')):
        if d.is_dir() and (d / '.git').exists() and d.resolve() != repo.resolve():
            yield d


def scan(ws, repo, hours, now=None, acks=None):
    now = now or time.time()
    acks = acks or {}
    rows = []
    for wt in lane_worktrees(ws, repo):
        bench = wt / 'benchmark'
        if not bench.is_dir():
            continue
        for listing in bench.glob('**/landing-paths*.txt'):
            mt = listing.stat().st_mtime
            if now - mt > hours * 3600:
                continue
            r = classify(wt, listing, repo)
            r.update(worktree=wt.name, listing=str(listing.relative_to(wt)), mtime=mt)
            if r['status'] == 'UNLANDED' and acks.get((r['worktree'], r['listing'])) == sha(listing):
                r['status'] = 'acked'
            rows.append(r)
    rows.sort(key=lambda r: r['mtime'])
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--hours', type=float, default=24)
    ap.add_argument('--workspaces', type=Path)
    ap.add_argument('--repo', type=Path, default=REPO)
    ap.add_argument('--all', action='store_true', help='also print landed / master-newer / acked rows')
    ap.add_argument('--ack-json', type=Path, default=ACK_JSON)
    a = ap.parse_args(argv)
    ws = a.workspaces or Path(workspaces())
    rows = scan(ws, a.repo, a.hours, acks=load_acks(a.ack_json))
    n = 0
    for r in rows:
        if r['status'] == 'UNLANDED':
            n += 1
        elif not a.all:
            continue
        stamp = time.strftime('%m-%d %H:%M', time.localtime(r['mtime']))
        detail = ''
        if r['missing'] or r['lane_newer']:
            first = (r['missing'] + r['lane_newer'])[0]
            detail = f" missing={len(r['missing'])} lane_newer={len(r['lane_newer'])} e.g. {first}"
        print(f"{r['status']:<12} {stamp} {r['worktree']}/{r['listing']} same={r['same']}{detail}")
    print(f'UNLANDED {n}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
