import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
LOADER = HERE / "native-loader"


def digest(filename):
    return hashlib.sha256(Path(filename).read_bytes()).hexdigest()


def validate_policy():
    relative = "policy/native_bridge_policy.v1.json"
    baseline = json.loads((LOADER / "baseline" / relative).read_text())
    candidate = json.loads((LOADER / "overlay" / relative).read_text())
    shared = candidate.pop("shared_sonames")
    previous = baseline.pop("shared_sonames")
    if candidate != baseline or shared != previous + ["libstdc++.so"]:
        raise ValueError("policy must add exactly one libstdc++ edge")
    if "libc++.so" in shared:
        raise ValueError("platform libc++ must not enter app shared policy")
    for entry in json.loads((LOADER / "inputs.json").read_text())["files"]:
        original = entry["path"]
        filename = LOADER / "baseline" / original.removeprefix("adapter/framework/native-loader-oh/")
        if original.startswith("bms/"):
            filename = LOADER / "dependencies" / Path(original).name
        if digest(filename) != entry["sha256"]:
            raise ValueError("loader input mismatch: " + original)
    return previous, shared


def main():
    parser = argparse.ArgumentParser(description="Build one-edge NativeLoader policy revision")
    parser.add_argument("--sdk", type=Path, default=os.environ.get("OHOS_SDK", "/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native"))
    parser.add_argument("--native-payload", type=Path, required=True)
    parser.add_argument("--link-inputs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    previous, shared = validate_policy()
    identities = json.loads((LOADER / "inputs.json").read_text())
    for filename, expected in [("libnativeloader.so", identities["old_sha256"]),
                               ("libapp_native_loader.so", identities["unchanged_ANL_sha256"])]:
        if digest(args.native_payload / filename) != expected:
            raise ValueError("U9 loader identity mismatch: " + filename)
    sdk = args.sdk.resolve()
    compiler = sdk / "llvm/bin/clang"
    commands = []
    args.out.mkdir(parents=True, exist_ok=True)
    for variant in ["baseline", "candidate"]:
        objects = []
        directory = args.out / variant
        directory.mkdir(exist_ok=True)
        common = [str(compiler), "--target=aarch64-linux-ohos", "--sysroot=" + str(sdk / "sysroot"),
                  "-std=gnu++17", "-fPIC", "-O2", "-g", "-D_GNU_SOURCE",
                  "-include", str(LOADER / "platform-config.h"), "-fno-exceptions",
                  "-fno-rtti", "-fvisibility=hidden"]
        if variant == "candidate":
            common += ["-I" + str(LOADER / "overlay/include")]
        common += ["-I" + str(LOADER / "baseline/include"),
                   "-I" + str(LOADER / "baseline/src"), "-I" + str(LOADER / "dependencies")]
        for filename in ["native_loader.cpp", "native_loader_registry.cpp", "system_loader.cpp"]:
            target = directory / (filename + ".o")
            command = common + ["-c", str(LOADER / "baseline/src" / filename), "-o", str(target)]
            commands.append(command)
            subprocess.run(command, check=True)
            objects.append(str(target))
        target = args.out / ("libnativeloader-" + variant + ".so")
        command = [str(compiler), "--target=aarch64-linux-ohos", "--sysroot=" + str(sdk / "sysroot"),
                   "-fuse-ld=lld", "-shared", "-nostdlib++", "-Wl,-z,defs", "-Wl,-z,now",
                   "-Wl,--hash-style=both", "-Wl,-soname,libnativeloader.so",
                   "-Wl,--version-script=" + str(LOADER / "baseline/native_loader.map"),
                   *objects, str(args.native_payload / "libapp_native_loader.so"),
                   str(args.link_inputs / "chipset-sdk-sp/libc++.so"),
                   "-lc", "-ldl", "-lpthread", "-o", str(target)]
        commands.append(command)
        subprocess.run(command, check=True)
    roots = [(str(sdk), "$OHOS_SDK"), (str(args.native_payload.resolve()), "$U9_NATIVE_PAYLOAD"),
             (str(args.link_inputs.resolve()), "$OH61_LINK_INPUTS"),
             (str(args.out.resolve()), "$OUT"), (str(args.out), "$OUT"),
             (str(HERE.parents[1]), "$REPO")]
    for command in commands:
        for index, argument in enumerate(command):
            for before, after in roots:
                argument = argument.replace(before, after)
            command[index] = argument
    receipt = {"schema": "u10-policy-build-v1", "compiler_sha256": digest(compiler),
               "compiler_version": subprocess.check_output([str(compiler), "--version"], text=True),
               "sdk_config_site_sha256": digest(sdk / "llvm/include/libcxx-ohos/include/c++/v1/__config_site"),
               "platform_cpp_namespace": "__h, matching the pinned OH runtime and deployed loader imports; otherwise SDK defaults to __n1",
               "unchanged_ANL_sha256": digest(args.native_payload / "libapp_native_loader.so"),
               "OH_libcxx_sha256": digest(args.link_inputs / "chipset-sdk-sp/libc++.so"),
               "policy_before": previous, "policy_after": shared, "commands": commands,
               "artifacts": {variant: digest(args.out / ("libnativeloader-" + variant + ".so")) for variant in ["baseline", "candidate"]}}
    (args.out / "loader-build-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt["artifacts"]))


if __name__ == "__main__":
    main()
