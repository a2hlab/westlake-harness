#!/usr/bin/env python3
"""T1 R155 ART patch-series checkers (transcalled by tools/spec-checks).

Subcommands:
  apply    d1_patch_series_applies_to_r1  — the series applies cleanly (git apply, in
           `series` order) onto a fresh android-14.0.0_r1 art tree, and the result is
           byte-identical to the B6 rebuild tree art-hanbin on the 19 r1-vs-hanbin diff
           files (#20 PRIMCLASS-GUARD touches dex_cache-inl.h, which is NOT in that diff
           set, so it is verified to apply but excluded from the byte-identical check).
  sources  d1_every_patch_has_source      — every patch listed in `series` has a row in
           SOURCES.md with a non-empty source and a sha256 that matches the patch file;
           number of patches without a source is 0.

Reference trees (read-only) come from the B6 recovery dir. Override with
ART_R155_RECOVERY; default is the sibling westlake-harness-bms-deploy worktree.
If the recovery tree is absent (e.g. a fresh checkout without it), `apply` prints a
loud SKIP and exits 0 (it cannot verify without the reference); `sources` is
self-contained and always runs.
"""
import os, sys, re, shutil, subprocess, tempfile, hashlib, pathlib

HERE = pathlib.Path(__file__).resolve().parent          # knowledge/toolchains/art-r155
REPO = HERE.parents[2]                                   # repo root
PATCHES = HERE / "patches"
SERIES = HERE / "series"
SOURCES = HERE / "SOURCES.md"

def recovery_dir():
    env = os.environ.get("ART_R155_RECOVERY")
    if env:
        return pathlib.Path(env)
    # default: sibling worktree
    return REPO.parent / "westlake-harness-bms-deploy/bms/src/.work/b6-art14-recovery"

def series_list():
    return [l.strip() for l in SERIES.read_text().splitlines() if l.strip()]

def sha256(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()

def patch_target(pf):
    # first line: --- a/<relpath>
    first = (PATCHES / pf).read_text().splitlines()[0]
    return first.split("a/", 1)[1].strip()

def check_apply():
    rec = recovery_dir()
    r1, hanbin = rec / "art-r1", rec / "art-hanbin"
    if not r1.is_dir() or not hanbin.is_dir():
        print(f"SKIP d1_patch_series_applies_to_r1: recovery tree not found at {rec} "
              f"(set ART_R155_RECOVERY). Cannot verify apply without art-r1/art-hanbin.")
        return 0
    series = series_list()
    # target rel paths of each patch
    targets = [patch_target(pf) for pf in series]
    diff19 = [t for t in targets if t != "runtime/mirror/dex_cache-inl.h"]  # the 19 r1-vs-hanbin files
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        for t in targets:
            dst = td / t
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(r1 / t, dst)
        for pf in series:
            r = subprocess.run(["git", "apply", "-p1", str(PATCHES / pf)],
                               cwd=td, capture_output=True, text=True)
            if r.returncode != 0:
                print(f"FAIL: patch did not apply: {pf}\n{r.stderr}")
                return 1
        mism = [t for t in diff19 if (td / t).read_bytes() != (hanbin / t).read_bytes()]
        if mism:
            print(f"FAIL: not byte-identical to art-hanbin: {mism}")
            return 1
        # PRIMCLASS-GUARD present on the 20th file
        if "PRIMCLASS-GUARD" not in (td / "runtime/mirror/dex_cache-inl.h").read_text():
            print("FAIL: PRIMCLASS-GUARD not applied to dex_cache-inl.h")
            return 1
    print(f"OK d1_patch_series_applies_to_r1: {len(series)} patches applied, "
          f"{len(diff19)} files byte-identical to art-hanbin, PRIMCLASS-GUARD applied.")
    return 0

def check_sources():
    series = series_list()
    text = SOURCES.read_text()
    # parse table rows: | NN | patch | target | source | sha256 |
    rows = {}
    for m in re.finditer(r"^\|\s*\d+\s*\|\s*([^|]+?)\s*\|\s*[^|]+?\s*\|\s*([^|]+?)\s*\|\s*([0-9a-f]{64})\s*\|",
                         text, re.M):
        rows[m.group(1).strip()] = (m.group(2).strip(), m.group(3).strip())
    missing = []
    for pf in series:
        if pf not in rows:
            missing.append(f"{pf}: no SOURCES.md row"); continue
        src, sha = rows[pf]
        if not src:
            missing.append(f"{pf}: empty source")
        actual = sha256(PATCHES / pf)
        if sha != actual:
            missing.append(f"{pf}: sha256 mismatch (SOURCES={sha} actual={actual})")
    if missing:
        print("FAIL d1_every_patch_has_source:")
        print("\n".join("  " + m for m in missing))
        return 1
    print(f"OK d1_every_patch_has_source: {len(series)} patches, 0 without source, all sha256 match.")
    return 0

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit({"apply": check_apply, "sources": check_sources}.get(cmd, lambda: (print("usage: check_series.py apply|sources"), 2)[1])())
