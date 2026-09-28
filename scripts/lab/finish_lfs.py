"""Finish a manifest fetch that stopped at `git lfs pull` (LFS budget), using locally supplied objects.

usage: finish_lfs.py <manifest> <workspace> <lock> <project path> <file>...
Each supplied file is stored under its SHA-256 in the checkout's LFS object store only if that
hash is one of the checkout's LFS pointers; then the remaining steps of fetch_sources.fetch()
run unchanged: lfs checkout, lfs fsck, the locked patch, the tree check and the source record.
"""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

manifest, workspace, lock, project = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
sys.path.insert(0, str(manifest / "tools"))
from fetch_sources import ROOT, read_lock, run  # noqa: E402

entry = next(e for e in read_lock(manifest / lock) if e["path"] == project)
target = workspace / project
if (target / ".git/a2hlab-source.json").exists():
    sys.exit(f"already complete: {project}")
wanted = {line.split()[0] for line in subprocess.check_output(["git", "lfs", "ls-files", "-l"], cwd=target, text=True).splitlines()}
for supplied in map(Path, sys.argv[5:]):
    oid = hashlib.sha256(supplied.read_bytes()).hexdigest()
    if oid not in wanted:
        sys.exit(f"{supplied} ({oid}) is not an LFS object of {project}")
    store = target / ".git/lfs/objects" / oid[:2] / oid[2:4] / oid
    store.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(supplied, store)
    wanted.discard(oid)
if wanted:
    sys.exit(f"still missing LFS objects: {sorted(wanted)}")
run("git", "lfs", "checkout", cwd=target)
run("git", "lfs", "fsck", cwd=target)
if entry.get("patch"):
    patch = (ROOT / entry["patch"]).resolve()
    if hashlib.sha256(patch.read_bytes()).hexdigest() != entry["patch_sha256"]:
        sys.exit("patch digest mismatch")
    run("git", "apply", "--index", str(patch), cwd=target)
record = dict(entry, tree=run("git", "write-tree", cwd=target).decode().strip())
if entry.get("tree") and record["tree"] != entry["tree"]:
    sys.exit(f"patched checkout tree differs from lock: {project}")
if subprocess.check_output(["git", "status", "--porcelain"], cwd=target).strip() and not entry.get("patch"):
    sys.exit(f"checkout not clean after LFS checkout: {project}")
(target / ".git/a2hlab-source.json").write_text(json.dumps(record, sort_keys=True, indent=2) + "\n")
print("READY", project, record["tree"], "(LFS objects supplied locally)")
