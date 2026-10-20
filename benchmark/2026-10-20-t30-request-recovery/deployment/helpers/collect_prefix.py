#!/usr/bin/env python3
"""T28 fixed-prefix capture derivation. Outer channel only; preview by default."""
import argparse
import datetime
import hashlib
import json
import re
import shlex
import subprocess
import time
import uuid
from pathlib import Path

SERIAL = "5cd1e3dd00000000000000000923012c"
EXE = "a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c"
CAP = 250000000
q = shlex.quote


def require(v, text):
    if not v:
        raise ValueError(text)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def identity_guard(a, remote):
    parts = [f'test "$(cat /proc/sys/kernel/random/boot_id)" = {q(a.boot)}']
    for pid, birth, uid, ppid in ((a.parent, a.parent_birth, 0, 1),
                                  (a.child, a.child_birth, 20011300, a.parent),
                                  (a.host, a.host_birth, 20011300, None)):
        parts += [f'r=$(cat /proc/{pid}/stat); z=${{r##*) }}; set -- $z',
                  f'test "${{20}}" = {birth}',
                  'test "$1" != Z; test "$1" != X; test "$1" != T; test "$1" != t',
                  f'u=$(sed -n \'s/^Uid:[[:space:]]*//p\' /proc/{pid}/status); '
                  f'test "$u" != ""; saved_ppid=$2; set -- $u; test "$1:$2:$3:$4" = {uid}:{uid}:{uid}:{uid}',
                  f'test "$(sed -n \'s/^TracerPid:[[:space:]]*//p\' /proc/{pid}/status)" = 0']
        if ppid is not None:
            parts += [f'test "$saved_ppid" = {ppid}',
                      f'test "$(sha256sum /proc/{pid}/exe | cut -d\' \' -f1)" = {EXE}']
    parts += [f'test "$(readlink /proc/{a.parent}/ns/mnt)" != "$(readlink /proc/1/ns/mnt)"',
              f'test "$(readlink /proc/{a.child}/ns/mnt)" = "$(readlink /proc/{a.parent}/ns/mnt)"',
              f'test "$(readlink /proc/{a.child}/fd/2)" = {q(remote)}']
    return ";\n".join(parts)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("context", "out"):
        p.add_argument("--" + key, required=True, type=Path)
    p.add_argument("--boot", required=True)
    for key in ("child", "child-birth", "parent", "parent-birth", "host", "host-birth"):
        p.add_argument("--" + key, required=True, type=int)
    p.add_argument("--execute", action="store_true")
    a = p.parse_args()
    c = json.loads(a.context.read_text())
    require(c["serial"] == SERIAL, "serial")
    require(str(uuid.UUID(a.boot)) == a.boot, "boot")
    require(all(getattr(a, k) > 0 for k in
                ("child", "child_birth", "parent", "parent_birth", "host", "host_birth")), "identity")
    require(len({a.child, a.parent, a.host}) == 3, "distinct process identities")
    repo = Path(c["repo"])
    require(repo.name == "westlake-harness" and repo.is_absolute(), "MAIN cwd")
    tokens = c["holder"].split()
    require(len(tokens) == 3 and tokens[0] == "inner(cx-seal)" and
            abs(datetime.datetime.fromisoformat(tokens[2]).timestamp() - c["start"]) < 1,
            "holder/start")
    if not a.execute:
        print(json.dumps(dict(status="PREVIEW_NO_DEVICE", device_calls=0,
                              prefix_cap=CAP, stop_at=c["start"] + 1200)))
        return
    remaining = c["start"] + 1200 - time.time()
    require(0 < remaining <= 1200, "experiment deadline")
    deadline = time.monotonic() + remaining
    require(a.out.is_absolute() and not str(a.out).startswith(("/tmp/", "/private/tmp/")),
            "persistent output")
    a.out.mkdir(parents=True, exist_ok=False)
    result = dict(status="INCOMPLETE_EVIDENCE_RETAINED", boot=a.boot, child=a.child,
                  child_birth=a.child_birth, parent=a.parent, parent_birth=a.parent_birth,
                  host=a.host, host_birth=a.host_birth, scope="fixed source prefix [0,end), not global history",
                  postguard="UNKNOWN", prefix_cap=CAP, immutability_not_proven=True,
                  source_context_sha256=digest(a.context))
    def save():
        (a.out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    def budget():
        seconds = min(deadline-time.monotonic(), c["start"]+1200-time.time())
        require(seconds > 0, "1200-second experiment deadline")
        return seconds
    def raw_run(tag, argv, timeout):
        (a.out / (tag+".argv.json")).write_text(json.dumps(argv, indent=2)+"\n")
        rc = 127
        try:
            with (a.out/(tag+".stdout")).open("wb") as o, (a.out/(tag+".stderr")).open("wb") as e:
                try:
                    rc = subprocess.run(argv, cwd=repo, stdout=o, stderr=e,
                                        timeout=min(timeout, budget())).returncode
                except subprocess.TimeoutExpired:
                    rc = 124
                except OSError as ex:
                    e.write(str(ex).encode())
        finally:
            (a.out/(tag+".rc")).write_text(str(rc)+"\n")
        require(rc == 0, tag+" host rc="+str(rc))
        return (a.out/(tag+".stdout")).read_text(errors="replace")
    def run(tag, argv, timeout=30):
        held = raw_run(tag+"-held", ["bash", str(repo/"scripts/lab/board_note.sh"),
                                     "held", SERIAL], 5)
        require(held.strip() == c["holder"], "exact holder drift")
        return raw_run(tag, argv, timeout)
    remote = f"/data/service/el1/public/appspawnx/adapter_child_{a.child}.stderr"
    # Same-directory unique stage does not modify the source log or runtime.
    suffix = hashlib.sha256(str(a.out).encode()).hexdigest()[:12]
    stage = f"/data/local/tmp/t30-log-{a.child}-{int(c['start'])}-{suffix}"
    guard = identity_guard(a, remote)
    def shell(tag, body, timeout=30):
        script = f"(set -eu;\n{guard};\n{body};\n{guard};\necho T30_LOG_COMPLETE)\nr=$?; echo T30_LOG_REMOTE_RC=$r"
        text = run(tag, [c["hdc"], "-t", SERIAL, "shell", script], timeout)
        require(text.splitlines()[-2:] == ["T30_LOG_COMPLETE", "T30_LOG_REMOTE_RC=0"],
                tag+" missing remote completion; raw retained")
        return text
    def one(text, key, pattern):
        values = re.findall("^"+key+"=("+pattern+")$", text, re.M)
        require(len(values) == 1, "missing/ambiguous "+key)
        return values[0]
    save()
    try:
        pre = shell("before", f'test ! -L {remote}; test -f {remote}; '
                    f'printf "SOURCE="; stat -c %d:%i:%s {remote}; '
                    f'cat /proc/{a.child}/stat; cat /proc/{a.child}/maps')
        source = one(pre, "SOURCE", r"\d+:\d+:\d+")
        dev, ino, size = map(int, source.split(":"))
        end = min(size, CAP)
        require(end > 0, "empty source")
        result.update(source=remote, source_before=source, source_end=end,
                      source_size_before=size, capped=size > CAP, selected_remote=stage+"/selected.raw")
        save()
        fileguard = (f'test ! -L {remote}; test -f {remote}; '
                     f'test "$(stat -c %d:%i {remote})" = {dev}:{ino}; '
                     f'test "$(stat -c %s {remote})" -ge {end}')
        selected = shell("selected", f'{fileguard}; test ! -e {stage}; mkdir {stage}; chmod 700 {stage}; '
                         f'head -c {end} {remote} > {stage}/selected.raw; '
                         f'test "$(stat -c %s {stage}/selected.raw)" = {end}; '
                         f'printf "PREFIX_SHA="; sha256sum {stage}/selected.raw | cut -d" " -f1; '
                         f'{fileguard}', 45)
        before_sha = one(selected, "PREFIX_SHA", "[0-9a-f]{64}")
        result["prefix_sha_before"] = before_sha
        save()
        run("receive", [c["hdc"], "-t", SERIAL, "file", "recv",
                        stage+"/selected.raw", str(a.out/"selected.raw")], 60)
        require((a.out/"selected.raw").stat().st_size == end and
                digest(a.out/"selected.raw") == before_sha, "local byte/SHA mismatch")
        result["transfer_verified"] = True
        save()
        post = shell("after", f'{fileguard}; '
                     f'head -c {end} {remote} > {stage}/recheck.raw; '
                     f'test "$(stat -c %s {stage}/recheck.raw)" = {end}; '
                     f'printf "PREFIX_SHA="; sha256sum {stage}/recheck.raw | cut -d" " -f1; '
                     f'printf "SOURCE="; stat -c %d:%i:%s {remote}; '
                     f'{fileguard}; cat /proc/{a.child}/stat', 45)
        result["prefix_sha_after"] = one(post, "PREFIX_SHA", "[0-9a-f]{64}")
        result["source_after"] = one(post, "SOURCE", r"\d+:\d+:\d+")
        result["postguard"] = "LIVE_EXACT_IDENTITIES_MATCH"
        require(result["prefix_sha_after"] == before_sha, "source prefix changed; retain both hashes")
        result.update(status="FIXED_PREFIX_TRANSFER_AND_RECHECK_VERIFIED",
                      sha256=before_sha, prefix_recheck_equal=True)
    except Exception as ex:
        result["error"] = str(ex)
        raise
    finally:
        result["elapsed_window_seconds"] = time.time()-c["start"]
        save()


if __name__ == "__main__":
    main()
