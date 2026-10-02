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
BASE = WS / "westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle"
PREVIOUS = WS / "westlake-harness-bms/benchmark/2026-10-03-u13-final-assembly"
PACKAGE = WS / "westlake-harness-bms/benchmark/2026-10-03-u13-effective-rebind/.artifacts/bundle-v4"
BASE_SHA = "190afedd3ddb250752e67b83d19669b6a952eb04cd69db5edf0b06eafe119736"
OLD_SHA = "bd83d846bc6c3a47a1a8e6431051d874d0cdd30db0687b3338ddd0f3fc61141d"
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
        value = re.sub(r"/home/[^/\s'\"]+", "$LAB_HOME", value)
    return value


def save(name, value, compact=False):
    path = Path(name) if isinstance(name, Path) else HERE / name
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
