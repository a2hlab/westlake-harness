import json
from pathlib import Path

from prepare import HERE, REPO, PRIVATE, save, sha
from validation import check_plan

LAYOUT = "| **`benchmark/2026-10-03-u16-assembly-draft/`** | **Disabled U16 ledger: pinned U15 profiles, WifiManager stubs and ON_START runtime JAR, nine-input FZ-005 27-image rebake plan, fresh paired-receipt template and explicit pending native slots.** |"
DIGEST = "- U16备料(2026-10-03,cx-bms):内容底U15 29c8/8a26不是晋级事务BASE；stubs8593仅换9件BCP中的1件仍须全27镜像新配对，runtime JARf6f5不进BCP。t1历史merge收据仍钉c53而非确定性8593，留为历史证据不冒认当前构建回执；8个新增类待批，M1/Impeller待件、t2不进首批、t5等A0。见benchmark/2026-10-03-u16-assembly-draft/。"


def main():
    plan = json.loads((HERE / "plan.json").read_text())
    images = json.loads((HERE / "expected-images.json").read_text())
    slots = json.loads((HERE / "native-slots.json").read_text())
    check_plan(plan, images, slots)
    for row in json.loads((HERE / "input-inventory.json").read_text())["files"]:
        if sha(PRIVATE / row["path"]) != row["sha256"]:
            raise ValueError("Private input snapshot drift")
    commands = json.loads((HERE / "validation-runs.json").read_text())["records"] if (HERE / "validation-runs.json").exists() else []
    if (HERE / "preflight.json").exists():
        commands += json.loads((HERE / "preflight.json").read_text())["records"]
    save("composition.json", dict(schema="u16-incomplete-composition/v1", execution_enabled=False, rollout_ready=False,
        content_bases=plan["content_bases"], transaction_base={"common": None, "61b": None},
        runtime_jar=plan["runtime_jar"], bcp=plan["bcp"], native=slots, boot_images=images,
        final_manifest_sha256=None, final_inputs_sha256=None, final_bundle_sha256=None,
        blockers=["M1 runtime and Flutter proc artifacts pending", "new27-image pair not baked", "eight stubs allow_add pending",
            "t1 current-artifact build receipt needs donor correction", "U15 per-board armed transaction BASE and promotion signoff pending"],
        finalization="Compose one native version and one runtime JAR version only after arrivals; atomically update payload, target aliases, inputs and reference bindings; do not publish mixed intermediate executables"))
    save("results.json", dict(execution_enabled=False, rollout_ready=False, board_access=False, vm_access=False, remote_access=False,
        bake_executed=False, native_rebuilt=False, active_registry_updated=False, promotion_confirmed=False,
        final_bundle_sha256=None, final_manifest_sha256=None, final_inputs_sha256=None, input_count=9,
        unchanged_bcp_count=8, changed_bcp=plan["changed_bcp"], images_planned=27, actual_changed_image_count=None,
        arrived={"stubs": plan["bcp"][6]["sha256"], "runtime_jar": plan["runtime_jar"]["sha256"]},
        pending_native=[row["id"] for row in slots["slots"]], excluded=slots["excluded"], dependency_blocked=slots["dependency_blocked"],
        donor_receipt=json.loads((HERE / "donor-receipt-status.json").read_text()),
        static_input_checks=json.loads((HERE / "static-input-checks.json").read_text()),
        native_gates="NOT_RUN: no new native candidate", production_gates="NOT_RUN: incomplete disabled composition",
        commands=commands, observed_first_fatal_moves=0, conditional_targets={"fd-wifianalyzer": "WifiManager member-gap only; no Wi-Fi functionality", "fd-breezyweather": "launch ON_START ordering only; not a lit claim"}))
    save("documentation.json", {"README.md": [LAYOUT], ".octos/KNOWLEDGE-DIGEST.md": [DIGEST]})
    paths = [str(path.relative_to(REPO)) for path in HERE.rglob("*") if path.is_file() and ".artifacts" not in path.parts
        and "__pycache__" not in path.parts and path.name not in ["landing-paths.txt", "listing-receipt.json"]]
    paths += [str(path.relative_to(REPO)) for path in (REPO / "specs/u16-assembly-draft").glob("*.spec.md")]
    paths += ["tools/spec-checks/tests/u16_assembly_draft.rs", str((HERE / "listing-receipt.json").relative_to(REPO))]
    paths = sorted(set(paths))
    (HERE / "landing-paths.txt").write_text("\n".join(paths) + "\n")
    save("listing-receipt.json", dict(paths=len(paths), sha256=sha(HERE / "landing-paths.txt"), execution_enabled=False, rollout_ready=False))
    print("U16 disabled draft: " + str(len(paths)) + " paths; landing_sha256=" + sha(HERE / "landing-paths.txt"))


if __name__ == "__main__":
    main()
