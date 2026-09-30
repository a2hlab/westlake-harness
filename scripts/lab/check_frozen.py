#!/usr/bin/env python3
"""Refuse any build or deployment that would change a frozen public-API fix (AGENTS.md 做事方式 3).

    check_frozen.py [--registry knowledge/frozen/frozen.json]
                    [--fingerprint runtime-fingerprint.txt]... [--package <generation dir>]...
                    [--source-root <worktree>]...

--fingerprint  a bms_batch runtime-fingerprint.txt ("<sha256>  <path>" lines): every frozen artifact path it
               lists must carry the frozen sha256.
--package      a deploy_generation package: its package.json `live_hashes` must carry the frozen sha256 for
               every frozen artifact path it declares.
--source-root  a worktree of this repo: every frozen source file must exist with the frozen git blob id.

A frozen artifact that a fingerprint/package does not mention is not a violation (that input does not touch
it). Prints one line per checked item and exits 1 on any mismatch. There is no exception list: only the
user can unfreeze, by editing the registry.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]


def load(registry):
    return json.loads(pathlib.Path(registry).read_text())["entries"]


def git_blob(path):
    data = pathlib.Path(path).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def fingerprint_hashes(path):
    out = {}
    for line in pathlib.Path(path).read_text().splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2 and re.fullmatch(r"[0-9a-f]{64}", parts[0]):
            out[parts[1].strip()] = parts[0]
    return out


def package_hashes(path):
    return dict(json.loads((pathlib.Path(path) / "package.json").read_text()).get("live_hashes", {}))


def check_artifacts(entries, hashes, label):
    lines, bad = [], 0
    for e in entries:
        for a in e.get("artifacts", []):
            if a["path"] not in hashes:
                continue
            ok = hashes[a["path"]] == a["sha256"]
            bad += not ok
            lines.append(f"{'ok' if ok else 'FROZEN-VIOLATION'} {e['id']} {label} {a['path']} "
                         f"{hashes[a['path']][:8]} (frozen {a['sha256'][:8]})")
    return lines, bad


def check_sources(entries, root):
    lines, bad = [], 0
    for e in entries:
        for s in e.get("sources", []):
            f = pathlib.Path(root) / s["repo_path"]
            got = git_blob(f) if f.is_file() else "absent"
            ok = got == s["blob"]
            bad += not ok
            lines.append(f"{'ok' if ok else 'FROZEN-VIOLATION'} {e['id']} {root} {s['repo_path']} "
                         f"{got[:8]} (frozen {s['blob'][:8]})")
    return lines, bad


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--registry", default=str(REPO / "knowledge/frozen/frozen.json"))
    ap.add_argument("--fingerprint", action="append", default=[])
    ap.add_argument("--package", action="append", default=[])
    ap.add_argument("--source-root", action="append", default=[])
    a = ap.parse_args(argv)
    entries = load(a.registry)
    lines, bad = [], 0
    for f in a.fingerprint:
        l, b = check_artifacts(entries, fingerprint_hashes(f), f)
        lines += l; bad += b
    for p in a.package:
        l, b = check_artifacts(entries, package_hashes(p), p)
        lines += l; bad += b
    for r in a.source_root:
        l, b = check_sources(entries, r)
        lines += l; bad += b
    print("\n".join(lines))
    print(f"frozen: {len(entries)} entries, {len(lines)} checked, {bad} violation(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
