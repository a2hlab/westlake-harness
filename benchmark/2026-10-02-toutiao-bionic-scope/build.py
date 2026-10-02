import json
from pathlib import Path
import shlex
import shutil
import subprocess

from audit import COMPAT, HERE, REPO, WS, elf, portable, save, sha


def main():
    previous = REPO / "benchmark/2026-10-01-u10-native-shims"
    receipt_path = previous / "evidence/build-receipt.json"
    receipt = json.loads(receipt_path.read_text())
    link = [value.replace("$REPO", str(REPO)).replace("$OUT", str(previous / ".artifacts"))
            .replace("$OHOS_SDK", "/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native")
            .replace("$OH61_LINK_INPUTS", str(WS / "westlake-inputs/oh61-link-inputs/system-lib64")) for value in receipt["commands"][-1]]
    compiler = Path(link[0])
    if sha(compiler) != receipt["compiler_sha256"]:
        raise ValueError("deployed recipe compiler mismatch")
    out = HERE / ".artifacts/build"
    out.mkdir(parents=True, exist_ok=True)
    frozen = out / "objects"
    frozen.mkdir(exist_ok=True)
    inputs = {str(compiler): sha(compiler), str(receipt_path): sha(receipt_path)}
    for name, digest in receipt["link_inputs"].items():
        path = WS / "westlake-inputs/oh61-link-inputs/system-lib64" / name
        if sha(path) != digest:
            raise ValueError("frozen link provider drift")
        inputs[str(path)] = digest
    for index, value in enumerate(link):
        if value.endswith(".o"):
            path = Path(value)
            target = frozen / (sha(path) + ".o")
            shutil.copyfile(path, target)
            inputs[str(path)] = sha(path)
            link[index] = str(target)
    exports = elf(COMPAT.read_bytes())["all_exports"]
    runs, repeated = [], []

    def execute(variant, command):
        print(variant + " " + shlex.join(command), flush=True)
        completed = subprocess.run(command, capture_output=True, text=True, cwd=REPO)
        print(completed.stdout, end="", flush=True)
        print(completed.stderr, end="", flush=True)
        if completed.returncode:
            raise ValueError("build failed: " + variant)
        runs.append(dict(variant=variant, command=[portable(value) for value in command]))

    cmsg = out / "cmsg_android.o"
    sysroot = next(value for value in link if value.startswith("--sysroot="))
    compile_command = [str(compiler), "--target=aarch64-linux-ohos", sysroot, "-std=c11", "-fPIC", "-O2", "-g",
                       "-ffile-prefix-map=" + str(REPO) + "=.", "-c", str(HERE / "cmsg_android.c"), "-o", str(cmsg)]
    inputs[str(HERE / "cmsg_android.c")] = sha(HERE / "cmsg_android.c")
    for repeat in [1, 2]:
        execute("cmsg", compile_command)
        identities = {}
        for variant in ["baseline", "exports-only", "scope-global-reference"]:
            mapping = out / (variant + ".map")
            allowed = exports if variant == "baseline" else sorted(set(exports + ["__errno", "__cmsg_nxthdr"]))
            mapping.write_text("{ global: " + "; ".join(allowed) + "; local: *; };\n")
            target = out / (variant + ".so")
            command = ["-Wl,--version-script=" + str(mapping) if value.startswith("-Wl,--version-script=") else value for value in link]
            command[command.index("-o") + 1] = str(target)
            if variant != "baseline":
                command.append(str(cmsg))
            if variant == "scope-global-reference":
                command.append("-Wl,-z,global")
            execute(variant, command)
            identities[variant] = sha(target)
            if variant == "baseline" and sha(target) != sha(COMPAT):
                raise ValueError("baseline failed exact015aa3a6 reproduction; stop")
        repeated.append(identities)
        print("REPEAT " + str(repeat) + " " + json.dumps(identities), flush=True)
    if repeated[0] != repeated[1]:
        raise ValueError("repeated build not byte-identical")
    ndk = Path.home() / "Library/Android/sdk/ndk/23.1.7779620/toolchains/llvm/prebuilt/darwin-x86_64/sysroot/usr/include/sys/socket.h"
    donor = WS / "westlake-inputs/aosp-14.0.0_r1-src/bionic/libc/bionic/__cmsg_nxthdr.cpp"
    for path in [donor, ndk, previous / "baseline/src/misc_compat.cpp", previous / "baseline-inputs.json",
                 previous / "baseline/bionic_compat.map"]:
        inputs[str(path)] = sha(path)
    save("build-receipt.json", dict(device_io=False, repeated=repeated, same_bytes=True, baseline_reproduced=True,
         compiler_sha256=sha(compiler), inputs=[dict(path=portable(path), sha256=digest) for path, digest in sorted(inputs.items())],
         commands=runs, donor="AOSP14 cmsg body adapted to explicitly pinned Android LP64 structures; not OH msghdr",
         cmsg_header_reference="NDK23 LP64 header, not claimed AOSP14 header",
         scope_global_status="FLAG_SUPPORTED_BY_BINARY_SCOPE_OWNER_ORACLE_PENDING", no_host_policy_changes=True))


if __name__ == "__main__":
    main()
