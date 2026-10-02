import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = Path(os.environ.get("WORKSPACES", REPO.parent))
MASTER = WS / "westlake-harness"
U12 = WS / "westlake-inputs/generations/u12-final-j0482c9b1-s615b8bbe-icu-media-zlib-v2/bundle"
SIGNED = WS / "westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle"
POLICY_SHA = "2a6ec73fd87239ae90ba6464727649f5a4d73aab7588dda392df8803c2e76c4e"
HOST_SHA = "2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def portable(value):
    text = str(value)
    for root, token in [(REPO, "$REPO"), (WS, "$WORKSPACES"), (Path.home(), "$HOME")]:
        if text == str(root):
            return token
        text = text.replace(str(root) + "/", token + "/")
    return text


def save(name, value):
    target = HERE / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(portable(json.dumps(value, indent=2, ensure_ascii=False)) + "\n")


def run(name, argv, allowed=(0,)):
    raw = HERE / ".artifacts/raw" / (name + ".txt")
    raw.parent.mkdir(parents=True, exist_ok=True)
    with raw.open("wb") as output:
        process = subprocess.Popen([str(value) for value in argv], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for block in iter(lambda: process.stdout.read(65536), b""):
            output.write(block)
            output.flush()
            print(block.decode(errors="replace"), end="", flush=True)
        code = process.wait()
    evidence = HERE / "evidence" / raw.name
    evidence.parent.mkdir(exist_ok=True)
    evidence.write_text(portable(raw.read_text(errors="replace")))
    record = dict(command=[portable(value) for value in argv], exit_code=code, runtime_tee=True,
                  raw_path=portable(raw), raw_sha256=sha(raw), evidence=evidence.relative_to(HERE).as_posix())
    if code not in allowed:
        raise RuntimeError(name + ": exit=" + str(code))
    return record


def expand(argv):
    return [value.replace("$WORKSPACES", str(WS)).replace("$REPO", str(REPO)) for value in argv]


def stage():
    prior_policy = REPO / "benchmark/2026-10-02-u12-mediandk"
    prior_host = REPO / "benchmark/2026-10-02-u12-private-zlib"
    original = prior_policy / ".artifacts/policy/candidate1/source"
    support = HERE / "sources/build-support"
    if not support.exists():
        shutil.copytree(prior_policy / "inputs/build-support", support)
    for role, source in [("policy", original), ("host", prior_host / "inputs")]:
        target = HERE / "sources/baseline" / role
        if not target.exists():
            if role == "policy":
                shutil.copytree(source, target)
            else:
                target.mkdir(parents=True)
                for name in ["candidate-stock-host.c", "resident-compat.h", "zlib-route.h"]:
                    shutil.copyfile(source / name, target / name)
        candidate = HERE / "sources/candidate" / role
        if not candidate.exists():
            shutil.copytree(target, candidate)
    tree = HERE / "sources/candidate/policy"
    json_name = "policy/native_bridge_policy.v1.json"
    header_name = "include/nativeloader/native_bridge_policy.h"
    base = HERE / "sources/baseline/policy"
    original_manifest = json.loads((base / json_name).read_text())
    if len(original_manifest["system_libraries"]) != 6 or len(original_manifest["shared_sonames"]) != 7:
        raise ValueError("not the U12 six/seven policy")
    updated = json.loads(json.dumps(original_manifest))
    updated["system_libraries"].append(dict(soname="libmedia_jni.so", path="/system/android/lib64/liboh_android_runtime.so"))
    overlay = {json_name: json.dumps(updated, indent=2) + "\n"}
    header = (base / header_name).read_text()
    anchor = '    {"libmediandk.so", "/system/android/lib64/libmediandk.so"},'
    if header.count(anchor) != 1:
        raise ValueError("U12 mediandk header anchor drift")
    overlay[header_name] = header.replace("std::array<SystemLibrary, 6>", "std::array<SystemLibrary, 7>").replace(
        anchor, anchor + '\n    {"libmedia_jni.so", "/system/android/lib64/liboh_android_runtime.so"},')
    loader_name = "src/system_loader.cpp"
    loader = (base / loader_name).read_text()
    line = "  void* handle = ops_->OpenExact(resolved.c_str(), RTLD_NOW | RTLD_LOCAL);"
    if loader.count(line) != 1:
        raise ValueError("reviewed loader anchor drift")
    overlay[loader_name] = loader.replace(line, '  const bool media_owner = library->soname == "libmedia_jni.so";\n'
        '  const int flags = RTLD_NOW | RTLD_LOCAL | (media_owner ? RTLD_NOLOAD : 0);\n'
        '  void* handle = ops_->OpenExact(resolved.c_str(), flags);')
    verify_name = "tests/verify_bridge_policy.py"
    verifier = (base / verify_name).read_text()
    line = '    if item["path"] != f"/system/android/lib64/{item[\'soname\']}":'
    if verifier.count(line) != 1:
        raise ValueError("reviewed verifier anchor drift")
    overlay[verify_name] = verifier.replace(line, '    media_owner_alias = (item["soname"], item["path"]) == (\n'
        '        "libmedia_jni.so", "/system/android/lib64/liboh_android_runtime.so")\n'
        '    if not media_owner_alias and item["path"] != f"/system/android/lib64/{item[\'soname\']}":')
    for name, text in overlay.items():
        (tree / name).write_text(text)
    host_base = HERE / "sources/baseline/host/zlib-route.h"
    route = host_base.read_text()
    anchor = '"com.emn8.mobilem8.nativeapp.bk"};'
    if route.count(anchor) != 1:
        raise ValueError("reviewed private whitelist drift")
    (HERE / "sources/candidate/host/zlib-route.h").write_text(route.replace(anchor,
        '"com.emn8.mobilem8.nativeapp.bk", "com.mcdonalds.app"};'))
    for role in ["policy", "host"]:
        diff = []
        root = HERE / "sources/baseline" / role
        for path in sorted(root.rglob("*")):
            if path.is_file():
                name = path.relative_to(root).as_posix()
                candidate = HERE / "sources/candidate" / role / name
                if path.read_bytes() != candidate.read_bytes():
                    diff.extend(difflib.unified_diff(path.read_text().splitlines(True), candidate.read_text().splitlines(True),
                        fromfile="a/" + role + "/" + name, tofile="b/" + role + "/" + name))
        (HERE / (role + ".patch")).write_text("".join(diff))
    save("source-identity.json", dict(files={path.relative_to(HERE).as_posix(): sha(path)
        for path in sorted((HERE / "sources").rglob("*")) if path.is_file()},
        policy_receipt_sha256=sha(prior_policy / "policy-receipt.json"),
        host_receipt_sha256=sha(prior_host / "build-receipt.json"),
        source_lookup="local exact U12 receipts and reviewed resident-only patches; no remote source substitution"))


def build_role(role):
    prior = REPO / "benchmark" / ("2026-10-02-u12-mediandk" if role == "policy" else "2026-10-02-u12-private-zlib")
    receipt = json.loads((prior / ("policy-receipt.json" if role == "policy" else "build-receipt.json")).read_text())
    if role == "policy":
        recipes = [expand(row["command"]) for row in receipt["commands"]
            if "-o" in row["command"] and "/candidate1/" in " ".join(row["command"])][:4]
        old_source = prior / ".artifacts/policy/candidate1/source"
        old_output = prior / ".artifacts/policy/candidate1"
        filename = "libnativeloader-candidate.so"
        expected = POLICY_SHA
    else:
        recipes = [expand(row["command"]) for row in receipt["commands"][2:4]]
        old_source = prior / "inputs"
        old_output = prior / ".artifacts"
        filename = "appspawn-x-candidate1"
        expected = HOST_SHA
    output = HERE / ".artifacts" / role
    output.mkdir(parents=True, exist_ok=True)
    records, artifacts = [], {}
    for variant in ["baseline", "candidate1", "candidate2"]:
        directory = output / variant
        directory.mkdir(exist_ok=True)
        if role == "policy":
            (directory / "candidate").mkdir(exist_ok=True)
        tree = old_source if variant == "baseline" else HERE / "sources/candidate" / role
        if role == "policy":
            records.append(run(role + "-verify-" + variant, ["python3", tree / "tests/verify_bridge_policy.py"]))
        for number, recipe in enumerate(recipes):
            argv = [value.replace(str(old_output) + "/", str(directory) + "/") for value in recipe]
            argv = [value.replace(str(directory / "source") + "/", str(tree) + "/") for value in argv]
            argv = [value.replace(str(old_source) + "/", str(tree) + "/") for value in argv]
            if "-c" in argv and variant != "baseline":
                argv += ["-ffile-prefix-map=" + str(tree) + "=" + str(old_source),
                         "-fdebug-prefix-map=" + str(tree) + "=" + str(old_source)]
            if "-c" in argv:
                if "-MF" in argv:
                    argv[argv.index("-MF") + 1] = str(directory / "dependencies.d")
                else:
                    argv += ["-MD", "-MF", str(directory / (str(number) + ".d"))]
            records.append(run(role + "-" + variant + "-" + str(number), argv))
        artifact = directory / filename
        artifacts[variant] = dict(path=portable(artifact), sha256=sha(artifact))
        if variant == "baseline" and sha(artifact) != expected:
            save(role + "-rebuild-failed.json", dict(expected=expected, artifacts=artifacts, commands=records))
            raise ValueError(role + " exact U12 baseline reproduction failed")
    if artifacts["candidate1"]["sha256"] != artifacts["candidate2"]["sha256"]:
        raise ValueError(role + " repeat build differs")
    headers = {}
    for dependency in sorted(output.glob("candidate1/*.d")):
        text = dependency.read_text().replace("\\\n", " ")
        for value in text.split(":", 1)[1].split():
            path = Path(value)
            if path.is_file():
                headers[portable(path)] = sha(path)
                target = HERE / ".artifacts/frozen-headers" / sha(path)
                if not target.exists():
                    target.parent.mkdir(exist_ok=True)
                    shutil.copyfile(path, target)
    toolchain = {}
    compiler = Path(recipes[0][0])
    for path in [compiler, compiler.parent / "ld.lld", shutil.which("llvm-readelf"), shutil.which("llvm-objdump")]:
        if path and Path(path).is_file():
            toolchain[portable(path)] = sha(path)
    reused = {portable(Path(value)): sha(value) for recipe in recipes for value in recipe
              if value.endswith((".so", ".a", ".o")) and not value.startswith(str(old_output) + "/") and Path(value).is_file()}
    save(role + "-build-receipt.json", dict(artifacts=artifacts, commands=records, headers=headers,
        toolchain=toolchain, reused_inputs=reused, exact_u12_baseline=True, two_builds_identical=True,
        cwd=portable(REPO), execution_enabled=False))
    print(role + " baseline=" + expected + " candidate=" + artifacts["candidate1"]["sha256"] + " repeat identical")


if __name__ == "__main__":
    stage()
    for role in ["policy", "host"]:
        build_role(role)
