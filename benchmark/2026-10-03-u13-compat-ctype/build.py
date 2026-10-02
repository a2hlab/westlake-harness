import argparse
import json
from pathlib import Path
import shlex
import shutil
import subprocess

from common import HERE, OLD, PRIOR, REPO, SDK, capture, expand, portable, save, sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-only", action="store_true")
    args = parser.parse_args()
    out = HERE / ".artifacts"
    out.mkdir(exist_ok=True)
    receipt_path = PRIOR / "build-receipt.json"
    receipt = json.loads(receipt_path.read_text())
    link = [expand(value) for value in receipt["commands"][2]["command"]]
    compiler = Path(link[0])
    if sha(compiler) != receipt["compiler_sha256"]:
        raise ValueError("frozen compiler mismatch")
    baseline = PRIOR / ".artifacts/candidate1.so"
    if sha(baseline) != OLD:
        raise ValueError("admitted b2 baseline mismatch")
    inputs = [dict(path=receipt_path, sha256=sha(receipt_path)), dict(path=compiler, sha256=sha(compiler))]
    for row in receipt["source_and_object_inputs"]:
        path = Path(expand(row["path"]))
        if sha(path) != row["sha256"]:
            raise ValueError("frozen input mismatch: " + str(path))
        inputs.append(dict(path=path, sha256=sha(path)))
    for value in link:
        if value.endswith(".o"):
            inputs.append(dict(path=Path(value), sha256=sha(value)))
    mapping = Path(next(value.split("=", 1)[1] for value in link if value.startswith("-Wl,--version-script=")))
    inputs.append(dict(path=mapping, sha256=sha(mapping)))
    commands = []

    def execute(command):
        print(shlex.join([str(value) for value in command]), flush=True)
        process = subprocess.run(command, cwd=REPO)
        commands.append(dict(command=command, exit_code=process.returncode))
        if process.returncode:
            raise ValueError("build failed")

    repeated = []
    for repeat in [1, 2]:
        command = list(link)
        command[command.index("-o") + 1] = str(out / ("baseline" + str(repeat) + ".so"))
        execute(command)
        digest = sha(command[command.index("-o") + 1])
        if digest != OLD:
            raise ValueError("b2 byte reproduction failed; stop")
        repeated.append(dict(baseline=digest))
        print("BASELINE " + str(repeat) + " " + digest, flush=True)
    if args.baseline_only:
        save("baseline-receipt.json", dict(baseline_reproduced=True, repeated=repeated, inputs=inputs,
             compiler_sha256=sha(compiler), commands=commands, execution_enabled=False))
        return
    source = HERE / "ctype_compat.c"
    source_identity = json.loads((HERE / "sources.json").read_text())
    if sha(source) != source_identity["candidate_source_sha256"]:
        raise ValueError("reviewed ctype source mismatch")
    inputs.append(dict(path=source, sha256=sha(source)))
    for row in source_identity["sources"]:
        path = HERE / row["snapshot"]
        if sha(path) != row["sha256"]:
            raise ValueError("original table/header snapshot drift")
        inputs.append(dict(path=path, sha256=sha(path)))
    inputs.append(dict(path=HERE / "inputs/shim/ctype.h", sha256=sha(HERE / "inputs/shim/ctype.h")))
    candidate_map = out / "candidate.map"
    names = subprocess.check_output(["llvm-nm", "-D", "--defined-only", "--format=just-symbols", baseline], text=True).splitlines()
    candidate_map.write_text("{ global: " + "; ".join(sorted(set(names + ["_ctype_"]))) + "; local: *; };\n")
    for repeat in [1, 2]:
        object_path = out / "ctype_compat.o"
        execute([compiler, "--target=aarch64-linux-ohos", "--sysroot=" + str(SDK / "sysroot"),
                 "-std=c11", "-O2", "-g", "-fPIC", "-ffile-prefix-map=" + str(REPO) + "=.",
                 "-I" + str(HERE / "inputs/shim"),
                 "-I" + str(HERE / "inputs/aosp/libc/upstream-openbsd/lib/libc/include"),
                 "-c", source, "-o", object_path])
        command = ["-Wl,--version-script=" + str(candidate_map) if value.startswith("-Wl,--version-script=") else value for value in link]
        command[command.index("-o") + 1] = str(out / ("candidate" + str(repeat) + ".so"))
        command.append(str(object_path))
        execute(command)
        repeated[repeat - 1]["candidate"] = sha(command[command.index("-o") + 1])
        repeated[repeat - 1]["ctype_object"] = sha(object_path)
        print("REPEAT " + str(repeat) + " " + json.dumps(repeated[repeat - 1]), flush=True)
    if repeated[0] != repeated[1]:
        raise ValueError("repeated build differs")
    save("build-receipt.json", dict(baseline_reproduced=True, same_bytes=True, repeated=repeated,
         inputs=inputs, compiler_sha256=sha(compiler), commands=commands, added_exports=["_ctype_"],
         execution_enabled=False, method="Exact frozen b2 objects and link; one new data object plus one public version-map name"))


if __name__ == "__main__":
    main()
