from datetime import datetime
import argparse
import json
import sys

from finalize import HERE, MASTER, PRIOR, install, save
from reports import capture, expand


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewed", action="store_true")
    args = parser.parse_args()
    suffix = "-reviewed" if args.reviewed else ""
    build = HERE / "inputs/U14-BUILD.md"
    install(PRIOR / "inputs/U14-BUILD.md", build)
    for variant in ["common", "61b"]:
        root = HERE / variant
        composition = json.loads((root / ("reviewed-composition.json" if args.reviewed else "composition.json")).read_text())
        package = expand(composition["package"])
        output = root / ".artifacts" / ("t4b-" + datetime.now().strftime("%Y%m%dT%H%M%S%f") + ".json")
        records = [capture(root, "rb" + suffix, [sys.executable, MASTER / "knowledge/toolchains/art-r155/check_boot_oat_rb.py", package / "boot/arm64/boot.oat", "--image", package / "boot/arm64/boot.art"]),
            capture(root, "t4b" + suffix, [sys.executable, MASTER / "knowledge/toolchains/art-r155/t4b_build_switch_gate.py",
                "--libart", package / "native/payload/route/libart.so", "--oat", package / "boot/arm64/boot.oat", "--build", build, "--out", output]),
            capture(root, "frozen" + suffix, [sys.executable, MASTER / "scripts/lab/check_frozen.py", "--package", package / "native"])]
        save(root / "evidence" / ("t4b" + suffix + ".json"), json.loads(output.read_text()))
        save(root / ("artifact-gates" + suffix + ".json"), dict(bundle_sha256=composition["bundle_sha256"], records=records,
            all_exit_zero=all(row["exit_code"] == 0 for row in records),
            image_exception_scope="Separate exact-pair outer approval, not inferred from frozen gate", execution_enabled=False))
        if any(row["exit_code"] != 0 for row in records):
            raise ValueError("Fresh artifact gate failed")


if __name__ == "__main__":
    main()
