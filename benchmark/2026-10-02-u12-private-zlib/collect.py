import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = Path(os.environ.get("WORKSPACES", REPO.parent))
MASTER = WS / "westlake-harness"
BASE = WS / "westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle/native"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def portable(value):
    text = str(value)
    for root, variable in [(REPO, "$REPO"), (WS, "$WORKSPACES"), (Path.home(), "$HOME")]:
        if text == str(root):
            return variable
        text = text.replace(str(root) + "/", variable + "/")
    return text


def save(name, value):
    (HERE / name).write_text(portable(json.dumps(value, indent=2, ensure_ascii=False)) + "\n")


def run(name, command, allowed=(0,)):
    result = subprocess.run([str(value) for value in command], capture_output=True, text=True)
    text = result.stdout + result.stderr
    raw = HERE / ".artifacts" / (name + ".txt")
    raw.write_text(text)
    (HERE / "evidence" / raw.name).write_text(portable(text))
    if result.returncode not in allowed:
        raise RuntimeError(name + ": " + text)
    return dict(command=[portable(value) for value in command], exit_code=result.returncode, raw_sha256=sha(raw))
