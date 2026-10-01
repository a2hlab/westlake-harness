import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


HERE = Path(__file__).resolve().parent
SOURCES = ["system_properties.cpp", "malloc_compat.cpp", "fdsan_stubs.cpp",
           "misc_compat.cpp", "abort_message_compat.cpp", "liblog_android_supplement.cpp",
           "sync_builtins.c"]


def digest(filename):
    return hashlib.sha256(Path(filename).read_bytes()).hexdigest()


def verify_sources():
    receipt = json.loads((HERE / "baseline-inputs.json").read_text())
    for entry in receipt["files"]:
        relative = entry["path"].removeprefix(receipt["compat_prefix"])
        target = HERE / "baseline" / relative
        if digest(target) != entry["sha256"]:
            raise ValueError("baseline source SHA mismatch: " + relative)
    return receipt


def main():
    parser = argparse.ArgumentParser(description="Build pinned U10 compat baseline and candidate offline")
    parser.add_argument("--sdk", type=Path, default=os.environ.get("OHOS_SDK", "/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native"))
    parser.add_argument("--old", type=Path, required=True)
    parser.add_argument("--link-inputs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--nm", default=shutil.which("llvm-nm") or "llvm-nm")
    args = parser.parse_args()
    receipt = verify_sources()
    if digest(args.old) != receipt["old_sha256"]:
        raise ValueError("deployed compat identity mismatch")
    sdk = args.sdk.resolve()
    compiler = sdk / "llvm/bin/clang"
    strip = sdk / "llvm/bin/llvm-strip"
    base = HERE / "baseline"
    args.out.mkdir(parents=True, exist_ok=True)
    exports = subprocess.check_output([args.nm, "-D", "--defined-only", "--format=just-symbols", str(args.old)], text=True).split()
    commands = []
    common = [str(compiler), "--target=aarch64-linux-ohos", "--sysroot=" + str(sdk / "sysroot"),
              "-fPIC", "-O2", "-g", "-D__OHOS__", "-D_GNU_SOURCE", "-D_POSIX_SOURCE",
              "-I" + str(base / "include")]

    def execute(command):
        commands.append(command)
        subprocess.run(command, check=True)

    objects = []
    for filename in SOURCES:
        target = args.out / (Path(filename).stem + ".o")
        extra = ["-std=c11", "-D__ANDROID_API__=34", "-DPAGE_SIZE=4096"] if filename.endswith(".c") else ["-std=gnu++17", "-DPARAM_VALUE_LEN_MAX=96", "-Wno-constant-conversion"]
        execute(common + extra + ["-c", str(base / "src" / filename), "-o", str(target)])
        objects.append(str(target))
    extra_objects = []
    for filename in ["android_dlopen_ext.c", "gnu_strerror_r.c"]:
        target = args.out / (Path(filename).stem + ".o")
        execute(common + ["-std=c11", "-c", str(HERE / "overlay" / filename), "-o", str(target)])
        extra_objects.append(str(target))
    for variant, allowed, inputs in [
        ("baseline", exports, objects),
        ("candidate", exports + receipt["new_exports"], objects + extra_objects),
    ]:
        mapping = args.out / (variant + ".map")
        mapping.write_text("{ global: " + "; ".join(allowed) + "; local: *; };\n")
        target = args.out / ("libbionic_compat-" + variant + ".so")
        execute([str(compiler), "--target=aarch64-linux-ohos", "--sysroot=" + str(sdk / "sysroot"),
                 "-fuse-ld=lld", "-shared", "-nostdlib++", "-Wl,-z,defs", "-Wl,-z,now",
                 "-Wl,--build-id=sha1", "-Wl,--hash-style=both", "-Wl,--no-undefined",
                 "-Wl,-soname,libbionic_compat.so", "-Wl,--version-script=" + str(mapping),
                 "-L" + str(args.link_inputs / "platformsdk"), "-L" + str(args.link_inputs / "chipset-sdk-sp"),
                 "-o", str(target), *inputs, "-Wl,--no-as-needed", "-lbegetutil.z", "-lc++",
                 "-Wl,--as-needed", "-lc", "-ldl", "-lpthread"])
    build_receipt = {
        "schema": "u10-native-shim-build-v1",
        "baseline_inputs_sha256": digest(HERE / "baseline-inputs.json"),
        "compiler_sha256": digest(compiler),
        "compiler_version": subprocess.check_output([str(compiler), "--version"], text=True),
        "strip_sha256": digest(strip),
        "strip_policy": "retain local function labels for accurate abi_diff --calls boundaries",
        "sdk_sysroot_libc_sha256": digest(sdk / "sysroot/usr/lib/aarch64-linux-ohos/libc.so"),
        "link_inputs": {filename: digest(args.link_inputs / filename) for filename in ["platformsdk/libbegetutil.z.so", "chipset-sdk-sp/libc++.so"]},
        "commands": [[argument.replace(str(sdk), "$OHOS_SDK")
                      .replace(str(args.link_inputs.resolve()), "$OH61_LINK_INPUTS")
                      .replace(str(args.out.resolve()), "$OUT")
                      .replace(str(args.out), "$OUT")
                      .replace(str(HERE.parents[1]), "$REPO")
                      for argument in command] for command in commands],
        "overlay_inputs": {str(filename.relative_to(HERE)): digest(filename)
                           for filename in sorted((HERE / "overlay").iterdir())},
        "headers": "SDK native C/C++ headers; historical forced libcxx_compat.h omitted",
        "artifacts": {variant: digest(args.out / ("libbionic_compat-" + variant + ".so")) for variant in ["baseline", "candidate"]},
        "caller_preservation_requires_aarch64_tail_branch_check": True,
        "ppsspp_namespace_fixed": False,
    }
    (args.out / "build-receipt.json").write_text(json.dumps(build_receipt, indent=2) + "\n")
    print(json.dumps(build_receipt["artifacts"]))


if __name__ == "__main__":
    main()
