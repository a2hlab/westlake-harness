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
ASSEMBLY_BASE = WS / "westlake-harness-bms/benchmark/2026-10-03-u13-effective-rebind/.artifacts/bundle-v4"
ASSEMBLY_SHA = "91272eaf4cdda30b0c079575cd269959c6f6dab9f23a09a0fed567c20478bd28"
BRIDGE = "7daa5435333ab99c2360dfe5ad5b75180ba0b8118d4f69f6750764c01b546452"
OLD_BRIDGE = "84695d62f515cfec6bb317c959ec55b1d5085bf82303f792a764cf549a22267a"
DONOR = WS / "westlake-inputs/generations/u14-m5m6-m5m6-a"
REPEAT = WS / "westlake-inputs/generations/u14-m5m6-m5m6-b"
INTERMEDIATE = WS / "westlake-inputs/generations/u14-r1r3-v4/out/liboh_adapter_bridge.so"
sys.path.insert(0, str(MASTER / "scripts/lab"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def portable(value):
    if isinstance(value, dict):
        return {name: portable(item) for name, item in value.items()}
    if isinstance(value, list):
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


def expand(value):
    return Path(value.replace("$WORKSPACES", str(WS)).replace("$REPO", str(REPO)))


def save(name, value, compact=False):
    path = name if isinstance(name, Path) else HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(portable(value), indent=None if compact else 2) + "\n")


def capture(name, command, timeout=600):
    raw = HERE / ".artifacts/raw" / (name + ".txt")
    raw.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.run([str(item) for item in command], capture_output=True, text=True, errors="replace", timeout=timeout)
    raw.write_text(process.stdout + process.stderr)
    evidence = HERE / "evidence" / (name + ".txt")
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(portable(raw.read_text()))
    print(name + " exit=" + str(process.returncode), flush=True)
    return dict(command=portable(command), exit_code=process.returncode, raw=portable(raw), raw_sha256=sha(raw), evidence=portable(evidence))
