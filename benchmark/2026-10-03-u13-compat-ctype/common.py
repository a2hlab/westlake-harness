import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = Path(os.environ.get("WORKSPACES", REPO.parent))
MASTER = WS / "westlake-harness"
OLD = "b2be657ca2c171dd786068e77be90d82ec3a50407df37b1ccbafef94a8db88a6"
DEPLOYED = "015aa3a632eabe057bd8d6ce0e0ff181209da7dcab8de22409a79addc0a56d58"
PRIOR = REPO / "benchmark/2026-10-02-u12-vlc-bionic-residue"
SDK = Path("/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def portable(value):
    if isinstance(value, dict):
        return {name: portable(item) for name, item in value.items()}
    if isinstance(value, list):
        return [portable(item) for item in value]
    text = str(value) if isinstance(value, Path) else value
    if isinstance(text, str):
        text = re.sub(re.escape(str(REPO)) + r"/(benchmark/[^/]+/\.artifacts)(?=/|[\s'\"]|$)", r"$WORKSPACES/westlake-harness-bms/\1", text)
        for root, token in [(SDK, "$OHOS_SDK"), (REPO, "$REPO"), (WS, "$WORKSPACES"), (Path.home(), "$HOME")]:
            text = token if text == str(root) else text.replace(str(root) + "/", token + "/")
    return text


def expand(value):
    for token, root in [("$REPO", REPO), ("$WORKSPACES", WS), ("$OHOS_SDK", SDK), ("$HOME", Path.home())]:
        value = value.replace(token, str(root))
    return value


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(portable(value), indent=2) + "\n")


def capture(name, command, allowed=(0,)):
    process = subprocess.run([str(item) for item in command], text=True, capture_output=True, errors="replace")
    raw = HERE / ".artifacts/raw" / (name + ".txt")
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(process.stdout + process.stderr)
    evidence = HERE / "evidence" / (name + ".txt")
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(portable(raw.read_text()))
    print(name + " exit=" + str(process.returncode), flush=True)
    if process.returncode not in allowed:
        raise ValueError(name + " failed: " + process.stderr[:1000])
    return dict(command=command, exit_code=process.returncode, raw=raw, raw_sha256=sha(raw), evidence=evidence)
