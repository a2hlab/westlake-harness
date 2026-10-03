import json
import subprocess
import sys

from prepare import HERE, MASTER, portable, save, sha


def main():
    plan = json.loads((HERE / "plan.json").read_text())
    records = []
    for label, row in [("stubs", plan["bcp"][6]), ("runtime-jar", plan["runtime_jar"])]:
        candidate = row["snapshot"].replace("$WORKSPACES/", str(MASTER.parent) + "/")
        deployed = row["u15_source"].replace("$WORKSPACES/", str(MASTER.parent) + "/")
        args = [sys.executable, str(MASTER / "scripts/lab/deployed_class_diff.py"), candidate, "--deployed", deployed, "--frozen"]
        raw = HERE / ".artifacts/raw" / (label + "-classes.txt")
        raw.parent.mkdir(parents=True, exist_ok=True)
        with raw.open("wb") as stream:
            result = subprocess.run(args, stdout=stream, stderr=subprocess.STDOUT)
        evidence = HERE / "evidence" / raw.name
        evidence.parent.mkdir(exist_ok=True)
        evidence.write_text(portable(raw.read_text(encoding="utf-8", errors="backslashreplace")))
        records.append(dict(label=label, argv=args, exit_code=result.returncode, raw=raw, raw_sha256=sha(raw),
            evidence=str(evidence.relative_to(HERE)), evidence_sha256=sha(evidence), allow_add_applied=False,
            approval_status="eight exact adds pending outer review" if label == "stubs" else "no class drop/add/reshape expected"))
        print(label + " frozen class diff exit=" + str(result.returncode) + " (no allow_add applied)")
    save("static-input-checks.json", dict(results=records, production_pass=False, approvals_applied=False, board_access=False, vm_access=False))


if __name__ == "__main__":
    main()
