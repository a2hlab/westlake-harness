import hashlib
import json
import os
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WORKSPACES = Path(os.environ.get("WORKSPACES", REPO.parent)).resolve()
MASTER = WORKSPACES / "westlake-harness"
ACCEPTED = "benchmark/2026-10-02-n11h-host-owner"
ARTIFACTS = WORKSPACES / "westlake-harness-bms" / ACCEPTED / ".artifacts/frozen-r1"
HOST_SHA = "65ac50894de8d06e32439d2aee91f61eb1c45d6c0822826d529f671ca3c49aed"
BASE_SHA = "65cc3535ebf22bdf664b3c8ddf932ccd7f42d936be1c861e1221a80b12a00284"
MANIFEST_SHA = "37c48e2b07e5e757bc872f174f883d44cc0f369a19b035afe9035b2a115286bf"
INPUTS_SHA = "a825ba2387793c9904a18a8b6ee95d4f695f968511d1fb31921d63255b333fc3"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def file(name):
    for root in [REPO, MASTER]:
        path = root / name
        if path.is_file():
            return path
    raise ValueError("missing existing evidence: " + name)


def load(name):
    return json.loads(file(name).read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def reference(name, needle):
    path = file(name)
    lines = path.read_text().splitlines()
    matched = [(number, text) for number, text in enumerate(lines, 1) if needle in text]
    if not matched:
        raise ValueError("missing source witness: " + name + ": " + needle)
    number, text = matched[0]
    return dict(path=name, line=number, text=text.strip(), sha256=sha(path))


def candidate_report():
    report = load(ACCEPTED + "/evidence/native-candidate.txt")
    if report["package_manifest_sha256"] != MANIFEST_SHA or report["inputs_sha256"] != INPUTS_SHA:
        raise ValueError("accepted manifest/input drift")
    return report
