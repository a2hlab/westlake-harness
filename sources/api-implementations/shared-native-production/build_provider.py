#!/usr/bin/env python3
"""Execute the original provider argv with explicit relocated, pinned inputs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from acquire import sha256, verify


EXPECTED = "0509fe235a7883b5cd9b57477221cb868465de944c6f70ed0cf2835b0fe4a97c"


def provider_commands(generation, output, source_root):
    originals = json.loads((source_root / "FZ-002/build-evidence/original-commands.json").read_text())
    original_prefix = originals[0][0].split("/.work/product-tls-generation/")[0]
    original_source = originals[0][originals[0].index("-c") + 1]
    original_object = originals[0][originals[0].index("-o") + 1]
    source = str(generation / "adapter/framework/appspawn-x/src/child_main_after_stock.cpp")
    object_path = str(output / "child_main_after_stock.o")

    def relocate(value):
        if value == original_source:
            return source
        if value == original_object:
            return object_path
        return value.replace(original_prefix, str(generation))

    commands = [[relocate(value) for value in command] for command in originals]
    commands[1][commands[1].index("-o") + 1] = str(output / "libwestlake_android_runtime_provider.so")
    return commands


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    generation = args.generation.resolve()
    output = args.out.resolve()
    if not generation.is_dir() or output.exists():
        parser.error("generation must exist and output must be a new directory")
    output.mkdir(parents=True)
    commands = provider_commands(generation, output, here)
    receipt = {"argv": commands, "cwd": str(generation), "execution_requested": args.run, "frozen_sha256": EXPECTED, "steps": [], "historical_production_proven": False}
    exit_code = 2
    try:
        lock = json.loads((here / "dependencies.lock.json").read_text())
        marker = json.loads((generation / "restore-receipt.json").read_text())
        archives = {item["id"]: item for item in lock["archives"]}
        if marker.get("status") != "RESTORED_NOT_BUILT" or marker.get("generation_path") != str(generation):
            raise ValueError("REFUSE_NON_PRIVATE_RESTORED_GENERATION")
        if marker.get("inputs_sha256") != archives["FZ002_GENERATION"]["sha256"] or marker.get("external_sha256") != archives["FZ002_PLATFORM_LINK"]["sha256"]:
            raise ValueError("RESTORED_ARCHIVE_BINDING_MISMATCH")
        for name, relative in [
            ("clang-15", ".work/product-tls-generation/frozen/toolchain/bin/clang-15"),
            ("ld.lld", ".work/product-tls-generation/frozen/toolchain/bin/ld.lld"),
            ("libc.so", ".work/product-tls-generation/frozen/sysroot/lib/aarch64-linux-ohos/libc.so"),
        ]:
            path = generation / relative
            verify(path, lock["tools"][name])
            receipt.setdefault("tools", []).append({"name": name, "sha256": sha256(path)})
        if not args.run:
            receipt["status"] = "PREVIEW_NOT_EXECUTED"
            exit_code = 0
        else:
            source = here / "FZ-002/src/child_main_after_stock.cpp"
            verify(source, "3fc2060ea0f705cce50555caa509b215ea64edc343a714b20c438dba505b61d8")
            staged_source = generation / "adapter/framework/appspawn-x/src/child_main_after_stock.cpp"
            if staged_source.is_symlink() or not staged_source.is_file():
                raise ValueError("INVALID_STAGED_SOURCE")
            receipt["source_overlay"] = {"before_sha256": sha256(staged_source), "after_sha256": sha256(source), "scope": "private freshly restored generation only; signed source and artifact untouched"}
            staged_source.write_bytes(source.read_bytes())
            for index, command in enumerate(commands):
                stdout_path = output / f"step-{index}.stdout"
                stderr_path = output / f"step-{index}.stderr"
                with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
                    environment = os.environ.copy()
                    runtime = generation / ".work/product-tls-generation/frozen/toolchain/runtime"
                    environment["LD_LIBRARY_PATH"] = str(runtime) + ":" + environment.get("LD_LIBRARY_PATH", "")
                    result = subprocess.run(command, cwd=generation, env=environment, stdout=stdout, stderr=stderr, check=False)
                receipt["steps"].append({"exit_code": result.returncode, "stdout_sha256": sha256(stdout_path), "stderr_sha256": sha256(stderr_path)})
                if result.returncode:
                    raise ValueError(f"PRODUCER_STEP_FAILED {index} rc={result.returncode}")
            artifact = output / "libwestlake_android_runtime_provider.so"
            actual = sha256(artifact)
            receipt.update({"output_sha256": actual, "byte_equal": actual == EXPECTED, "bytes": artifact.stat().st_size})
            receipt["status"] = "NEW_BUILD_BYTE_EQUAL" if actual == EXPECTED else "NEW_BUILD_DIFFERENT_NOT_HISTORICAL_EXACT"
            exit_code = 0 if actual == EXPECTED else 3
    except (OSError, ValueError) as error:
        receipt["status"] = "REJECT"
        receipt["error"] = str(error)
        (output / "failure.stderr").write_text(str(error) + "\n")
    receipt["exit_code"] = exit_code
    (output / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
