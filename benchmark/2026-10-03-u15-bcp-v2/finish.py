import collections
import json
from pathlib import Path

from prepare import BASES, HERE, PRIVATE, REPO, portable, save, sha
from validation import check_plan, check_slots


def main():
    plan = json.loads((HERE / "plan.json").read_text())
    images = json.loads((HERE / "expected-images.json").read_text())
    check_plan(plan, images)
    check_slots(json.loads((HERE / "native-slots.json").read_text()))
    for row in plan["bcp"]:
        source = PRIVATE / "jars9" / row["name"]
        if sha(source) != row["sha256"]:
            raise ValueError("Local candidate snapshot drift")
    root = plan["machine"]["remote_root"]
    argv = [plan["frozen_tools"]["dex2oat64"]["path"], "--android-root=/system", "--instruction-set=arm64",
        "--base=0x70000000", "--compiler-filter=speed", "--runtime-arg", "-Xms64m", "--runtime-arg", "-Xmx512m",
        "--runtime-arg", "-Xverify:none", "--image=" + root + "/work/products/arm64/boot.art",
        "--oat-file=" + root + "/work/products/arm64/boot.oat"]
    for row in plan["bcp"]:
        argv.extend(["--dex-file=" + root + "/work/incoming/" + row["name"], "--dex-location=" + row["target"]])
    save("planned-argv.json", dict(status="PLANNED_NOT_EXECUTED", run1=argv, run2=argv, actual_argv_sha256=None))
    inventory = [dict(path=str(path.relative_to(PRIVATE)), sha256=sha(path), bytes=path.stat().st_size)
        for path in sorted(PRIVATE.rglob("*")) if path.is_file()]
    save("input-inventory.json", dict(root=PRIVATE, files=inventory, bcp_count=9,
        scope="nine candidate BCP JARs, unchanged non-BCP runtime JAR and separate M3 donor; no boot images"))
    save("transaction-base.template.json", dict(status="UNBOUND_NO_PROMOTION_CLAIM", execution_enabled=False,
        profiles={name: dict(content_base_sha256=digest, transaction_base=dict(path=None, sha256=None, signed_identity=None, expected=None),
            installer_identity=plan["content_bases"][name]["installers"]) for name, digest in BASES.items()}))
    checks = json.loads((HERE / "static-input-checks.json").read_text())
    save("results.json", dict(schema="u15-dual-bcp-preparation/v2", execution_enabled=False, rollout_ready=False,
        bake_executed=False, vm_access=False, board_access=False, active_registry_updated=False,
        promotion_confirmed=False, final_bundle_sha256=None, actual_changed_image_count=None,
        input_count=9, changed_bcp=plan["changed_bcp"], unchanged_bcp_count=7, expected_images=27,
        forecast=dict(collections.Counter(row["prediction"].split(":", 1)[0] for row in images)),
        paired_receipt="NOT_RUN; actual argv/log/toolchain/status/output identities unknown",
        frozen_exception="No U14/T7d approval transfers to these two new BCP inputs",
        raw_input_checks=checks, native_slot_status="partial referenced; Flutter9b824 arrived, composition is a separate task",
        observed_first_fatal_moves=0, conditional_targets=dict(bitmap=2, nsd=1),
        plan_sha256=sha(HERE / "plan.json"), inventory_sha256=sha(HERE / "input-inventory.json")))
    save("documentation.json", dict(
        layout_row="| **`benchmark/2026-10-03-u15-bcp-v2/`** | **Pinned Bitmap+NSD nine-input snapshot, guarded hw248 two-run full 27-image recipe and fresh paired receipt; no execution or historical exception reuse.** |",
        digest_append="- U15双BCP(2026-10-03,cx-bms):framework9e55+stubs94a9必须同一次FZ005全27烤，旧单件计划保留历史；新9输入/工具/tee/argv/rc逐项配对，U14/T7d异常不自动迁移。NSD只是类型链接桩，getSystemService仍null；immich下一堵ATrace另由Flutter9b824覆盖，不把静态可解析当亮。见benchmark/2026-10-03-u15-bcp-v2/。"))
    paths = sorted(str(path.relative_to(REPO)) for path in HERE.rglob("*") if path.is_file()
        and ".artifacts" not in path.parts and "__pycache__" not in path.parts
        and path.name not in ["landing-paths.txt", "listing-receipt.json"])
    paths.extend(str(path.relative_to(REPO)) for path in sorted((REPO / "specs/u15-bcp-v2").glob("*.spec.md")))
    paths.extend(["tools/spec-checks/tests/u15_bcp_v2.rs", str((HERE / "listing-receipt.json").relative_to(REPO))])
    paths = sorted(set(paths))
    (HERE / "landing-paths.txt").write_text("\n".join(paths) + "\n")
    save("listing-receipt.json", dict(paths=len(paths), listing_sha256=sha(HERE / "landing-paths.txt"),
        binaries=False, default_disabled=True, preflight_required=True))
    print("U15 BCP V2: paths=" + str(len(paths)) + " listing=" + sha(HERE / "landing-paths.txt") + "; 9 inputs, 2 swaps, 27 unbaked outputs")


if __name__ == "__main__":
    main()
