import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = Path(os.environ.get("WORKSPACES", REPO.parent))
MASTER = WS / "westlake-harness"
BASE = WS / "westlake-harness-bms/benchmark/2026-10-03-u13-effective-rebind/.artifacts/bundle-v4"
BASE_SHA = "91272eaf4cdda30b0c079575cd269959c6f6dab9f23a09a0fed567c20478bd28"
PLAN = WS / "westlake-harness-bms/benchmark/2026-10-03-u14-jar-image-plan"
BRIDGE_CHECKS = WS / "westlake-harness-bms/benchmark/2026-10-03-u14-native-assembly/.artifacts/u14-bridge-only-t8/native/native-checks"
RELEASE = WS / "westlake-inputs/generations/u14-bt-bake-0349-87cf-v1"
PARTIAL = HERE / ".artifacts/native-jar"
sys.path.insert(0, str(MASTER / "scripts/lab"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def portable(value):
    if isinstance(value, dict):
        return {name: portable(item) for name, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [portable(item) for item in value]
    if isinstance(value, Path):
        value = str(value)
    if isinstance(value, str):
        value = re.sub(re.escape(str(REPO)) + r"/(benchmark/[^/]+/\.artifacts)(?=/|[\s'\"]|$)", r"$WORKSPACES/westlake-harness-bms/\1", value)
        for root, token in [(REPO, "$REPO"), (WS, "$WORKSPACES"), (Path.home(), "$HOME")]:
            value = token if value == str(root) else value.replace(str(root) + "/", token + "/")
        value = value.replace("/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native", "$OHOS_SDK")
        value = re.sub(r"/home/[^/\s'\"]+", "$LAB_HOME", value)
    return value


def save(path, value, compact=False):
    path = Path(path)
    if not path.is_absolute():
        path = HERE / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(portable(value), indent=None if compact else 2) + "\n")


def capture(name, argv, timeout=900):
    raw = HERE / ".artifacts/raw" / (name + ".txt")
    raw.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.run([str(item) for item in argv], capture_output=True, text=True, errors="replace", timeout=timeout)
    raw.write_text(process.stdout + process.stderr)
    proof = HERE / "evidence" / (name + ".txt")
    proof.parent.mkdir(parents=True, exist_ok=True)
    proof.write_text(portable(raw.read_text()))
    print(name + " exit=" + str(process.returncode), flush=True)
    return dict(command=portable(argv), exit_code=process.returncode, raw=portable(raw), raw_sha256=sha(raw), evidence=portable(proof), evidence_sha256=sha(proof))
