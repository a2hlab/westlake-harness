#!/usr/bin/env python3
"""Reproduce the U13 host appspawn-x (2a87118e) and build the U14-patched candidate, in THIS benchmark dir.

Mirrors the compile+link core of benchmark/2026-10-02-u12-private-zlib/build.py (read-only recipe), but reads sources
from ./inputs and writes objects/binaries to ./.artifacts here -- never into another lane's worktree. Large binary
inputs (sysroot, frozen toolchain, reused .o) are referenced read-only by $WORKSPACES path, not copied.

    reproduce_host.py            # unpatched reproduce x2 -> must equal 2a87118e (N10b gate)
    reproduce_host.py --patched  # apply win-u14-appns-public-libs.patch to a copy, build x2 -> U14 candidate

Stops (non-zero) on any gate failure: compiler sha, reused-object sha, two-builds-differ, or (unpatched) != 2a87118e.
"""
import hashlib, json, os, subprocess, sys, shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent          # the benchmark dir
# WS = the workspaces root (parent of all westlake-harness* checkouts); from $WORKSPACES or derived from this worktree.
WS = Path(os.environ.get("WORKSPACES") or HERE.parents[2])
MASTER = WS / "westlake-harness"
RECIPE = MASTER / "benchmark/2026-10-01-u10-bundle/r2-host-build-receipt.json"
EXPECT_2A = "2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e"
ART = HERE / ".artifacts"


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sub(v): return v.replace("$WORKSPACES", str(WS)).replace("$REPO", str(WS / "westlake-harness-bms"))


def build_one(variant, source, recipe):
    compile_command = [sub(v) for v in recipe["runs"][0]["commands"][0]]
    link_command = [sub(v) for v in recipe["runs"][0]["commands"][1]]
    if sha(compile_command[0]) != recipe["compiler_sha256"]:
        sys.exit("FAIL compiler sha mismatch")
    old_object = compile_command[compile_command.index("-o") + 1]
    obj = ART / (variant + ".o")
    compile_command[compile_command.index("-c") + 1] = str(source)
    compile_command[compile_command.index("-o") + 1] = str(obj)
    compile_command.insert(1, "-I" + str(HERE / "inputs"))
    allowed = {row["sha256"] for row in recipe["reused_objects"]}
    link_command = [str(obj) if v == old_object else v for v in link_command]
    artifact = ART / ("appspawn-x-" + variant)
    link_command[link_command.index("-o") + 1] = str(artifact)
    for v in link_command:
        if v.endswith(".o") and v != str(obj) and sha(v) not in allowed:
            sys.exit(f"FAIL reused object not in allowlist: {v}")
    for step, cmd in [("compile", compile_command), ("link", link_command)]:
        r = subprocess.run(cmd, capture_output=True, text=True)
        (ART / f"{variant}-{step}.log").write_text(r.stdout + r.stderr)
        if r.returncode:
            sys.exit(f"FAIL {variant} {step}:\n{r.stdout}{r.stderr}")
    return sha(artifact)


def main():
    ART.mkdir(exist_ok=True)
    patched = "--patched" in sys.argv
    recipe = json.loads(RECIPE.read_text())
    src = HERE / "inputs" / "candidate-stock-host.c"
    label = "candidate"
    if patched:
        src = ART / "candidate-stock-host.patched.c"
        text = (HERE / "inputs" / "candidate-stock-host.c").read_text()
        old = ("    if (wants_bridge) {\n"
               "        result = dlns_inherit(app_namespace, bridge_namespace,\n"
               "                              bridge_shared_sonames);\n")
        new = ("    if (wants_bridge) {\n"
               "        static const char kAospPublicLibs[] =\n"
               "            \"libicui18n.so:libicuuc.so:libGLESv2.so:libGLESv3.so:libvulkan.so:libjnigraphics.so\";\n"
               "        char app_public[2 * PATH_MAX];\n"
               "        int app_public_len = snprintf(app_public, sizeof(app_public), \"%s:%s\",\n"
               "                                      bridge_shared_sonames, kAospPublicLibs);\n"
               "        if (app_public_len < 0 || (size_t)app_public_len >= sizeof(app_public)) {\n"
               "            return NamespaceResultFence(ENAMETOOLONG);\n"
               "        }\n"
               "        result = dlns_inherit(app_namespace, bridge_namespace, app_public);\n")
        if text.count(old) != 1:
            sys.exit(f"FAIL patch anchor not unique (count={text.count(old)})")
        src.write_text(text.replace(old, new))
        label = "u14"
    s1 = build_one(label + "1", src, recipe)
    s2 = build_one(label + "2", src, recipe)
    print(f"{label}1 = {s1}")
    print(f"{label}2 = {s2}")
    if s1 != s2:
        sys.exit("FAIL two builds differ")
    if not patched:
        print(f"expect   = {EXPECT_2A}")
        if s1 != EXPECT_2A:
            sys.exit("FAIL N10b gate: reproduce != 2a87118e (report the delta, do not patch)")
        print("GATE PASS: reproduced 2a87118e byte-identical x2")
    else:
        print("U14 candidate built byte-identical x2:", s1)


if __name__ == "__main__":
    main()
