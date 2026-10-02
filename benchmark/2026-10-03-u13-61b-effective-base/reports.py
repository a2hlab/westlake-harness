import json
import platform
import sys

from common import BASE, HERE, INSTALLS, MASTER, ORIGINAL_BASE, ORIGINAL_PACKAGE, ORIGINAL_PACKAGE_SHA, PACKAGE, SOURCE, TARGETS, capture, save, sha
from validation import require_board_local_identity
import generation_bundle as bundle
import generation_static_checks as static
import u7_executor as executor


def main():
    if platform.system() != "Darwin":
        raise ValueError("Mac-only during current window")
    composition = json.loads((HERE / "composition.json").read_text())
    records = [capture("whois", [sys.executable, MASTER / "scripts/lab/deployed_whois.py", "libinstalls.z.so"]),
        capture("source-dynamic", ["llvm-readelf", "-d", "--wide", SOURCE])]
    data = json.loads((PACKAGE / "bundle.json").read_text())
    policy = json.loads(bundle.member(PACKAGE, data["static_checks"]["policy"]).read_text())
    old_static = static.check(ORIGINAL_PACKAGE, ORIGINAL_BASE, policy)
    new_static = static.check(PACKAGE, BASE, policy)
    save("evidence/static-original.json", old_static, compact=True)
    save("evidence/static-61b.json", new_static, compact=True)
    old_members = json.dumps(old_static["members"], sort_keys=True).replace(str(ORIGINAL_PACKAGE) + "/", "$CANDIDATE/").replace(str(ORIGINAL_BASE) + "/", "$BASE/")
    new_members = json.dumps(new_static["members"], sort_keys=True).replace(str(PACKAGE) + "/", "$CANDIDATE/").replace(str(BASE) + "/", "$BASE/")
    if old_static["status"] != "PASS" or new_static["status"] != "PASS" or old_members != new_members:
        raise ValueError("New static finding or changed artifact comparison")
    native = {}
    for label, root in [("base", BASE / "native"), ("candidate", PACKAGE / "native")]:
        records.append(capture("native-" + label, [sys.executable, MASTER / "scripts/lab/native_predeploy.py", "--package", root,
            "--inputs", root / "native-checks/native-gates.json", "--readelf", "llvm-readelf"]))
        report = json.loads((HERE / ".artifacts/raw" / ("native-" + label + ".txt")).read_text())
        save("evidence/native-" + label + ".json", report, compact=True)
        if report["status"] != "PASS" or report["errors"]:
            raise ValueError("Active native gate refused unchanged identity")
        native[label] = {name: dict(excepted=gate["excepted"], rejected=gate["rejected"]) for name, gate in report["gates"].items()}
    plan = executor.prepare(PACKAGE, BASE / "native")
    require_board_local_identity(plan["baseline"], plan["expected"], TARGETS, INSTALLS, {row["target"] for row in plan["changes"]})
    changed_files = []
    for label, old, replacement in [("base", ORIGINAL_BASE, BASE), ("candidate", ORIGINAL_PACKAGE, PACKAGE)]:
        names = {path.relative_to(old).as_posix() for path in old.rglob("*") if path.is_file()} | {path.relative_to(replacement).as_posix() for path in replacement.rglob("*") if path.is_file()}
        changed = []
        for name in sorted(names):
            before = sha(old / name) if (old / name).is_file() else None
            after = sha(replacement / name) if (replacement / name).is_file() else None
            if before != after:
                changed.append(dict(path=name, old_sha256=before, new_sha256=after))
        expected = {"bundle.json", "reference/runtime.txt"} if label == "candidate" else {"bundle.json", "reference/runtime.txt", *["native/board-local" + target for target in TARGETS]}
        if {row["path"] for row in changed} != expected:
            raise ValueError("Unexpected non-metadata file change: " + label + str(changed))
        changed_files.append(dict(variant=label, rows=changed))
    if sha(ORIGINAL_PACKAGE / "bundle.json") != ORIGINAL_PACKAGE_SHA:
        raise ValueError("Authorized original changed")
    save("file-delta.json", dict(variants=changed_files, output_bytes_changed=False, service_deployed=False))
    save("report-summary.json", dict(status="OFFLINE_STATIC_PASS_PENDING_OUTER_PRODUCTION", actual_os=platform.system(), architecture=platform.machine(),
        base_bundle_sha256=composition["base_bundle_sha256"], bundle_sha256=composition["bundle_sha256"], records=records,
        static_status=new_static["status"], static_members_identical=True, native=native,
        unchanged_service_paths=TARGETS, service_action_count=0, expected_full_identity=True,
        vm_replay="outer pending", production_run=False, execution_enabled=False, device_access=False))
    print("STATIC old190/new61b PASS; member comparisons byte-for-byte same, no new finding")
    print("NATIVE base/candidate active PASS; unchanged manifest/inputs; no registry delta")
    print("FULL_IDENTITY exact signed61b 316/319; two libinstalls51e aliases no actions; original912 unchanged")
    print("VM/production PENDING outer; no orb/device access; metadata needs separate authorization")


if __name__ == "__main__":
    main()
