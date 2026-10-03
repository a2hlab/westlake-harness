from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = Path(os.environ.get("WORKSPACES", REPO.parent))
MASTER = WS / "westlake-harness"
LANE = WS / "westlake-harness-bms"
PRIOR = LANE / "benchmark/2026-10-03-u15-on-u14-base"
ASSEMBLY = LANE / "benchmark/2026-10-03-u15-final-assembly"
sys.path.insert(0, str(MASTER / "scripts/lab"))


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def portable(value):
    if isinstance(value, dict):
        return {portable(key): portable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [portable(item) for item in value]
    if isinstance(value, Path):
        value = str(value)
    if isinstance(value, str):
        for root, token in [(WS, "$WORKSPACES"), (Path.home(), "$HOME")]:
            value = token if value == str(root) else value.replace(str(root) + "/", token + "/")
    return value


def expand(value):
    return Path(str(value).replace("$WORKSPACES/", str(WS) + "/"))


def load(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path)
    if not path.is_absolute():
        path = HERE / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(portable(value), ensure_ascii=False, indent=2) + "\n")


def capture(name, argv):
    raw = HERE / ".artifacts/raw" / (name + ".txt")
    raw.parent.mkdir(parents=True, exist_ok=True)
    started = datetime.now().astimezone().isoformat()
    with raw.open("w") as stream:
        result = subprocess.run([str(item) for item in argv], stdout=stream, stderr=subprocess.STDOUT)
    evidence = HERE / "evidence" / (name + ".txt")
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(portable(raw.read_text(encoding="utf-8", errors="backslashreplace")))
    print(name + " exit=" + str(result.returncode), flush=True)
    return dict(command=portable(argv), exit_code=result.returncode, started_at=started, finished_at=datetime.now().astimezone().isoformat(),
        raw=portable(raw), raw_sha256=sha(raw), evidence=portable(evidence), evidence_sha256=sha(evidence))
