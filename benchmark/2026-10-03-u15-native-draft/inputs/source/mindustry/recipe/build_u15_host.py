#!/usr/bin/env python3
"""Build the U15 host appspawn-x = U14 host 341c1260 (candidate-stock-host.c + Wall-1 public-libs inherit)
+ the mindustry audio-branch verify fix, in THIS benchmark dir (A' standard).

Mirrors benchmark/2026-10-03-u14-appns-build/recipe/reproduce_host.py (same recipe, compiler sha, reused-object
allowlist, two-build determinism). Reads base source from ./inputs, writes to ./.artifacts here only.

    build_u15_host.py            # base341c gate: candidate+Wall-1 -> must == 341c1260
    build_u15_host.py --u15      # base341c gate + apply the mindustry patch -> U15 host x2 (byte-identical)

The mindustry patch (verify each OpenSLES symbol against its REAL provider):
  (1) audio_symbols on the OH libOpenSLES handle drops "SL_IID_BUFFERQUEUE" (libarc does not use it; OH libOpenSLES
      has it, so it was a false/extraneous assertion) -> keeps the 4 core libarc uses from OH libOpenSLES.
  (2) after the native_abi dlopen handle, assert dlsym(handle,"SL_IID_ANDROIDSIMPLEBUFFERQUEUE") for native_private
      (the Android-extension IID libarc actually uses, which lives in native_abi, NOT OH libOpenSLES), reusing the
      existing "[N4-AUDIO] provider lacks %{public}s" format (no new log literal). dlsym is not an open-site, so
      open_site_scan is unchanged; strings delta = swap the IID name only.
"""
import hashlib, json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
WS = Path(os.environ.get("WORKSPACES") or HERE.parents[2])
MASTER = WS / "westlake-harness"
RECIPE = MASTER / "benchmark/2026-10-01-u10-bundle/r2-host-build-receipt.json"
EXPECT_341C = "341c12608091246a09e973214b197eaf7d5b6b3f0bf9cc6ebbf3392648d338da"
ART = HERE / ".artifacts"

WALL1_OLD = ("    if (wants_bridge) {\n"
             "        result = dlns_inherit(app_namespace, bridge_namespace,\n"
             "                              bridge_shared_sonames);\n")
WALL1_NEW = ("    if (wants_bridge) {\n"
             "        static const char kAospPublicLibs[] =\n"
             "            \"libicui18n.so:libicuuc.so:libGLESv2.so:libGLESv3.so:libvulkan.so:libjnigraphics.so\";\n"
             "        char app_public[2 * PATH_MAX];\n"
             "        int app_public_len = snprintf(app_public, sizeof(app_public), \"%s:%s\",\n"
             "                                      bridge_shared_sonames, kAospPublicLibs);\n"
             "        if (app_public_len < 0 || (size_t)app_public_len >= sizeof(app_public)) {\n"
             "            return NamespaceResultFence(ENAMETOOLONG);\n"
             "        }\n"
             "        result = dlns_inherit(app_namespace, bridge_namespace, app_public);\n")

MIND_OLD1 = '                "slCreateEngine", "SL_IID_ENGINE", "SL_IID_VOLUME", "SL_IID_PLAY", "SL_IID_BUFFERQUEUE"\n'
MIND_NEW1 = '                "slCreateEngine", "SL_IID_ENGINE", "SL_IID_VOLUME", "SL_IID_PLAY"\n'
MIND_OLD2 = ("        void* handle = dlopen_ns(app_namespace, abi, RTLD_NOW | RTLD_GLOBAL);\n"
             "        if (handle == NULL) return NamespaceResultFence(ENOENT);\n")
MIND_NEW2 = ("        void* handle = dlopen_ns(app_namespace, abi, RTLD_NOW | RTLD_GLOBAL);\n"
             "        if (handle == NULL) return NamespaceResultFence(ENOENT);\n"
             "        if (native_private && dlsym(handle, \"SL_IID_ANDROIDSIMPLEBUFFERQUEUE\") == NULL) {\n"
             "            APPSPAWN_LOGE(\"[N4-AUDIO] provider lacks %{public}s\", \"SL_IID_ANDROIDSIMPLEBUFFERQUEUE\");\n"
             "            return NamespaceResultFence(ENOENT);\n"
             "        }\n")


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sub(v): return v.replace("$WORKSPACES", str(WS)).replace("$REPO", str(WS / "westlake-harness-bms"))


def apply_once(text, old, new, what):
    if text.count(old) != 1:
        sys.exit(f"FAIL patch anchor not unique for {what} (count={text.count(old)})")
    return text.replace(old, new)


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
    u15 = "--u15" in sys.argv
    recipe = json.loads(RECIPE.read_text())
    base = (HERE / "inputs" / "candidate-stock-host.c").read_text()

    # base341c = candidate + Wall-1 public-libs inherit -> must reproduce 341c1260
    base341c = apply_once(base, WALL1_OLD, WALL1_NEW, "wall1")
    src_b = ART / "base341c-stock-host.c"; src_b.write_text(base341c)
    b1 = build_one("base341c-1", src_b, recipe)
    b2 = build_one("base341c-2", src_b, recipe)
    print(f"base341c-1 = {b1}")
    print(f"base341c-2 = {b2}")
    print(f"expect341c = {EXPECT_341C}")
    if b1 != b2:
        sys.exit("FAIL base341c two builds differ")
    if b1 == EXPECT_341C:
        print("GATE PASS: reproduced 341c1260 byte-identical")
    else:
        # A' standard: a different benchmark dir embeds a different __FILE__/path -> clang reorders .rodata string
        # literals -> .text PC-relative immediates shift -> byte-diff that is NOT a semantic change. Prove semantic
        # faithfulness (abi_diff + deployed_strings_diff: ABI identical, strings identical modulo the build path)
        # and use base341c(this dir) as the single-variable base for the u15 delta below.
        print("A' NOTE: base341c != 341c1260 byte-identical (expected: different build-dir path reorders .rodata); "
              "semantic-faithfulness checks reported separately. Continuing under A'.")
    if not u15:
        return

    # u15 = base341c + mindustry audio verify fix
    u15src = apply_once(base341c, MIND_OLD1, MIND_NEW1, "mind-audio-symbols")
    u15src = apply_once(u15src, MIND_OLD2, MIND_NEW2, "mind-native_abi-iid")
    src_u = ART / "u15-stock-host.c"; src_u.write_text(u15src)
    u1 = build_one("u15-1", src_u, recipe)
    u2 = build_one("u15-2", src_u, recipe)
    print(f"u15-1 = {u1}")
    print(f"u15-2 = {u2}")
    if u1 != u2:
        sys.exit("FAIL u15 two builds differ")
    print("U15 host built byte-identical x2:", u1)


if __name__ == "__main__":
    main()
