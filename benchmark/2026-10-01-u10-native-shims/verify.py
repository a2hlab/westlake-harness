import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

from gate import NEW_EXPORTS, validate


HERE = Path(__file__).resolve().parent


def digest(filename):
    return hashlib.sha256(Path(filename).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Replay U10 ABI gates against pinned APK consumers")
    parser.add_argument("--old", type=Path, required=True)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--abi-tool", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    sources = json.loads((HERE / "baseline-inputs.json").read_text())
    provenance = json.loads((HERE / "provenance.json").read_text())
    if digest(args.old) != sources["old_sha256"]:
        raise ValueError("old deployment identity mismatch")
    if digest(args.abi_tool) != provenance["abi_tool_sha256"]:
        raise ValueError("ABI gate tool identity mismatch")
    receipt = json.loads((args.build_dir / "build-receipt.json").read_text())
    for variant, expected in receipt["artifacts"].items():
        if digest(args.build_dir / ("libbionic_compat-" + variant + ".so")) != expected:
            raise ValueError("built artifact identity mismatch")
    for relative, expected in receipt["overlay_inputs"].items():
        if digest(HERE / relative) != expected:
            raise ValueError("overlay source identity mismatch")
    args.out.mkdir(parents=True, exist_ok=True)
    consumers = []
    for application in json.loads((HERE / "consumers.json").read_text())["apps"]:
        apk = Path(os.path.expandvars(application["apk"]))
        if digest(apk) != application["apk_sha256"]:
            raise ValueError("consumer APK identity mismatch: " + application["key"])
        with zipfile.ZipFile(apk) as archive:
            for member in application["members"]:
                content = archive.read(member["member"])
                if hashlib.sha256(content).hexdigest() != member["sha256"]:
                    raise ValueError("consumer DSO identity mismatch")
                target = args.out / member["file"]
                target.write_bytes(content)
                consumers += ["--consumer", str(target)]
    for variant, expected in [("baseline", set()), ("candidate", NEW_EXPORTS)]:
        output = args.out / (variant + "-abi.json")
        subprocess.run(["python3", str(args.abi_tool), "--old", str(args.old),
                        "--new", str(args.build_dir / ("libbionic_compat-" + variant + ".so")),
                        "--calls", "--json", str(output), *consumers], check=True)
        validate(json.loads(output.read_text()), expected)
    print("U10 ABI/CALLS/CONSUMER GATE PASS; PPSSPP namespace remains unsupported")


if __name__ == "__main__":
    main()
