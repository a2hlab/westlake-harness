import json
from pathlib import Path

from prepare import HERE, REPO, PRIVATE, save, sha
from validation import check_plan

LAYOUT = "| **`benchmark/2026-10-03-u16-assembly-draft/`** | **Disabled U16 ledger: pinned U15 profiles, WifiManager stubs and ON_START runtime JAR, nine-input FZ-005 27-image rebake plan, fresh paired-receipt template and explicit pending native slots.** |"
DIGEST = "- U16双件补槽(2026-10-03,cx-bms):runtime94c3→1d42拆TU使ABI+1、callset3处差(不是0差)，open197/NEEDED/strings同；Flutter15e988误以U14fff9为底删U15三ATrace且abi_diff rc0不拒removed，外环作废后改9b82→b1c9实核0删/+eglGetProcAddress/calls0，双件219consumer各断0。Flutter开点7→11新增4均NOLOAD、strings0删8加未批；联合N1/N2活表仍拒103/105，202同+2个NOLOAD行移+4新NOLOAD待审，未换绑。t1收据8593/dex b3b24已实核，27镜像/武装BASE仍待。见benchmark/2026-10-03-u16-assembly-draft/。"
A3_DIGEST = "- U16 A3补槽(2026-10-03,cx-bms):Flutterb1c9→eb90仅westlake_flutter槽，ee2fb私有owner不动；全296字节核对、对U15 ABI0删/+1/calls0/219断0，4新增NOLOAD中libEGL在新布局已真解析(不能沿用旧unknown ADR)。increments只列两变体8已到件native/JAR，keys6f42用oc-t4已提交v3实际checker得0GAP，去掉Flutter观察源负例报2GAP；27镜像未烤不伪造SHA、不冒认全包覆盖。N1/N2与strings仍待审，未动活表/未上板。见benchmark/2026-10-03-u16-assembly-draft/。"
PACKET_DIGEST = "- U16待批包(2026-10-03,cx-bms):17行=Flutter4个NOW|NOLOAD+runtime2行移+3callset差+8真实ADDED(strings0删8加rc1)，逐行源与新鲜反汇编绑定。M1拆TU后dl_iterate/HiLog移进显式fn+session入口，不能冒称3函数逐指令同或callsets0；NOLOAD只查不建不等于owner可见、GL空实现正确或已亮。17项仅建议批、未签未入门，27镜像仍未烤。见benchmark/2026-10-03-u16-assembly-draft/outer-approval-packet.json。"


def main():
    plan = json.loads((HERE / "plan.json").read_text())
    images = json.loads((HERE / "expected-images.json").read_text())
    slots = json.loads((HERE / "native-slots.json").read_text())
    check_plan(plan, images, slots)
    native_binding = json.loads((HERE / "native-pair-binding.json").read_text())
    native_reports = json.loads((HERE / "native-pair-gates.json").read_text())
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
        native_partial=native_binding,
        blockers=["new27-image pair not baked", "eight stubs allow_add pending",
            "combined native103/105 bindings and four new NOLOAD findings require outer review",
            "Flutter strings eight ADDED and open-site delta require outer review",
            "runtime three call-set differences and two NOLOAD line shifts require outer review",
            "U15 per-board armed transaction BASE and promotion signoff pending"],
        finalization="Compose one native version and one runtime JAR version only after arrivals; atomically update payload, target aliases, inputs and reference bindings; do not publish mixed intermediate executables"))
    save("results.json", dict(execution_enabled=False, rollout_ready=False, board_access=False, vm_access=False, remote_access=False,
        bake_executed=False, native_rebuilt=False, active_registry_updated=False, promotion_confirmed=False,
        final_bundle_sha256=None, final_manifest_sha256=None, final_inputs_sha256=None, input_count=9,
        unchanged_bcp_count=8, changed_bcp=plan["changed_bcp"], images_planned=27, actual_changed_image_count=None,
        arrived={"stubs": plan["bcp"][6]["sha256"], "runtime_jar": plan["runtime_jar"]["sha256"],
            **{row["id"]: row["sha256"] for row in slots["slots"]}},
        native_binding=native_binding, native_reports=native_reports,
        native_review=json.loads((HERE / "native-review.pending.json").read_text()),
        pair_review=json.loads((HERE / "native-pair-review.pending.json").read_text()),
        withdrawn_flutter=json.loads((HERE / "flutter-withdrawal.json").read_text()),
        fix_observers=json.loads((HERE / "fix-observer-receipt.json").read_text()),
        outer_approval_packet=json.loads((HERE / "outer-approval-packet.json").read_text()),
        outer_packet_runs=json.loads((HERE / "outer-packet-runs.json").read_text()),
        pending_native=[row["id"] for row in slots["slots"] if row["state"] == "pending"], excluded=slots["excluded"], dependency_blocked=slots["dependency_blocked"],
        donor_receipt=json.loads((HERE / "donor-receipt-status.json").read_text()),
        static_input_checks=json.loads((HERE / "static-input-checks.json").read_text()),
        native_gates="FRESH paired Mac: N1/N2 REJECT103/105 against current active table; no exceptions applied", production_gates="NOT_RUN: incomplete disabled composition",
        commands=commands, observed_first_fatal_moves=0, conditional_targets={"fd-wifianalyzer": "WifiManager member-gap only; no Wi-Fi functionality", "fd-breezyweather": "launch ON_START ordering only; not a lit claim"}))
    save("documentation.json", {"README.md": [LAYOUT], ".octos/KNOWLEDGE-DIGEST.md": [DIGEST, A3_DIGEST, PACKET_DIGEST]})
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
