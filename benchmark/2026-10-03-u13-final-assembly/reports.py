import json

from common import BASE, HERE, MASTER, PACKAGE, PREVIOUS, capture, save, sha
import auto_approve_exceptions as auto
import generation_static_checks as static
from validation import compare_new


def main():
    registry = MASTER / "knowledge/gates/native-predeploy-exceptions.json"
    registry_sha = sha(registry)
    records = []
    reports = {}
    for name, root in [("u12", BASE / "native"), ("v3", PACKAGE / "native")]:
        records.append(capture("native-" + name, ["python3", MASTER / "scripts/lab/native_predeploy.py", "--package", root,
            "--inputs", root / "native-checks/native-gates.json", "--readelf", "llvm-readelf"]))
        report = json.loads((HERE / ".artifacts/raw" / ("native-" + name + ".txt")).read_text())
        if report["errors"]:
            raise ValueError(report["errors"])
        reports[name] = report
        save("evidence/native-" + name + ".json", report)
    report = static.check(PACKAGE, BASE, {})
    save("evidence/static-v3.json", report)
    records.append(capture("strings-v3", ["python3", MASTER / "scripts/lab/deployed_strings_diff.py",
        PACKAGE / "native/payload/android/lib64/libbionic_compat.so", "--deployed",
        BASE / "native/payload/android/lib64/libbionic_compat.so"]))
    strings = (HERE / "evidence/strings-v3.txt").read_text()
    previous_rows = json.loads((PREVIOUS / "strings-review.json").read_text())["rows"]
    import ast
    actual_rows = [(line.split()[0], ast.literal_eval(line[8:])) for line in strings.splitlines() if line.startswith(("ADDED", "DROPPED"))]
    expected_rows = [(row["operation"], row["value"]) for row in previous_rows]
    matched, new = auto.classify(reports["v3"], [reports["u12"]], json.loads(registry.read_text())["exceptions"])
    old_native = json.loads((PREVIOUS / "evidence/native-v2.json").read_text())
    mapping = compare_new(old_native, reports["v3"])
    compat = [item for item in report["members"] if item["target"].endswith("/libbionic_compat.so")]
    signed = json.loads((HERE / "evidence/outer-approval.json").read_text())
    approved_delta = "2cd13b3defeda8318d91d23d1ab8e63f77b0bb79e45bc5961f27fa67e864bd3d"
    delta_matches = len(compat) == 2 and all(item["delta_sha256"] == approved_delta for item in compat)
    summary = dict(records=records, native_status=reports["v3"]["status"], auto_identical=len(matched), new_findings=len(new),
        new_finding_mapping=mapping, exact_new_findings=all(row["equal"] for row in mapping),
        compat_aliases=[{key: item[key] for key in ["target", "candidate_sha256", "deployed_sha256", "delta_sha256", "open_site_delta"]} for item in compat],
        approved_delta_sha256=approved_delta, production_delta_matches_signed=delta_matches,
        strings_equal=actual_rows == expected_rows, strings_rows=actual_rows,
        static_status=report["status"], changed_jars=report["changed_jars"], changed_native_paths=report["changed_native_paths"],
        jar_checks=[item for item in report["members"] if item.get("kind") == "DEX-JAR"],
        signer=signed["signer"], execution_enabled=False, approvals_transferred=False,
        registry_unchanged=sha(registry) == registry_sha)
    save("transfer-check.json", summary)
    print(json.dumps({key: value for key, value in summary.items() if key not in {"records", "compat_aliases", "new_finding_mapping", "strings_rows"}}, indent=2))


if __name__ == "__main__":
    main()
