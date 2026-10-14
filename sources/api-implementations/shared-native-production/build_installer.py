#!/usr/bin/env python3
"""Build the delivered final installer sources, reject partial legacy compilation."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from acquire import sha256, verify
from materialize import materialize


EXPECTED = "7048c7c50a828fc744b5f06e4e9ec50ac317a2272f33789249fc63e43a655a18"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--oh-root", type=Path, required=True)
    parser.add_argument("--aosp-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    args.out.mkdir(parents=True, exist_ok=False)
    out = args.out.resolve()
    environment = os.environ.copy()
    environment.update({"OH_ROOT": str(args.oh_root.resolve()), "AOSP_ROOT": str(args.aosp_root.resolve()), "A": str(args.aosp_root.resolve()), "BUILD_INNER_INVOKED": "1", "ADAPTER_ROOT": str(out / "adapter"), "APK_INSTALLER_BUILD_TMP": str(out / "objects")})
    compiler = args.oh_root / "prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang-15"
    lock = json.loads((here / "dependencies.lock.json").read_text())
    recipe = here / "FZ-001/recipes/compile_apk_installer.sh.original.txt.sh"
    receipt = {"argv": ["bash", str(recipe)], "expected_sha256": EXPECTED, "recipe_sha256": sha256(recipe), "historical_production_proven": False}
    exit_code = 2
    try:
        verify(compiler, lock["tools"]["clang-15"])
        receipt["materialized_sources"] = materialize("FZ-001/archive-source/adapter", out / "adapter")
        with (out / "build.stdout").open("wb") as stdout, (out / "build.stderr").open("wb") as stderr:
            result = subprocess.run(receipt["argv"], cwd=out, env=environment, stdout=stdout, stderr=stderr, check=False)
        receipt["producer_exit_code"] = result.returncode
        if result.returncode:
            raise ValueError("ORIGINAL_PRODUCER_FAILED")
        text = (out / "build.stdout").read_text(errors="backslashreplace")
        counts = re.findall(r"^  Compiled: (\d+)/(\d+)\s*$", text, re.M)
        if len(counts) != 1 or int(counts[0][0]) == 0 or counts[0][0] != counts[0][1]:
            raise ValueError("INCOMPLETE_COMPILATION " + repr(counts))
        artifact = out / "adapter/out/adapter/libapk_installer.so"
        strip = compiler.with_name("llvm-strip")
        with (out / "strip.stdout").open("wb") as stdout, (out / "strip.stderr").open("wb") as stderr:
            result = subprocess.run([str(strip), "--strip-unneeded", str(artifact)], stdout=stdout, stderr=stderr, check=False)
        receipt["strip_exit_code"] = result.returncode
        if result.returncode:
            raise ValueError("ORIGINAL_STRIP_FAILED")
        actual = sha256(artifact)
        receipt.update({"actual_sha256": actual, "bytes": artifact.stat().st_size, "byte_equal": actual == EXPECTED, "status": "NEW_BUILD_BYTE_EQUAL" if actual == EXPECTED else "NEW_BUILD_DIFFERENT"})
        exit_code = 0 if actual == EXPECTED else 3
    except (OSError, ValueError) as error:
        receipt.update({"status": "REJECT", "error": str(error)})
        (out / "failure.stderr").write_text(str(error) + "\n")
    receipt["exit_code"] = exit_code
    receipt["raw"] = [{"path": path.name, "sha256": sha256(path)} for path in out.glob("*.std*")]
    (out / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
