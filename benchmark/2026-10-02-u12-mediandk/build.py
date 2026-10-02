import json
from pathlib import Path
import shutil
import subprocess

from collect import BASE, HERE, MASTER, SDK, WS, portable, run, save, sha


def main():
    compiler = SDK / "llvm/bin/clang"
    includes = ["-I" + str(HERE), "-I" + str(HERE / "inputs/public-types"),
                "-I" + str(HERE / "inputs/aosp14/media/ndk/include")]
    commands = []
    for number in [1, 2]:
        output = HERE / ".artifacts" / ("libmediandk-build" + str(number) + ".so")
        command = [compiler, "--target=aarch64-linux-ohos", "--sysroot=" + str(SDK / "sysroot"), "-std=c11", "-D_GNU_SOURCE",
                   "-fPIC", "-shared", "-O2", "-Werror", *includes, "-Wl,-soname,libmediandk.so", "-Wl,-z,defs",
                   "-Wl,--build-id=sha1", "-Wl,--version-script=" + str(HERE / "exports.map"), "-o", output, HERE / "candidate.c"]
        commands.append(run("build" + str(number), command))
    candidate = HERE / ".artifacts/libmediandk-build1.so"
    if sha(candidate) != sha(HERE / ".artifacts/libmediandk-build2.so"):
        raise ValueError("two builds differ")
    baseline = BASE / "payload/zigzag/libmediandk.so"
    if sha(baseline) != "110d02fc4bbb32ed241358c6329f6aa5e4849f021e5b224f9ae2b826f8fa75fb":
        raise ValueError("presence baseline mismatch")
    exports = set(subprocess.check_output(["llvm-nm", "-D", "--defined-only", "--format=just-symbols", candidate], text=True).splitlines())
    apis = json.loads((HERE / "api.json").read_text())
    expected = {row["symbol"] for row in apis["apis"]} | {"AMediaFormat_new", "westlake_mediandk_presence_provenance"}
    if exports != expected:
        raise ValueError("export allowlist mismatch")
    for name, path in [("baseline", baseline), ("candidate", candidate)]:
        commands.append(run("open-" + name, ["python3", MASTER / "scripts/lab/open_site_scan.py", path,
                                             "--json", HERE / ".artifacts" / ("open-" + name + ".json")]))
        value = json.loads((HERE / ".artifacts" / ("open-" + name + ".json")).read_text())
        save("evidence/open-" + name + ".json", value)
    commands.append(run("strings-mediandk", ["python3", MASTER / "scripts/lab/deployed_strings_diff.py", candidate,
                                            "--deployed", baseline], allowed=(0, 1)))
    commands.append(run("abi-mediandk", ["python3", MASTER / "scripts/lab/abi_diff.py", "--old", baseline, "--new", candidate,
                                        "--calls", "--consumer", HERE / ".artifacts/libunity.so", "--json", HERE / ".artifacts/abi-mediandk.json"]))
    save("evidence/abi-mediandk.json", json.loads((HERE / ".artifacts/abi-mediandk.json").read_text()))
    commands.append(run("candidate-dynamic", ["llvm-readelf", "-d", candidate]))
    commands.append(run("candidate-undefined", ["llvm-nm", "-D", "--undefined-only", candidate]))
    host = HERE / ".artifacts/test-provider"
    commands.append(run("host-build", ["clang", "-std=c11", "-D_GNU_SOURCE", "-O2", "-Werror", *includes, HERE / "test_provider.c", "-o", host]))
    commands.append(run("host-behavior", [host]))
    sources = [HERE / name for name in ["candidate.c", "objects.c.inc", "platform.h", "exports.map"]]
    save("build-receipt.json", dict(candidate_path=portable(candidate), candidate_sha256=sha(candidate),
         baseline_path=portable(baseline), baseline_sha256=sha(baseline), builds_identical=True,
         compiler=portable(compiler), compiler_sha256=sha(compiler),
         linker_sha256=sha(SDK / "llvm/bin/ld.lld"), sdk_libc_link_sha256=sha(SDK / "sysroot/usr/lib/aarch64-linux-ohos/libc.so"),
         sources={portable(path): sha(path) for path in sources}, source_inventory_sha256=sha(HERE / "sources.json"),
         exports=sorted(exports), commands=commands, deployment_authorized=False))
    print("libmediandk candidate=" + sha(candidate) + " builds=2 identical exports=" + str(len(exports)))


if __name__ == "__main__":
    main()
