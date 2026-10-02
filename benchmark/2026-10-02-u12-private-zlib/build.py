import json
from pathlib import Path
import shutil
import subprocess

from collect import BASE, HERE, MASTER, REPO, WS, portable, run, save, sha


def tee_build(name, command):
    raw = HERE / ".artifacts" / (name + ".txt")
    with raw.open("wb") as log:
        process = subprocess.Popen([str(value) for value in command], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for block in iter(lambda: process.stdout.read(4096), b""):
            log.write(block)
            log.flush()
            print(block.decode(errors="replace"), end="", flush=True)
        code = process.wait()
    (HERE / "evidence" / raw.name).write_text(portable(raw.read_text(errors="replace")))
    if code:
        raise RuntimeError("build failed: " + name)
    return dict(command=[portable(value) for value in command], exit_code=code, runtime_tee=True, raw_sha256=sha(raw))


def main():
    for name in ["inputs", "evidence", ".artifacts"]:
        (HERE / name).mkdir(exist_ok=True)
    old = REPO / "benchmark/2026-10-02-u11-native-batch"
    original_receipt = json.loads((old / ".artifacts/r1/build-receipt.json").read_text())["host"]
    source_rows = {"baseline-stock-host.c": old / "inputs/host-r3/candidate-stock-host.c",
                   "candidate-stock-host.c": old / ".artifacts/r1/host/candidate-stock-host.c",
                   "resident-compat.h": old / "inputs/host-r3/resident-compat.h",
                   "zlib-route.h": old / "zlib-route.h", "test_routes.c": old / "test_routes.c"}
    if sha(source_rows["candidate-stock-host.c"]) != original_receipt["source_sha256"]:
        raise ValueError("reviewed route source drift")
    if sha(source_rows["baseline-stock-host.c"]) != "507bf160dfae87851345c8fc564c9378356a773cc84272d2ec0635b1c0ef0c50":
        raise ValueError("reviewed r3 source drift")
    for name, path in source_rows.items():
        shutil.copyfile(path, HERE / "inputs" / name)
    patch = old / "patches/zlib/westlake_stock_host_main.c.patch"
    shutil.copyfile(patch, HERE / "route.patch")
    recipe_path = MASTER / "benchmark/2026-10-01-u10-bundle/r2-host-build-receipt.json"
    recipe = json.loads(recipe_path.read_text())
    records, artifacts = [], {}
    allowed_objects = {row["sha256"] for row in recipe["reused_objects"]}
    for variant in ["baseline", "candidate1", "candidate2"]:
        commands = [[value.replace("$WORKSPACES", str(WS)).replace("$REPO", str(REPO)) for value in row]
                    for row in recipe["runs"][0]["commands"]]
        compile_command, link_command = commands
        if sha(compile_command[0]) != recipe["compiler_sha256"]:
            raise ValueError("compiler mismatch")
        old_object = compile_command[compile_command.index("-o") + 1]
        obj = HERE / ".artifacts" / (variant + ".o")
        source = HERE / "inputs" / ("baseline-stock-host.c" if variant == "baseline" else "candidate-stock-host.c")
        compile_command[compile_command.index("-c") + 1] = str(source)
        compile_command[compile_command.index("-o") + 1] = str(obj)
        compile_command.insert(1, "-I" + str(HERE / "inputs"))
        compile_command += ["-MD", "-MF", str(HERE / ".artifacts" / (variant + ".d"))]
        link_command = [str(obj) if value == old_object else value for value in link_command]
        artifact = HERE / ".artifacts" / ("appspawn-x-" + variant)
        link_command[link_command.index("-o") + 1] = str(artifact)
        for value in link_command:
            if value.endswith(".o") and value != str(obj) and sha(value) not in allowed_objects:
                raise ValueError("reused object mismatch")
        for step, command in zip(["compile", "link"], [compile_command, link_command]):
            records.append(tee_build(variant + "-" + step, command))
        artifacts[variant] = dict(path=portable(artifact), sha256=sha(artifact))
    if artifacts["candidate1"]["sha256"] != artifacts["candidate2"]["sha256"]:
        raise ValueError("two builds differ")
    dependency_text = (HERE / ".artifacts/candidate1.d").read_text().replace("\\\n", " ")
    dependencies = [Path(value) for value in dependency_text.split(":", 1)[1].split()]
    closure = []
    for number, path in enumerate(dependencies):
        target = HERE / "inputs/headers" / (str(number) + "-" + path.name)
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(path, target)
        closure.append(dict(path=portable(path), sha256=sha(path), snapshot=target.relative_to(HERE).as_posix()))
    for name in ["appspawn-x", "libz.so", "libshared_libz.z.so"]:
        records.append(run("whois-" + name, ["python3", MASTER / "scripts/lab/deployed_whois.py", name]))
    baseline = BASE / "payload/runtime/appspawn-x"
    if sha(baseline) != "65cc3535ebf22bdf664b3c8ddf932ccd7f42d936be1c861e1221a80b12a00284":
        raise ValueError("actual r3 deployment drift")
    candidate = HERE / ".artifacts/appspawn-x-candidate1"
    for name, path in [("deployed", baseline), ("candidate", candidate)]:
        records.append(run("open-" + name, ["python3", MASTER / "scripts/lab/open_site_scan.py", path,
                           "--json", HERE / ".artifacts" / ("open-" + name + ".json")]))
        save("evidence/open-" + name + ".json", json.loads((HERE / ".artifacts" / ("open-" + name + ".json")).read_text()))
    records.append(run("strings-host", ["python3", MASTER / "scripts/lab/deployed_strings_diff.py", candidate, "--deployed", baseline], allowed=(0, 1)))
    records.append(run("abi-host", ["python3", MASTER / "scripts/lab/abi_diff.py", "--old", baseline, "--new", candidate,
                       "--calls", "--json", HERE / ".artifacts/abi-host.json"]))
    save("evidence/abi-host.json", json.loads((HERE / ".artifacts/abi-host.json").read_text()))
    alias = WS / "01.OH61AOSP16/real-work/.state/build-oh-component-hw248/m1-route-a-generation-20260825-r109c-zlib-global/route-a-generation/pass1/zlib/libz.so"
    provider = BASE / "payload/android/lib64/libshared_libz.z.so"
    if sha(alias) != "50b9ab6af637c8573736a595417f6177d5845d21fc48da5b8e1299a078b1e48d" or sha(provider) != "ab0820c6a33c58f2b5aa6d7b5f967f0eae42319baa2d7a42b779d1583f8a14fc":
        raise ValueError("reviewed zlib donor mismatch")
    for name, path in [("alias", alias), ("provider", provider)]:
        records.append(run("open-" + name, ["python3", MASTER / "scripts/lab/open_site_scan.py", path]))
        records.append(run("dynamic-" + name, ["llvm-readelf", "-d", path]))
        records.append(run("strings-" + name, ["python3", MASTER / "scripts/lab/deployed_strings_diff.py", path, "--deployed", path]))
    host_test = HERE / ".artifacts/test-routes"
    records.append(run("route-compile", ["clang", "-O2", "-Werror", "-I" + str(HERE / "inputs"), HERE / "inputs/test_routes.c", "-o", host_test]))
    records.append(run("route-behavior", [host_test]))
    save("build-receipt.json", dict(artifacts=artifacts, commands=records, compiler_sha256=recipe["compiler_sha256"],
         headers=closure, reused_objects=recipe["reused_objects"], recipe_path=portable(recipe_path), recipe_sha256=sha(recipe_path),
         reviewed_source_sha256=sha(source_rows["candidate-stock-host.c"]), original_reviewed_source=portable(source_rows["candidate-stock-host.c"]),
         source_files={name: sha(HERE / "inputs" / name) for name in source_rows},
         deployed_sha256=sha(baseline), comparison_only=True, two_builds_identical=True, execution_enabled=False,
         alias=dict(path=portable(alias), sha256=sha(alias)), provider=dict(path=portable(provider), sha256=sha(provider))))
    print("reviewed private zlib route candidate=" + sha(candidate) + " two builds identical; r3 deployed=" + sha(baseline))


if __name__ == "__main__":
    main()
