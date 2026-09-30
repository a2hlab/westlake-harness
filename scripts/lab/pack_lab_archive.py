#!/usr/bin/env python3
"""Pack lab state that is not in git into one deduplicating tar.zst, for the hw248 mirror (env.md §5).

    pack_lab_archive.py <out.tar.zst> --root <dir> (--untracked <repo-or-worktree> | --path <dir-or-file>)...

--untracked  every file git does not track in that checkout (untracked and ignored, so the OLP boards
             in .octos/ come along), minus agent session state (.octos/kimi|glm, *.lock) and regenerable caches (target/, __pycache__/, node_modules/, .venv/)
--path       a whole directory or file
Paths are stored relative to --root. Files are ordered by (name, size) so identical copies spread over
many generation directories sit next to each other and zstd --long=31 stores them once; unpack with
`zstd -d --long=31 -c <f> | tar -xf - -C <root>`. Writes <out>.files (the member list) next to it.
"""
import argparse, os, re, subprocess, sys

SKIP = re.compile(r"(^|/)\.octos/(kimi|glm)/|(^|/)(target|__pycache__|node_modules|\.venv|\.git)/|\.lock$|(^|/)\.DS_Store$")


def untracked(checkout):
    r = subprocess.run(["git", "-C", checkout, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if r.returncode:
        print(f"warning: skipping {checkout}: {r.stderr.strip()}", file=sys.stderr)
        return []
    top = r.stdout.strip()
    out = subprocess.run(["git", "-C", top, "-c", "core.quotepath=off", "ls-files", "-o", "-z"], check=True,
                         capture_output=True).stdout.decode("utf-8", "surrogateescape")
    return [os.path.join(top, f) for f in out.split("\0") if f and not SKIP.search(f)]


def walk(path):
    if os.path.isfile(path) or os.path.islink(path):
        return [path]
    files = []
    for d, dirs, names in os.walk(path):
        files += [os.path.join(d, x) for x in dirs if os.path.islink(os.path.join(d, x))]  # not followed
        dirs[:] = [x for x in dirs if x != ".git" and not os.path.islink(os.path.join(d, x))]
        files += [os.path.join(d, n) for n in names if n != ".DS_Store"]
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--root", required=True)
    ap.add_argument("--untracked", action="append", default=[])
    ap.add_argument("--path", action="append", default=[])
    ap.add_argument("--level", default="6")
    a = ap.parse_args()
    root = os.path.realpath(a.root)
    files = []
    for c in a.untracked:
        files += untracked(c)
    for p in a.path:
        files += walk(os.path.abspath(p))
    rel = sorted({os.path.relpath(os.path.realpath(os.path.dirname(f)), root) + "/" + os.path.basename(f)
                  for f in files if os.path.lexists(f)},
                 key=lambda r: (os.path.basename(r), os.path.lexists(os.path.join(root, r))
                                and os.lstat(os.path.join(root, r)).st_size, r))
    bad = [r for r in rel if r.startswith("../")]
    if bad:
        sys.exit(f"{len(bad)} paths outside --root, e.g. {bad[0]}")
    lst = a.out + ".files"
    with open(lst, "wb") as fh:
        fh.write(b"\0".join(r.encode("utf-8", "surrogateescape") for r in rel) + b"\0")
    size = sum(os.lstat(os.path.join(root, r)).st_size for r in rel)
    print(f"{a.out}: {len(rel)} files, {size / 2**30:.1f} GiB before compression", flush=True)
    tar = subprocess.Popen(["tar", "--null", "-T", lst, "-cf", "-"], cwd=root, stdout=subprocess.PIPE)
    part = a.out + ".part"  # renamed only on success, so a killed run never leaves a complete-looking file
    with open(part, "wb") as out:
        zst = subprocess.run(["zstd", "-q", "-T0", f"-{a.level}", "--long=31", "-c"], stdin=tar.stdout,
                             stdout=out)
    tar.stdout.close()
    if tar.wait() != 0 or zst.returncode != 0:
        sys.exit(f"tar={tar.returncode} zstd={zst.returncode}")
    os.replace(part, a.out)
    print(f"{a.out}: {os.path.getsize(a.out) / 2**30:.1f} GiB", flush=True)


if __name__ == "__main__":
    main()
