#!/usr/bin/env python3
"""Read local T30 restoration receipts; never execute device commands or sign close."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=Path, required=True)
    ap.add_argument("--restored-snapshot", default="restored-snapshot")
    ap.add_argument("--restored-supplement", default="restored-supplement")
    a = ap.parse_args()
    w = a.window
    refs = []

    def raw(rel):
        b = (w / rel).read_bytes()
        refs.append({"path": rel, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()})
        return b

    def obj(rel):
        return json.loads(raw(rel))

    before = obj("before-snapshot/snapshot.json")
    after = obj(a.restored_snapshot + "/snapshot.json")
    checks = {}
    for label, x in [("before", before), ("after", after)]:
        checks[label + "_complete"] = (
            x["capture_status"] == "COMPLETE"
            and all(x[k] is True for k in ("complete", "collection_complete", "boot_stable"))
            and x["serial"] == "5cd1e3dd00000000000000000923012c"
            and x["plan_target_count"] == 518
        )
    checks["original_before_boot"] = before["boot_id"] == "345e3fa2-ac65-4baa-89e2-370d73d73bb9"
    checks["different_restored_boot"] = after["boot_id"] != before["boot_id"]
    fields = ["sha", "labels", "params", "init_configs", "bind_targets",
              "config_policy_layer_roots", "selinux_enforce", "plan_sha256"]
    checks["snapshot_fields"] = {k: before[k] == after[k] for k in fields}
    checks["collection_sha_equal"] = before["collection_sha256"] == after["collection_sha256"]
    blobs = []
    for label, dirname, boot in [
        ("before", "before-supplement", before["boot_id"]),
        ("after", a.restored_supplement, after["boot_id"]),
    ]:
        r = obj(dirname + "/result.json")
        b = raw(dirname + "/stdout.raw")
        lines = b.splitlines(keepends=True)
        bootline = b"T16_SUPPLEMENT_BOOT " + boot.encode() + b"\n"
        checks[label + "_supplement_complete"] = (
            r["status"] == "SUPPLEMENT_BYTES_COMPLETE" and r["rc"] == 0
            and r["targets"] == 26 and r["boot"] == boot
            and lines.count(bootline) == 1 and lines[0] == bootline
            and sum(x.startswith(b"T16_TARGET ") for x in lines) == 26
            and lines[-1].strip() == b"T16_SUPPLEMENT_COMPLETE"
        )
        blobs.append(b"".join(x for x in lines if x != bootline))
    checks["supplement_equal_except_boot"] = blobs[0] == blobs[1]
    passed = all(all(v.values()) if isinstance(v, dict) else v for v in checks.values())
    print(json.dumps({
        "status": "SNAPSHOT_AND_SUPPLEMENT_EQUAL" if passed else "REFUSED",
        "checks": checks, "source_refs": refs,
        "not_checked": ["six physical/private states", "power", "debug parameter",
                        "actual UI", "lock release", "video or sound verdict"],
        "device_calls": 0, "close_written": False,
    }, indent=2))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
