import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WORKSPACES = Path(os.environ.get("WORKSPACES", REPO.parent))
MASTER = WORKSPACES / "westlake-harness"
LANE = WORKSPACES / "westlake-harness-bms"
sys.path.insert(0, str(MASTER / "scripts/lab"))

BASE = WORKSPACES / "westlake-inputs/generations/u12-final-j0482c9b1-s615b8bbe-icu-media-zlib-v2/bundle"
BASE_BUNDLE = "bf6c0fb67d76f1f1d54725738b78f58d24483ceeac66087e2e801d74d1b650ee"
BASE_MANIFEST = "2a3fac8153e080f509cd0949bc521e5e9d81ec37937c312689fb1fec2b1494df"
RUNTIME = "18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae"
COMPAT = "b2be657ca2c171dd786068e77be90d82ec3a50407df37b1ccbafef94a8db88a6"
POLICY = "b8be63d2f617ba202373e4a60b34cc4eadba84bcfe31e42b64cfe4f01bfa62f7"
HOST = "2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e"
PACKAGE = HERE / ".artifacts/bundle"


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
        for root, token in [(REPO, "$REPO"), (WORKSPACES, "$WORKSPACES"), (Path.home(), "$HOME")]:
            value = token if value == str(root) else value.replace(str(root) + "/", token + "/")
        value = re.sub(r"\$REPO/(benchmark/[^/]+/\.artifacts)(?=/|[\s'\"]|$)", r"$WORKSPACES/westlake-harness-bms/\1", value)
        if "Control socket connect(" in value or "ssh: connect to host" in value:
            value = re.sub(r"Control socket connect\([^)]*\)", "Control socket connect($SSH_CONTROL_SOCKET)", value)
            value = re.sub(r"ssh: connect to host \S+", "ssh: connect to host $LAB_HOST", value)
    return value


def save(path, data):
    path = HERE / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(portable(data), indent=2) + "\n")


def capture(name, command, timeout=600):
    command = [str(item) for item in command]
    raw = HERE / ".artifacts/raw" / (name + ".txt")
    raw.parent.mkdir(parents=True, exist_ok=True)
    try:
        process = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        output = process.stdout + process.stderr
        code = process.returncode
    except subprocess.TimeoutExpired as error:
        def decode(value):
            return value.decode(errors="replace") if isinstance(value, bytes) else value or ""
        output = decode(error.stdout) + decode(error.stderr) + f"\nTIMEOUT after {timeout}s\n"
        code = 124
    raw.write_text(output)
    evidence = HERE / "evidence" / (name + ".txt")
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(portable(output))
    return dict(command=portable(command), exit_code=code, raw=portable(raw), raw_sha256=sha(raw), evidence=portable(evidence))


def assert_disabled(data, manifest):
    if data.get("rollout_ready") is not False or manifest.get("rollout_ready") is not False:
        raise ValueError("draft must remain disabled")
    if "window_authorization" in data or "window_authorization" in manifest:
        raise ValueError("draft must not carry window authorization")
    if manifest["files"]["payload/runtime/appspawn-x"] != HOST:
        raise ValueError("McDonald host candidate is held; U12 host must remain")
    for name, expected in [("libbionic_compat.so", COMPAT), ("libnativeloader.so", POLICY)]:
        values = [manifest["files"]["payload/" + directory + "/" + name] for directory in ["android/lib64", "route"]]
        if values != [expected, expected]:
            raise ValueError("root and route alias must change together: " + name)
