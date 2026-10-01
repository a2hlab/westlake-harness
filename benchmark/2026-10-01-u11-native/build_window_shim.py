import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess


HERE = Path(__file__).resolve().parent
SOURCE_PATH = "benchmark/2026-10-01-n10-native/flutter/libandroid_webview_shim.c"
SOURCE_SHA = "c8772d05c5a815f1820809d6c1a6af265e51514c297d82bf427dd6a17b0e7f43"
SOURCE_COMMIT = "bf07c8e4d612b8cd721ebee4ab3b1aadcf73019f"
RUNTIME_SHA = "ac59dec077195bc7678c712505b0d802c56e07edea8d049be4a188d20485b7bf"


def digest(filename):
    return hashlib.sha256(Path(filename).read_bytes()).hexdigest()


def substitute(text, old, new):
    if text.count(old) != 1:
        raise ValueError("donor edit boundary mismatch: " + old[:60])
    return text.replace(old, new)


def donor_source(filename):
    if digest(filename) != SOURCE_SHA:
        raise ValueError("N10 donor source identity mismatch")
    original = filename.read_text()
    helpers = original[original.index("typedef struct WlLockedPixels {"):original.index("static void *bridge_symbol(")]
    lock = original[original.index("int32_t ANativeWindow_lock("):original.index("int32_t ANativeWindow_unlockAndPost(")]
    post_start = original.index("int32_t ANativeWindow_unlockAndPost(")
    post_end = original.index("\n/*", post_start)
    post = original[post_start:post_end]
    lock = substitute(lock, "int32_t ANativeWindow_lock(", "static int32_t U11DonorWindowLock(")
    post = substitute(post, "int32_t ANativeWindow_unlockAndPost(", "static int32_t U11DonorWindowPost(")
    lock = substitute(lock, "if (result != 0) {\n                    result = OH_NativeBuffer_Map(native_buffer, &mapped_addr);\n                }",
                      "if (result == 0) fence_fd = -1;\n                else if (fence_fd < 0) result = OH_NativeBuffer_Map(native_buffer, &mapped_addr);")
    helpers = substitute(helpers, "    int32_t key;\n", "")
    prefix = "\n".join(["#include <stddef.h>", "#include <stdint.h>", "#include <stdio.h>",
                        "#include <stdlib.h>", "#include <string.h>", "#include <unistd.h>",
                        "#include <errno.h>", "#include <dlfcn.h>"])
    checks = """
_Static_assert(offsetof(WlOHBufferHandle, stride) == 8, "OH byte stride offset");
_Static_assert(offsetof(WlOHBufferHandle, format) == 20, "OH format offset");
_Static_assert(offsetof(WlOHBufferHandle, vir_addr) == 32, "OH pixels offset");
_Static_assert(offsetof(WlOHBufferHandle, phy_addr) == 40, "OH physical address offset");
_Static_assert(sizeof(WlANativeWindowBuffer) == 48, "Android output buffer ABI");
"""
    wrapper = (HERE / "window-lock/owner_wrappers.c").read_text()
    result = prefix + "\n" + helpers + checks + lock + post + wrapper
    return result, {"donor_sha256": SOURCE_SHA, "donor_commit": SOURCE_COMMIT,
                    "donor_path": SOURCE_PATH, "donor_functions": ["ANativeWindow_lock:980", "ANativeWindow_unlockAndPost:1145"],
                    "adaptations": ["export only lock/post; all other APIs use current runtime dependency",
                                    "resolve existing oh_anw_get_oh before raw OH donor calls",
                                    "per-window mutex registry around original thread-local donor state",
                                    "SET_USAGE opcode5 CPU usage3 before dequeue",
                                    "full-buffer dirty expansion with null donor region",
                                    "remove donor trailing key field to match frozen OH BufferHandle",
                                    "MapWaitFence success owns fence; ordinary Map fallback only without a fence",
                                    "cancel buffer on failed post"],
                    "wrapper_sha256": digest(HERE / "window-lock/owner_wrappers.c")}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspaces", type=Path, default=os.environ.get("WORKSPACES", HERE.parents[2]))
    parser.add_argument("--sdk", type=Path, default=os.environ.get("OHOS_SDK", "/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    workspaces = args.workspaces.resolve()
    source_file = workspaces / "westlake-harness" / SOURCE_PATH
    runtime = workspaces / "westlake-generation-u9-j10g-238ffc14/native/payload/android/lib64/liboh_android_runtime.so"
    surface = workspaces / "westlake-inputs/oh61-link-inputs/system-lib64/chipset-sdk-sp/libsurface.z.so"
    if digest(runtime) != RUNTIME_SHA:
        raise ValueError("current runtime identity mismatch")
    args.out.mkdir(parents=True, exist_ok=True)
    source, receipt = donor_source(source_file)
    generated = args.out / "libandroid_window_shim.c"
    generated.write_text(source)
    compiler = args.sdk / "llvm/bin/clang"
    target = args.out / "libandroid.so"
    command = [str(compiler), "--target=aarch64-linux-ohos", "--sysroot=" + str(args.sdk / "sysroot"),
               "-std=gnu11", "-fPIC", "-O2", "-g", "-fvisibility=hidden", "-ftls-model=initial-exec",
               "-shared", "-Wl,-soname,libandroid.so", "-Wl,--no-undefined", "-Wl,--build-id=sha1",
               "-Wl,--version-script=" + str(HERE / "window-lock/exports.map"),
               str(generated), "-Wl,--no-as-needed", str(runtime), str(surface), "-lc", "-o", str(target)]
    subprocess.run(command, check=True)
    resource = args.sdk / "llvm/lib/clang/15.0.4"
    closure = [args.sdk / "llvm/bin/ld.lld", resource / "lib/aarch64-linux-ohos/libclang_rt.builtins.a",
               resource / "lib/aarch64-linux-ohos/clang_rt.crtbegin.o", resource / "lib/aarch64-linux-ohos/clang_rt.crtend.o",
               args.sdk / "llvm/lib/aarch64-linux-ohos/libunwind.a",
               args.sdk / "sysroot/usr/lib/aarch64-linux-ohos/crti.o", args.sdk / "sysroot/usr/lib/aarch64-linux-ohos/crtn.o",
               args.sdk / "sysroot/usr/lib/aarch64-linux-ohos/libc.so"]
    receipt["toolchain_link_inputs"] = [{"path": "$OHOS_SDK/" + str(filename.relative_to(args.sdk)), "sha256": digest(filename)} for filename in closure]
    fence_header = args.sdk / "sysroot/usr/include/native_buffer/native_buffer.h"
    receipt["fence_contract_reference"] = {"path": "$OHOS_SDK/sysroot/usr/include/native_buffer/native_buffer.h:360", "sha256": digest(fence_header), "kind": "SDK declaration, not proof of target implementation behavior"}
    roots = [(str(args.out.resolve()), "$OUT"), (str(args.out), "$OUT"),
             (str(args.sdk.resolve()), "$OHOS_SDK"), (str(HERE.parents[1]), "$REPO"), (str(workspaces), "$WORKSPACES"), (str(Path.home()), "$HOME")]
    dependency_text = subprocess.check_output([str(compiler), "--target=aarch64-linux-ohos", "--sysroot=" + str(args.sdk / "sysroot"),
                                               "-std=gnu11", "-M", "-MT", "shim", str(generated)], text=True)
    header_paths = shlex.split(dependency_text.split(":", 1)[1].replace("\\\n", " "))
    receipt["header_dependencies"] = []
    for name in sorted(set(header_paths)):
        filename = Path(name)
        portable_name = str(filename.resolve())
        for before, after in roots:
            portable_name = portable_name.replace(before, after)
        receipt["header_dependencies"].append({"path": portable_name, "sha256": digest(filename)})
    portable_command = []
    for argument in command:
        for before, after in roots:
            argument = argument.replace(before, after)
        portable_command.append(argument)
    receipt.update({"compiler_sha256": digest(compiler), "runtime_sha256": digest(runtime),
                    "build_script_sha256": digest(HERE / "build_window_shim.py"),
                    "exports_map_sha256": digest(HERE / "window-lock/exports.map"),
                    "surface_link_input_sha256": digest(surface), "generated_source_sha256": digest(generated),
                    "candidate_sha256": digest(target), "command": portable_command,
                    "board_touched": False, "superset_gate": "pending explicit approval of missing JNI inline wrapper",
                    "assembled_single_owner_gate": "pending final same-generation namespace/map assertions"})
    (args.out / "build-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"candidate_sha256": receipt["candidate_sha256"], "runtime_sha256": RUNTIME_SHA}))


if __name__ == "__main__":
    main()
