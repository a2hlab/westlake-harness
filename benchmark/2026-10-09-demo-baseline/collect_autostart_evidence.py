import collections
import hashlib
import json
import os
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
WORKSPACES = Path(os.environ.get("WORKSPACES", HERE.parents[2]))
MASTER = WORKSPACES / "westlake-harness"
ORCA = WORKSPACES.parent
DONOR = ORCA / "00.Workspace-games-ad1ab0a7"


def portable(path):
    value = str(path)
    for root, token in ((WORKSPACES, "$WORKSPACES"), (ORCA, "$ORCA")):
        if value.startswith(str(root) + "/"):
            return token + value[len(str(root)):]
    return value


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect():
    sys.path.insert(0, str(MASTER / "scripts/lab"))
    import u7_executor
    journal = WORKSPACES / "westlake-harness-u7-executor/benchmark/2026-10-03-u14-stage-a-plan/window2/u14-A2-20261003T131427/61b/transaction/transaction/journal.json"
    state = json.loads(journal.read_text())
    rows, sources = u7_executor.baseline_replay_plan(state)
    assert len(rows) == 56 and len(state["plan"]["baseline"]) == 319
    layers = []
    for index, row in enumerate(rows, 1):
        target = row["target"]
        members = {path: sha for path, sha in state["plan"]["baseline"].items() if path == target or path.startswith(target + "/")}
        group = "zigzag-private" if target.startswith("/data/app/") else "shared"
        layers.append({"sequence": index, **row, "group": group,
                       "kind": "directory" if any(path != target for path in members) else "file",
                       "covered_expected_members": len(members), "direct_file_sha256": members.get(target),
                       "previous_stack": state["before_mounts"][target],
                       "source_pointer": "/before_mounts/" + target.replace("~", "~0").replace("/", "~1")})
    paths = [journal, MASTER / "scripts/lab/u7_executor.py", MASTER / "scripts/lab/deploy_generation.py",
             MASTER / "benchmark/2026-10-08-61b-newboot-recovery/continuation/results.json",
             MASTER / "benchmark/2026-10-08-61b-newboot-recovery/fingerprint-scope-diff.json",
             MASTER / "benchmark/2026-10-08-u7-replay-placeholder-cleanup/README.md",
             MASTER / "benchmark/2026-09-28-persistent-demo/autostart/README.md",
             MASTER / "bms/src/adapter/framework/appspawn-x/config/appspawn_x.cfg"]
    paths += [DONOR / "src/tools/devices" / name for name in
              ("install-boat-attack-autostart.sh", "boat-attack-autostart-device.sh", "boat-attack-autostart.cfg",
               "pr03-runtime-recover-device.sh", "pr03-runtime-recovery.cfg")]
    summary = {"mounts": len(layers), "groups": dict(collections.Counter(row["group"] for row in layers)),
               "kinds": dict(collections.Counter(row["kind"] for row in layers)), "baseline_targets": 319,
               "source_members": len(sources), "data_source_members": sum(path.startswith("/data/") for path in sources),
               "unmounted_system_members": sum(path.startswith("/system/") for path in sources)}
    return {"schema": "demo-autostart-static-evidence/v1", "execution_enabled": False, "board_access": False,
            "serial": state["serial"], "journal_status": state["status"], "journal_sha256": digest(journal),
            "summary": summary, "layers": layers, "source_hashes": sources,
            "expected": state["plan"]["baseline"], "candidate_additions_to_clean": state["plan"]["additions"],
            "host_sha256": state["plan"]["baseline"][u7_executor.HOST],
            "reference_paths": state["plan"]["reference_paths"],
            "sources": [{"path": portable(path), "sha256": digest(path)} for path in paths],
            "limitations": ["source/config inspection and previous recovery evidence only; no new boot test",
                            "source appspawn_x.cfg is not present in the 319-path identity; live deployed config still requires readback",
                            "56 rows belong to signed 61b U13; not an automatic common-board or final demo-overlay plan"]}


if __name__ == "__main__":
    result = collect()
    output = HERE / "autostart-evidence.json"
    output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"sha256": digest(output), **result["summary"]}, sort_keys=True))
