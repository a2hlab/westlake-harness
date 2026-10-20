#!/usr/bin/env python3
"""Offline T29 bridge -> exact owner bindings -> shim. No device capability."""
import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

import jni_tables
from prepare_owner import derive, extract

P = Path(__file__).resolve().parent
BASE_BRIDGE = "dca530eb4b1b53e5dd0ecc41c36953f7463609c5b70bbdf67a49dc3cae17f9d9"
BASE_SHIM = "89b9a8b9868bb35d3cd70108e9114714c7f525cbed7006974b4f095912ff0b33"
UNITS = ("oh_surface_texture_jni.cpp", "oh_texture_view_jni.cpp")
CONSUMER_FILES = {*(f"derived/{n}" for n in UNITS),
                  "logger/observe29c.c", "logger/observe29c.h"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def need(v, message):
    if not v:
        raise ValueError(message)


def definitions(text):
    rows = [line.split() for line in text.splitlines()]
    return {tuple(f[i] for i in (3, 4, 5, 7)) for f in rows if len(f) >= 8 and
            f[0].endswith(":") and f[4] in ("GLOBAL", "WEAK") and f[6] != "UND"}


def compare_abi(before, after, expected=None):
    old, new = definitions(before), definitions(after)
    need(old and old == new, "empty/drifted ABI definition tuples")
    if expected:
        need(len(old) == expected, "unexpected ABI count")
    deps = lambda t: re.findall(r"\(NEEDED\).*Shared library: \[(.*?)\]", t)
    need(deps(before) and deps(before) == deps(after), "empty/drifted DT_NEEDED")
    need("TEXTREL" not in after, "candidate TEXTREL")
    return {"definitions": len(old), "needed": deps(after), "equal": True}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for n in ("repo", "sdk", "bridge-inputs", "bridge-base", "shim-base",
              "consumer", "consumer-pins", "out"):
        ap.add_argument("--" + n, type=Path, required=True)
    ap.add_argument("--path-map", action="append", default=[])
    ap.add_argument("--execute", action="store_true")
    a = ap.parse_args()
    mappings = [s.split("=", 1) for s in a.path_map]
    need(all(len(x) == 2 and x[0] for x in mappings), "path-map must be OLD=NEW")
    def remap(s):
        for old, new in sorted(mappings, key=lambda x: len(x[0]), reverse=True):
            s = s.replace(old, new)
        return s
    manifest = json.loads(a.consumer_pins.read_text())
    need(manifest["status"] == "CONSUMER_FINAL_REVIEWED", "consumer not final")
    need(set(manifest["sources"]) == CONSUMER_FILES, "exact consumer source set")
    for rel, h in manifest["sources"].items():
        need(sha(a.consumer / rel) == h, "consumer source pin " + rel)
    review = a.consumer / manifest["review"]["path"]
    need(review.resolve().is_relative_to(a.consumer.resolve()), "consumer review escape")
    need(sha(review) == manifest["review"]["sha256"], "consumer review pin")
    if not a.execute:
        print(json.dumps({"status": "PREVIEW_ONLY", "consumer_pins": sha(a.consumer_pins),
                          "order": ["bridge", "owner", "shim"], "device_calls": 0}))
        return
    a.out = a.out.absolute()
    a.out.mkdir(parents=True, exist_ok=False)
    raw = a.out / "raw"
    raw.mkdir()
    result = {"status": "INCOMPLETE_NOT_DEPLOYABLE", "inputs": {}, "commands": [],
              "device_calls": 0, "runtime_binding": "UNKNOWN"}
    def write(p, value):
        p.write_text(json.dumps(value, indent=2) + "\n")
    def save():
        write(a.out / "receipt.json", result)
    def pin(p):
        p = Path(p).absolute()  # preserve tool invocation name / clang++ mode
        need(p.is_file(), "missing input " + str(p))
        row = {"sha256": sha(p), "bytes": p.stat().st_size}
        if str(p) in result["inputs"]:
            need(result["inputs"][str(p)] == row, "input drift " + str(p))
        result["inputs"][str(p)] = row
        return p
    def run(name, argv):
        argv = list(map(str, argv))
        write(raw / (name + ".argv.json"), argv)
        with (raw / (name + ".stdout")).open("wb") as o, (raw / (name + ".stderr")).open("wb") as e:
            try:
                rc = subprocess.run(argv, stdout=o, stderr=e, timeout=180).returncode
            except subprocess.TimeoutExpired:
                rc = 124
            except OSError as ex:
                e.write(str(ex).encode())
                rc = 127
        (raw / (name + ".rc")).write_text(str(rc) + "\n")
        result["commands"].append({"name": name, "rc": rc})
        save()
        need(rc == 0, "command failed: " + name)
        return (raw / (name + ".stdout")).read_text()
    def command_inputs(argv):
        for arg in argv:
            p = Path(arg.split("=", 1)[1] if arg.startswith("-Wl,--version-script=") else arg)
            if p.is_file():
                pin(p)
    def compile_unit(name, argv, source, output):
        cmd = list(argv)
        cmd[cmd.index("-c")+1] = str(source)
        cmd[cmd.index("-o")+1] = str(output)
        if "-MMD" in cmd:
            cmd[cmd.index("-MMD")] = "-MD"
        cmd[cmd.index("-MF")+1] = str(output.with_suffix(".d"))
        command_inputs(cmd)
        run(name, cmd)
        deps = output.with_suffix(".d").read_text().replace("\\\n", " ")
        for f in shlex.split(deps.split(": ", 1)[1]):
            pin(f)
    try:
        for file in (Path(__file__), P/"prepare_owner.py", P/"jni_tables.py", a.consumer_pins, review):
            pin(file)
        run("00-frozen", [sys.executable, a.repo/"scripts/lab/check_frozen.py",
                         "--git", a.repo, "--registry", a.repo/"knowledge/frozen/frozen.json"])
        cc = pin(a.sdk/"llvm/bin/clang")
        cxx = pin(a.sdk/"llvm/bin/clang++")
        rd = pin(a.sdk/"llvm/bin/llvm-readelf")
        pin(a.sdk/"llvm/bin/ld.lld")
        # Original T18 720 inputs are verified before reusing any link object.
        old_pins = json.loads(pin(a.repo/"benchmark/2026-10-20-t18-audiotrack-production/input-pins.json").read_text())
        def expand(s):
            return s.replace("$INPUTS", str(a.bridge_inputs)).replace("$SDK", str(a.sdk)).replace("$OUT", str(a.out))
        for name, row in old_pins.items():
            f = pin(expand(name))
            need(sha(f) == row["sha256"] and f.stat().st_size == row["bytes"], "T18 pin " + name)
        need(sha(pin(a.bridge_base/"candidate.so")) == BASE_BRIDGE, "wrong dca baseline")
        need(sha(pin(a.shim_base/"candidate.so")) == BASE_SHIM, "wrong 89b9 baseline")
        old_shim = json.loads(pin(a.shim_base/"receipt.json").read_text())
        need(old_shim["outputs"]["candidate.so"]["sha256"] == BASE_SHIM, "shim receipt mismatch")
        for name, row in old_shim["inputs"].items():
            need(sha(pin(remap(name))) == row["sha256"], "T28 input drift")
        for name, row in old_shim["outputs"].items():
            need(sha(pin(a.shim_base/name)) == row["sha256"], "T28 output drift")
        bridge_link = [remap(x) for x in json.loads(pin(a.bridge_base/"candidate-link.argv.json").read_text())]
        bridge_link[0] = str(cxx)
        bridge_link[bridge_link.index("-o")+1] = str(a.out/"bridge-baseline.so")
        command_inputs(bridge_link)
        run("01-bridge-baseline", bridge_link)
        need(sha(a.out/"bridge-baseline.so") == BASE_BRIDGE, "dca relink differs")
        shim_link = [remap(x) for x in json.loads(pin(a.shim_base/"raw/30-candidate-link.argv.json").read_text())]
        shim_link[0] = str(cc)
        shim_link[shim_link.index("-o")+1] = str(a.out/"shim-baseline.so")
        command_inputs(shim_link)
        run("02-shim-baseline", shim_link)
        need(sha(a.out/"shim-baseline.so") == BASE_SHIM, "89b9 relink differs")
        recipe = json.loads(pin(a.repo/"benchmark/2026-10-20-t18-audiotrack-production/recipe.json").read_text())
        cflags = [expand(x) for x in recipe["compile"]]
        cflags[0] = str(cxx)
        baseline_objects = {}
        candidate_objects = {}
        for i, name in enumerate(UNITS):
            old_name = "westlake_framework_surface_jni_" + name + ".o"
            hits = [x for x in bridge_link if Path(x).name == old_name]
            need(len(hits) == 1, "ambiguous original consumer object " + name)
            original = pin(a.bridge_inputs/"westlake-touch21/framework/surface/jni"/name)
            fresh = a.out/("consumer-baseline-" + str(i) + ".o")
            compile_unit(f"10-consumer-original-{i}", cflags, original, fresh)
            baseline_objects[name] = {"historical": sha(pin(hits[0])), "rebuilt": sha(fresh),
                                      "byte_equal": sha(hits[0]) == sha(fresh)}
            new_source = pin(a.consumer/"derived"/name)
            need(sha(new_source) == manifest["sources"]["derived/"+name], "consumer changed before compile")
            obj = a.out/("consumer-" + str(i) + ".o")
            compile_unit(f"11-consumer-candidate-{i}",
                         cflags + ["-I"+str(a.consumer/"logger")], new_source, obj)
            candidate_objects[hits[0]] = str(obj)
        write(a.out/"consumer-original-object-comparison.json", baseline_objects)
        cbase = [str(cc), "--target=aarch64-linux-ohos", "--sysroot="+str(a.sdk/"sysroot"),
                 "-std=c11", "-fPIC", "-fvisibility=hidden", "-O2", "-Wall", "-Wextra",
                 "-Werror", "-Wno-misleading-indentation", "-D_GNU_SOURCE=1",
                 "-MD", "-MF", "UNSET.d", "-c", "UNSET.c", "-o", "UNSET.o"]
        for rel, h in manifest["sources"].items():
            need(sha(pin(a.consumer/rel)) == h, "consumer final source drift")
        clog = a.out/"consumer-logger.o"
        compile_unit("12-consumer-logger", cbase+["-I"+str(a.consumer/"logger")],
                     a.consumer/"logger/observe29c.c", clog)
        candidate = [candidate_objects.get(x, x) for x in bridge_link]
        candidate.insert(candidate.index("-Wl,--as-needed"), str(clog))
        candidate[candidate.index("-o")+1] = str(a.out/"bridge.so")
        run("13-bridge-candidate", candidate)
        def elf(name, file):
            return run(name, [rd, "--elf-output-style=GNU", "-h", "-d", "--dyn-syms", "--wide", file])
        bo = elf("14-bridge-baseline-elf", a.out/"bridge-baseline.so")
        bn = elf("15-bridge-candidate-elf", a.out/"bridge.so")
        result["bridge_abi"] = compare_abi(bo, bn)
        tables = []
        for label, file in [("baseline", a.out/"bridge-baseline.so"), ("candidate", a.out/"bridge.so")]:
            text = run("16-jni-"+label, [rd, "--elf-output-style=GNU", "--syms", "--wide", file])
            tables.append(jni_tables.inspect(file.read_bytes(), text))
        jni_tables.compare(*tables)
        write(a.out/"jni-tables.json", dict(zip(("baseline","candidate"), tables)))
        owner_text = run("17-owner-relocations", [rd, "--elf-output-style=GNU", "--dyn-syms", "--relocs", "--wide", a.out/"bridge.so"])
        offsets = extract(owner_text, (a.out/"bridge.so").read_bytes())
        write(a.out/"owner-bindings.json", {"bridge_sha256": sha(a.out/"bridge.so"),
              "offsets": {n: hex(v) for n, v in offsets.items()}, "runtime": "UNKNOWN"})
        # All generated source changes are confined to this new output tree.
        shim = P.parent/"shim"
        frozen = json.loads(pin(P.parent/"shim-checkpoint-02/manifest.json").read_text())
        for row in frozen:
            if "/shim/" in row["path"]:
                f = shim/row["path"].split("/shim/",1)[1]
                need(sha(pin(f)) == row["sha256"], "checkpoint02 drift")
        generated = a.out/"derived"
        generated.mkdir()
        changes = {}
        for name in ("geometry.c", "pair.c"):
            source = shim/"derived"/name
            target = generated/name
            target.write_text(derive(source.read_text(), offsets))
            changes[name] = {"before": sha(source), "after": sha(target)}
        write(a.out/"owner-source-delta.json", changes)
        replacement = {}
        for i, (name, src) in enumerate([
            ("r14.o", shim/"derived/window_module.c"),
            ("pair.o", generated/"pair.c"), ("geometry.o", generated/"geometry.c"),
            ("yv12.o", shim/"yv12.c"), ("observe29.o", shim/"observe29.c")]):
            obj = a.out/name
            compile_unit(f"20-shim-{i}", cbase+["-DWL_T27_OBSERVER", "-DR20_INTERNAL",
                         "-DR15_OH_SDK", "-I"+str(shim), "-I"+str(shim/"derived")], src, obj)
            replacement[name] = str(obj)
        successor = []
        seen = set()
        for x in shim_link:
            n = Path(x).name
            if n in replacement:
                need(n not in seen, "duplicate shim replacement")
                seen.add(n)
                successor.append(replacement[n])
            else:
                successor.append(x)
        need(seen == set(replacement)-{"observe29.o"}, "missing original shim object")
        successor.insert(successor.index("-Wl,--as-needed"), replacement["observe29.o"])
        successor[successor.index("-o")+1] = str(a.out/"shim.so")
        run("30-shim-candidate", successor)
        so = elf("31-shim-baseline-elf", a.out/"shim-baseline.so")
        sn = elf("32-shim-candidate-elf", a.out/"shim.so")
        result["shim_abi"] = compare_abi(so, sn, 78)
        result["shim_exports"] = {}
        for name in ("ANativeWindow_lock", "ANativeWindow_unlockAndPost", "ANativeWindow_setBuffersGeometry"):
            rows = [line.split() for line in sn.splitlines()
                    if line.split() and line.split()[-1] == name+"@@LIBC"]
            need(len(rows) == 1, "missing unique versioned export " + name)
            result["shim_exports"][name] = hex(int(rows[0][1],16))
        for path, row in result["inputs"].items():
            need(sha(path) == row["sha256"], "input changed during build " + path)
        result["consumer_original_objects"] = baseline_objects
        result["consumer_original_semantic_review"] = (
            "BYTE_EQUAL" if all(x["byte_equal"] for x in baseline_objects.values())
            else "REQUIRED_BEFORE_ADMISSION")
        result["outputs"] = {str(f.relative_to(a.out)): {"sha256": sha(f), "bytes": f.stat().st_size}
                             for f in a.out.rglob("*") if f.is_file() and f.name != "receipt.json"}
        result["status"] = "OFFLINE_OBSERVATION_CANDIDATE_NOT_DEPLOY_AUTHORIZED"
        save()
        print(json.dumps({n: result["outputs"][n] for n in ("bridge.so","shim.so")}))
    except Exception as ex:
        result["error"] = str(ex)
        save()
        raise


if __name__ == "__main__":
    main()
