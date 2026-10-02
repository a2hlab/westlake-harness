import collections
import json
from pathlib import Path

from prepare import BASES, HERE, MASTER, PRIVATE, REPO, RELEASE, WS, portable, save, sha, stage
from validation import check_plan, check_slots


LAYOUT = "| **`benchmark/2026-10-03-u15-plan/`** | **Disabled U15 input preparation: M3 native runtime, framework Bitmap-only BCP swap, full 27-image hw248 rebake plan, pending routes and explicit per-board transaction parameters.** |"
DIGEST = "- U15备料(2026-10-03,cx-bms):U14 common9b42/61bf589只作内容基座，不代表晋级；native94c3与非BCP runtime JAR0349分开，framework9e55换9件中的1件须FZ005全27新配对。hw248 hostname=ecs-9f6c且HOME按FZ005身份显式设，不能照抄旧hw248主机名/SSH HOME或复用U14 backtrace批文；class-diff UTF8解码失败保留unknown，不借donor verifier变PASS。compat v3外环06:55停构建，待Meet ANL/host同名单路由，不填假compat件。见benchmark/2026-10-03-u15-plan/。"


def main():
    plan = json.loads((HERE / "plan.json").read_text())
    images = json.loads((HERE / "expected-images.json").read_text())
    slots = json.loads((HERE / "native-slots.json").read_text())
    host_report = MASTER / "benchmark/2026-10-03-u15-host-mindustry/results.json"
    stopped_report = MASTER / "benchmark/2026-10-03-u15-compat-v3/results.json"
    host = json.loads(host_report.read_text())
    stopped = json.loads(stopped_report.read_text())
    host_digest = host["a_prime_gates"]["determinism"]["u15"]
    arrived = stage(RELEASE / "u15-host-mindustry-v1/appspawn-x", PRIVATE / "intermediate-host/appspawn-x", host_digest)
    slots["slots"][1]["arrived_reference"] = arrived
    slots["slots"][1]["selection_reason"] = "08175d18 intermediate Mindustry donor arrived; outer 06:55 requires subsequent Meet route in the same host and ANL, not a second native version"
    slots["slots"][2]["upstream_status"] = "STOPPED_BEFORE_BUILD; predicts zero; do not fabricate compat v3"
    slots["slots"][2]["selection_allowed"] = False
    slots["replacement_waitlist"] = dict(outer_ack="ACK(90) 2026-10-03T06:55:21+0800", scope="org.jitsi.meet in both ANL and host native-domain lists",
        host_parent_sha256=host_digest, host_candidate_sha256=None, anl_candidate_sha256=None, owner="cc-t3", applied=False)
    if stopped["built"] is not False:
        raise ValueError("Compat stopped-before-build evidence changed")
    save("native-slots.json", slots)
    snapshots = json.loads((HERE / "source-snapshots.json").read_text())
    for source, relative in [(host_report, "inputs/source/host-mindustry/results.json"), (stopped_report, "inputs/source/compat-v3/results.json")]:
        destination = HERE / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(portable(source.read_text()))
        snapshots.append(dict(source=source, source_sha256=sha(source), snapshot=relative, snapshot_sha256=sha(destination),
            transformation="portable paths; arrived intermediate or stopped donor, not composed native candidate"))
    snapshots = list({row["snapshot"]: row for row in snapshots}.values())
    save("source-snapshots.json", snapshots)
    check_plan(plan, images)
    check_slots(slots)
    argv = ["$HW248_HOME/aosp-14.0.0_r1-art/out/host/linux-x86/bin/dex2oat64", "--android-root=/system", "--instruction-set=arm64",
        "--base=0x70000000", "--compiler-filter=speed", "--runtime-arg", "-Xms64m", "--runtime-arg", "-Xmx512m", "--runtime-arg", "-Xverify:none",
        "--image=$HW248_HOME/u15-bitmap-9e55-v1/work/products/arm64/boot.art", "--oat-file=$HW248_HOME/u15-bitmap-9e55-v1/work/products/arm64/boot.oat"]
    for row in plan["bcp"]:
        argv.extend(["--dex-file=$HW248_HOME/u15-bitmap-9e55-v1/work/incoming/" + row["name"], "--dex-location=" + row["target"]])
    save("planned-argv.json", dict(status="PLANNED_NOT_EXECUTED", run1=argv, run2=argv, actual_argv_sha256=None))
    save("transaction-base.template.json", dict(status="UNBOUND_NO_PROMOTION_CLAIM", execution_enabled=False,
        profiles={name: dict(content_base_sha256=digest, transaction_base=dict(path=None, sha256=None, signed_identity=None, expected=None),
            installer_identity={target: plan["content_bases"][name]["installers"][target] for target in plan["content_bases"][name]["installers"]}) for name, digest in BASES.items()},
        rule="Require a fresh signed full expected identity for each board; do not use legacy reference/runtime or short fingerprints as promotion evidence"))
    inventory = [dict(path=str(path.relative_to(PRIVATE)), sha256=sha(path), bytes=path.stat().st_size)
        for path in sorted(PRIVATE.rglob("*")) if path.is_file()]
    save("input-inventory.json", dict(root=PRIVATE, files=inventory, scope="nine effective candidate BCP JARs, unchanged runtime JAR, M3 ELF and unselected intermediate host; no new boot images"))
    for name, digest in BASES.items():
        root = WS / plan["content_bases"][name]["path"].removeprefix("$WORKSPACES/")
        if sha(root / "bundle.json") != digest:
            raise ValueError("U14 content base changed during preparation")
    forecast = collections.Counter(row["prediction"].split(":", 1)[0] for row in images)
    checks = json.loads((HERE / "static-input-checks.json").read_text())
    save("results.json", dict(schema="u15-disabled-preparation-results/v1", status="PREPARATION_COMPLETE_EXECUTION_DISABLED",
        content_bases=BASES, transaction_base={"common": None, "61b": None}, promotion_confirmed=False,
        execution_enabled=False, rollout_ready=False, bake_executed=False, native_build_executed=False, vm_access=False, board_access=False,
        active_registry_updated=False, final_bundle_sha256=None, native_manifest_sha256=None, native_inputs_sha256=None,
        bcp_count=9, changed_bcp=["framework.jar"], runtime_jar_changed=False, selected_native_slots=["runtime-m3"],
        pending_native_slots=["host-mindustry final with Meet route", "compat-v3 stopped; replacement ANL/host route pending"],
        unselected_intermediate_host_sha256=host_digest, expected_image_count=27, actual_changed_image_count=None, image_forecast=dict(forecast),
        paired_receipt_status="NOT_RUN; actual argv/log/rc/output identities null; U14 exception cannot transfer",
        raw_input_check_exit_codes={row["name"]: row["exit_code"] for row in checks["results"]},
        admission="PENDING fresh composed N1/N2/static/class/image gates and exact outer approval",
        donor_predictions=dict(runtime_m3=dict(keys=["cv2-com-bytehamster-flowitgame", "fd-app", "fd-shatteredpixeldungeon"], first_wall_targets=3,
            observed_moves=0, confidence="medium; no on-board result inferred"),
            bitmap=dict(keys=["privacybrowser", "fd-musicplayer"], first_wall_targets=2, observed_moves=0, confidence="conditional; ALPHA_8 null preserved"),
            compat_v3=dict(first_wall_targets=0, built=False), meet_route=dict(first_wall_targets=1, built=False, approved_direction_only=True)),
        plan_sha256=sha(HERE / "plan.json"), tests="see fresh evidence/tests-python.txt, tests-cold.txt, tests-rust.txt and spec lifecycle"))
    save("documentation.json", dict(layout_row=LAYOUT, digest_append=DIGEST, note="Apply snippets only; accumulated root documents are not landing files"))
    paths = sorted(str(path.relative_to(REPO)) for path in HERE.rglob("*") if path.is_file()
        and ".artifacts" not in path.parts and "__pycache__" not in path.parts
        and path.name not in ["landing-paths.txt", "listing-receipt.json"])
    paths.extend(str(path.relative_to(REPO)) for path in sorted((REPO / "specs/u15-plan").glob("*.spec.md")))
    paths.extend(["tools/spec-checks/tests/u15_plan.rs", str((HERE / "listing-receipt.json").relative_to(REPO))])
    paths = sorted(set(paths))
    (HERE / "landing-paths.txt").write_text("\n".join(paths) + "\n")
    save("listing-receipt.json", dict(paths=len(paths), listing_sha256=sha(HERE / "landing-paths.txt"), binaries=False,
        default_disabled=True, large_evidence="persistent .artifacts only", user_paths="preflight required"))
    print("U15 PLAN: paths=" + str(len(paths)) + " listing=" + sha(HERE / "landing-paths.txt") + "; no final bundle SHA, no bake, no production admission")


if __name__ == "__main__":
    main()
