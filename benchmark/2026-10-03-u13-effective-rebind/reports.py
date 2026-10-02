import json
import sys

from common import BASE, HERE, MASTER, PACKAGE, PREVIOUS, capture, save, sha
import generation_bundle as bundle_tool
import generation_static_checks as static


def main():
    records = []
    native = capture("native-active", [sys.executable, MASTER / "scripts/lab/native_predeploy.py", "--package", PACKAGE / "native", "--inputs", PACKAGE / "native/native-checks/native-gates.json"])
    records.append(native)
    native_report = json.loads((HERE / ".artifacts/raw/native-active.txt").read_text())
    save("evidence/native-active.json", native_report)
    report = static.check(PACKAGE, BASE, {})
    save("evidence/static-unapproved.json", report, compact=True)
    old = static.effective(BASE)
    new = static.effective(PACKAGE)
    changes = []
    for target, entry in new.items():
        prior = old.get(target)
        if prior and prior["sha256"] == entry["sha256"]:
            continue
        changes.append(dict(target=target, candidate_sha256=entry["sha256"], deployed_sha256=prior["sha256"] if prior else None))
        candidate = bundle_tool.member(PACKAGE, entry)
        if not prior or candidate.suffix in {".art", ".oat", ".vdex"}:
            continue
        deployed = bundle_tool.member(BASE, prior)
        index = len(changes)
        if candidate.suffix == ".jar":
            records.append(capture("classes-" + str(index), [sys.executable, MASTER / "scripts/lab/deployed_class_diff.py", candidate, "--deployed", deployed, "--frozen"]))
        elif candidate.read_bytes()[:4] == b"\x7fELF":
            records.append(capture("strings-" + str(index), [sys.executable, MASTER / "scripts/lab/deployed_strings_diff.py", candidate, "--deployed", deployed]))
    save("changed-members.json", dict(changes=changes, records=records, compared_to="actual effective U10.1T8", payload_rebuilt=False))
    for row in report["members"]:
        print(row["status"], row["target"], row.get("delta_sha256", ""))
    print("native=" + native_report["status"] + " static=" + report["status"] + " actual_changes=" + str(len(changes)))


if __name__ == "__main__":
    main()
