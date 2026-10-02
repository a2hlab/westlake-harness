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
PACKAGE = HERE / ".artifacts/bundle-v3"
PREVIOUS = REPO / "benchmark/2026-10-03-u13-compat-ctype"
BASE = WS / "westlake-inputs/generations/u12-final-j0482c9b1-s615b8bbe-icu-media-zlib-v2/bundle"
JAR = "bbc3f530190fe98e2979dc4059379f8a0259d1f6ab243830347ca875cdb62f9b"
HOST = "2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e"
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
        value = re.sub(r"Control socket connect\([^)]*\)", "Control socket connect($SSH_CONTROL_SOCKET)", value)
        value = re.sub(r"ssh: connect to host \S+", "ssh: connect to host $LAB_HOST", value)
    return value


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(portable(value), indent=2) + "\n")


def capture(name, command, timeout=600):
    command = [str(item) for item in command]
    raw = HERE / ".artifacts/raw" / (name + ".txt")
    raw.parent.mkdir(parents=True, exist_ok=True)
    try:
        process = subprocess.run(command, text=True, capture_output=True, errors="replace", timeout=timeout)
        output, code = process.stdout + process.stderr, process.returncode
    except subprocess.TimeoutExpired as error:
        def decode(value):
            return value.decode(errors="replace") if isinstance(value, bytes) else value or ""
        output = decode(error.stdout) + decode(error.stderr) + f"\nTIMEOUT after {timeout}s\n"
        code = 124
    except OSError as error:
        output = str(error) + "\n"
        code = 127
    raw.write_text(output)
    evidence = HERE / "evidence" / (name + ".txt")
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(portable(output))
    print(name + " exit=" + str(code), flush=True)
    return dict(command=portable(command), exit_code=code, raw=portable(raw), raw_sha256=sha(raw), evidence=portable(evidence))
