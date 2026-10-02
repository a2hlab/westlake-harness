import argparse
import difflib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

from elf_readonly import rodata_strings
from source import BASE_SHA, HERE, REPO, R3_SHA, candidate, sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=HERE / ".artifacts/frozen-r1")
    args = parser.parse_args()
    output = args.out.resolve()
    workspaces = Path(os.environ.get("WORKSPACES", REPO.parent)).resolve()
    receipt_path = workspaces / "westlake-harness/benchmark/2026-10-01-u10-bundle/r2-host-build-receipt.json"
    if sha(receipt_path) != "8eaec4315b379e1e3675b38a5e298271716279c049db1ba3ede5c3815ea0cb40":
        raise ValueError("frozen r3 object recipe drift")
    recipe = json.loads(receipt_path.read_text())
    expected_objects = {row["sha256"] for row in recipe["reused_objects"]}
    original = HERE / "inputs/host-r3.c"
    snapshot = HERE / "src/candidate-stock-host.c"
    if sha(original) != BASE_SHA or snapshot.read_text() != candidate():
        raise ValueError("r3 or candidate source drift")
    if sha(HERE / "inputs/resident-compat.h") != "e4f7321547d6cafac5734a7ff3b9338cc0e8a93e94ff5932bafa3caa23cb35e0":
        raise ValueError("r3 resident-compat header drift")
    output.mkdir(parents=True, exist_ok=True)
    (output / "objects").mkdir(exist_ok=True)
    records, repeated, inputs = [], [], {}
    baseline_elf = workspaces / "westlake-inputs/generations/u10.1-j5ae3dd29-c015aa3a6-p0718f01e-r3-v1/bundle/native/payload/runtime/appspawn-x"
    if sha(baseline_elf) != R3_SHA:
        raise ValueError("accepted baseline changed")
    strings = rodata_strings(baseline_elf)
    source_suffix = "/benchmark/2026-10-01-u10-native-shims/.artifacts/host-r3/candidate-stock-host.c"
    header_suffix = "/benchmark/2026-10-01-u10-native-shims/host-r3/resident-compat.h"
    old_source = [value for value in strings if value.endswith(source_suffix)]
    old_header = [value for value in strings if value.endswith(header_suffix)]
    if len(old_source) != 1 or len(old_header) != 1:
        raise ValueError("baseline FILE identity is ambiguous")
    original_root = old_source[0][:-len(source_suffix)]
    for repeat in [1, 2]:
        identities = {}
        for variant in ["baseline", "candidate"]:
            folder = output / variant
            folder.mkdir(exist_ok=True)
            generated = folder / "candidate-stock-host.c" if variant == "baseline" else snapshot
            if variant == "baseline":
                generated.write_bytes(original.read_bytes())
            compile_command, link_command = [[value.replace("$WORKSPACES", str(workspaces)).replace("$REPO", str(REPO))
                                             for value in command] for command in recipe["runs"][0]["commands"]]
            if sha(compile_command[0]) != recipe["compiler_sha256"]:
                raise ValueError("recorded clang changed")
            inputs[compile_command[0]] = sha(compile_command[0])
            previous_main = compile_command[compile_command.index("-o") + 1]
            obj = folder / "host.o"
            compile_command[compile_command.index("-c") + 1] = str(generated)
            compile_command[compile_command.index("-o") + 1] = str(obj)
            compile_command.extend(["-MD", "-MF", str(folder / "host.d")])
            if variant == "baseline":
                compile_command[1:1] = ["-I" + str(HERE / "inputs"),
                                       "-ffile-prefix-map=" + str(REPO) + "=" + original_root,
                                       "-ffile-prefix-map=" + str(generated) + "=" + old_source[0],
                                       "-ffile-prefix-map=" + str(HERE / "inputs/resident-compat.h") + "=" + old_header[0]]
            else:
                compile_command[1:1] = ["-I" + str(HERE / "inputs"), "-I" + str(HERE),
                                       "-ffile-prefix-map=" + str(REPO) + "=."]
            rebuilt_link = []
            for value in link_command:
                if value == previous_main:
                    value = str(obj)
                elif value.endswith(".o"):
                    digest = sha(value)
                    if digest not in expected_objects:
                        raise ValueError("frozen stock object changed")
                    frozen = output / "objects" / (digest + ".o")
                    if not frozen.exists():
                        shutil.copyfile(value, frozen)
                    if sha(frozen) != digest:
                        raise ValueError("archived stock object changed")
                    inputs[value] = digest
                    value = str(frozen)
                rebuilt_link.append(value)
            target = folder / "appspawn-x"
            rebuilt_link[rebuilt_link.index("-o") + 1] = str(target)
            rebuilt_link.append("-Wl,--trace")
            for phase, command in [("compile", compile_command), ("link", rebuilt_link)]:
                print(f"repeat={repeat} variant={variant} phase={phase} " + shlex.join(command), flush=True)
                completed = subprocess.run(command, check=True, cwd=REPO, capture_output=True, text=True)
                print(completed.stdout, end="", flush=True)
                print(completed.stderr, end="", flush=True)
                if phase == "link":
                    for line in completed.stdout.splitlines():
                        filename = Path(line.split("(", 1)[0])
                        if filename.is_file():
                            inputs[str(filename.resolve())] = sha(filename)
                    for value in command:
                        if value.startswith("-Wl,--version-script="):
                            filename = value.split("=", 1)[1]
                            inputs[filename] = sha(filename)
                records.append({"repeat": repeat, "variant": variant, "phase": phase, "command": command})
            identities[variant] = sha(target)
            if variant == "baseline" and identities[variant] != R3_SHA:
                raise ValueError("new-directory baseline did not reproduce r3 bytes")
            inputs[str(generated)] = sha(generated)
            dependencies = (folder / "host.d").read_text().replace("\\\n", " ").split(":", 1)[1].split()
            for name in dependencies:
                filename = Path(name)
                if not filename.is_absolute():
                    filename = REPO / filename
                inputs[str(filename)] = sha(filename)
        repeated.append(identities)
        print("REPEAT " + str(repeat) + " " + json.dumps(identities), flush=True)
    if repeated[0] != repeated[1]:
        raise ValueError("same-path rebuild was not byte-identical")
    for filename in [HERE / "build.py", HERE / "source.py", HERE / "n11h-owner.h", HERE / "elf_readonly.py", receipt_path,
                     Path(recipe["runs"][0]["commands"][0][0]).parent / "ld.lld"]:
        inputs[str(filename)] = sha(filename)
    report = {"schema": "n11h-r3-host-build-v1", "deployed_baseline_sha256": R3_SHA,
              "compiler_sha256": recipe["compiler_sha256"], "source_baseline_sha256": BASE_SHA,
              "candidate_source_sha256": sha(snapshot), "resident_compat_sha256": sha(HERE / "inputs/resident-compat.h"),
              "repeated": repeated, "repeat_identical": True, "commands": records,
              "inputs": [{"path": name, "sha256": digest} for name, digest in sorted(inputs.items())],
              "device_io": False, "runtime_generation": recipe["runtime_generation"],
              "generation_binding": "retain accepted r3 constants; final candidate manifest and child binding require coordinator review"}
    (output / "build-receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    patch = ''.join(difflib.unified_diff(original.read_text().splitlines(True), snapshot.read_text().splitlines(True),
                                       fromfile="a/westlake_stock_host_main.c", tofile="b/westlake_stock_host_main.c"))
    (HERE / "stock-host.patch").write_text(patch)
    print("BUILD PASS: exact65cc baseline; two byte-identical candidate builds; no device IO", flush=True)


if __name__ == "__main__":
    main()
