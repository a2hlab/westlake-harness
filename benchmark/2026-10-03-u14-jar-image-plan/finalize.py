import hashlib
import json
from pathlib import Path

from prepare_inputs import BASE, BASE_SHA, HERE, PRIVATE, REPO, WS, generation_bundle, portable, save, sha
from validation import check_plan, check_slots


LAYOUT = "| **`benchmark/2026-10-03-u14-jar-image-plan/`** | **Disabled hw248 FZ-005 rebake plan, nine effective BCP snapshots, 27 unknown-output image rows, paired receipt checks and arrived native input slots.** |"
DIGEST = "- U14镜像备料(2026-10-03,cx-bms):0349 runtime非BCP，87cf stubs换有效9件中的1件须FZ005全27重烤；3预计变/16可能变/8预计同不是实际变数，U12的11变不能借。hw248历史ae865/14b1可沿用但本仓t5=0525非冻结驱动，执行前核远端工具/依赖及完整tee状态；新输入不能自动套T7d backtrace例外。341c/fff9/7605/9b36+4886到持久件才填输入槽(非8688旧Gecko)，旧90de包不改；见benchmark/2026-10-03-u14-jar-image-plan/。"


def main():
    plan = json.loads((HERE / "plan.json").read_text())
    images = json.loads((HERE / "expected-images.json").read_text())
    slots = json.loads((HERE / "native-slot-inputs.json").read_text())
    check_plan(plan, images)
    check_slots(slots)
    originals = [BASE, WS / "westlake-harness-bms/benchmark/2026-10-03-u14-native-assembly/.artifacts/u14-bridge-only-t8"]
    expected = [BASE_SHA, slots["historical_bridge_only_bundle"]]
    preservation = []
    for root, digest in zip(originals, expected):
        if sha(root / "bundle.json") != digest:
            raise ValueError("Historical bundle metadata changed")
        generation_bundle.validate(root)
        preservation.append(dict(root=root, bundle_sha256=digest, inventory_validation="PASS; every declared native payload and boot/runtime member SHA checked"))
    save("preservation.json", preservation)
    inventory = [dict(path=str(path.relative_to(PRIVATE)), sha256=sha(path), bytes=path.stat().st_size)
        for path in sorted(PRIVATE.rglob("*")) if path.is_file()]
    identity = hashlib.sha256(json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    save("input-snapshot-receipt.json", dict(root=PRIVATE, files=inventory, inventory_sha256=identity,
        includes="9 candidate BCP, 1 non-BCP runtime, 27 old reference images, 5 arrived native files; no new baked images"))
    raw_outputs = []
    for path in sorted((HERE / "evidence").glob("*")):
        if path.suffix not in [".json", ".txt"]:
            continue
        raw = HERE / ".artifacts/raw" / ("final-" + path.name)
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(path.read_bytes())
        path.write_text(portable(raw.read_text()))
        raw_outputs.append(dict(raw=raw, raw_sha256=sha(raw), evidence=str(path.relative_to(HERE)), evidence_sha256=sha(path)))
    save("evidence-output-receipt.json", raw_outputs)
    summary = dict(schema="westlake-u14-plan-results/v1", status="PREPARATION_COMPLETE_EXECUTION_DISABLED",
        execution_enabled=False, bake_executed=False, a2hlab_access=False, board_access=False,
        content_base_sha256=BASE_SHA, transaction_base="future explicit signed per-board parameter",
        plan_sha256=sha(HERE / "plan.json"), input_snapshot_inventory_sha256=identity,
        input_snapshots=len(inventory), bcp_jars=9, bcp_changed=1, runtime_is_bcp=False,
        rebake_images=27, image_change_forecast=dict(expected_change=3, may_change=16, expected_same=8, actual_changed=None),
        machine="hw248 after fresh frozen-tool/dependency check and outer approval; not executed",
        final_bundle_sha256=None, final_native_manifest_sha256=None,
        staged_native_host=slots["slots"][0]["sha256"], pending_native=[row["id"] for row in slots["slots"] if row["state"] == "pending"],
        host_open_sites=dict(u13=8, u14=8, namespace_edges_u13=17, namespace_edges_u14=17, inherit_repeat=0,
            inherit_after_open_may_paths_u13=4, inherit_after_open_may_paths_u14=4),
        raw_checks=dict(host_strings_exit=1, host_strings_dropped=2, host_strings_added=4,
            runtime_class_exit=1, runtime_class_dropped=0, runtime_class_reshaped=0, runtime_class_added=3,
            stubs_class_exit=1, stubs_class_dropped=0, stubs_class_reshaped=0, stubs_class_added=2,
            frozen_class_violations=0, final_native_static_gates="PENDING final composition"),
        tests=dict(python_plan=12, python_slots=6, rust_selectors=2, cold_tests="see evidence/cold-tests.txt",
            spec_lifecycle="two PASS computational contracts; not production evidence"),
        paired_receipt="template NOT_RUN; outputs and actual log identities null",
        production="NOT_RUN; future outer-owned Mac/VM after window; no authorization inferred")
    save("results.json", summary)
    save("documentation.json", dict(layout_row=LAYOUT, digest_append=DIGEST,
        note="Apply snippets only; root documents contain unrelated lane history and are not in landing list"))
    paths = sorted(str(path.relative_to(REPO)) for path in HERE.rglob("*") if path.is_file()
        and ".artifacts" not in path.parts and "__pycache__" not in path.parts
        and path.name not in ["landing-paths.txt", "listing-receipt.json"])
    paths.extend(str(path.relative_to(REPO)) for path in sorted((REPO / "specs/u14-jar-image-plan").glob("*.spec.md")))
    paths.append("tools/spec-checks/tests/u14_jar_image_plan.rs")
    paths.append(str((HERE / "listing-receipt.json").relative_to(REPO)))
    listing = HERE / "landing-paths.txt"
    listing.write_text("\n".join(sorted(paths)) + "\n")
    save("listing-receipt.json", dict(path=listing, paths=len(paths), listing_sha256=sha(listing)))
    print("PREPARATION COMPLETE; no bake, VM, board, production or registry mutation")
    print("input_snapshot_inventory=" + identity + "; files=" + str(len(inventory)))
    print("landing paths=" + str(len(paths)) + "; sha256=" + sha(listing))


if __name__ == "__main__":
    main()
