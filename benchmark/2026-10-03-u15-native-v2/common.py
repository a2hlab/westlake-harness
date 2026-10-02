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
BASE = WS / "westlake-harness-bms/benchmark/2026-10-03-u14-effective-rebind/.artifacts/common-reviewed"
LOCAL = BASE.parent / "61b-reviewed"
PARTIAL = HERE / ".artifacts/native-only"
DONOR = MASTER / "benchmark/2026-10-03-u15-jitsi-native-domain"
RELEASE = WS / "westlake-inputs/generations"
sys.path.insert(0, str(MASTER / "scripts/lab"))


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def portable(value):
    if isinstance(value, dict):
        return {name: portable(item) for name, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [portable(item) for item in value]
    if isinstance(value, Path):
        value = str(value)
    if isinstance(value, str):
        for root, token in [(WS, "$WORKSPACES"), (Path.home(), "$HOME")]:
            value = token if value == str(root) else value.replace(str(root) + "/", token + "/")
        value = re.sub(r"/home/[^/\s'\"]+", "$LAB_HOME", value)
    return value


def save(name, data):
    path = Path(name)
    if not path.is_absolute():
        path = HERE / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(portable(data), ensure_ascii=False, separators=(",", ":")) + "\n")


def capture(name, argv):
    raw = HERE / ".artifacts/raw" / (name + ".txt")
    raw.parent.mkdir(parents=True, exist_ok=True)
    with raw.open("w") as handle:
        result = subprocess.run([str(item) for item in argv], stdout=handle, stderr=subprocess.STDOUT)
    destination = HERE / "evidence" / (name + ".txt")
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(portable(raw.read_text()))
    print(name + " exit=" + str(result.returncode), flush=True)
    return dict(command=portable(argv), exit_code=result.returncode, raw=portable(raw), raw_sha256=sha(raw),
        evidence=str(destination.relative_to(HERE)), evidence_sha256=sha(destination))
