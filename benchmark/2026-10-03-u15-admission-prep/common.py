import hashlib
import json
import os
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = Path(os.environ.get("WORKSPACES", REPO.parent))
MASTER = WS / "westlake-harness"
NATIVE = REPO / "benchmark/2026-10-03-u15-native-v2"
BCP = REPO / "benchmark/2026-10-03-u15-bcp-v2"
sys.path.insert(0, str(MASTER / "scripts/lab"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def load(name):
    return json.loads((HERE / name).read_text())
