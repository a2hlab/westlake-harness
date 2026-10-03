"""Read-only binding preparation; never arm a composition or contact a board."""
import hashlib
import json
import os
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = Path(os.environ.get("WORKSPACES", REPO.parent))
MASTER = WS / "westlake-harness"
EXECUTOR = WS / "westlake-harness-u7-executor"
EXPECTED = {
    "common": ("56974aa051137bfd0da6f0dba2d714891c2aea4f65114e1600ebc5854a721770", "2abe4a4917e09d53f47edcfec0ec21b9e131fc72253b8f4aa3d47ff87e8d5aa0"),
    "61b": ("afb443708cdb9f7b4a26657b0f00068547f5918ea10802d6aafbb30156c95a1a", "0a31ad3515c021ce22d00c3d2e2543e16f9164a1b7d2fc6d1d966f3f2fbba761")}
COPY_LIMITS = {"liboh_adapter_bridge.so": {"min": 1, "max": 2}, "liboh_android_runtime.so": {"min": 1, "max": 2},
    "libjavacore.so": {"min": 1, "max": 2}, "libicu74compat.so": {"min": 0, "max": 1}}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def portable(value):
    if isinstance(value, dict):
        return {key: portable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [portable(item) for item in value]
    if isinstance(value, Path):
        value = str(value)
    if isinstance(value, str):
        value = value.replace(str(WS) + "/", "$WORKSPACES/")
    return value


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(portable(value), indent=2, ensure_ascii=False) + "\n")


def expand(value):
    return Path(value.replace("$WORKSPACES/", str(WS) + "/"))


def main():
    provenance = []
    def snapshot(source, relative):
        target = HERE / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        provenance.append(dict(path=source, sha256=sha(source), snapshot=target, snapshot_sha256=sha(target)))
        return target
    stage_a = MASTER / "benchmark/2026-10-03-u14-stage-a-plan"
    live_a = EXECUTOR / "benchmark/2026-10-03-u14-stage-a-plan/window1"
    reference = snapshot(MASTER / "benchmark/2026-10-03-u14-reference/sources.json", "inputs/reference.json")
    review = snapshot(stage_a / "outer-smoke-review.json", "inputs/outer-smoke-review.json")
    snapshot(MASTER / "scripts/lab/stage_a_selftest.py", "inputs/stage-a-selftest-source.txt")
    old = MASTER / "benchmark/2026-10-03-u13-stage-b"
    for name in ["promotion_dispatch_u13.py", "promotion_hook_u13_runtime.py", "review_wait_u13.py", "test_promotion_u13.py"]:
        snapshot(old / name, "inputs/donor/" + name + ".txt")
    prefix = "$WORKSPACES/westlake-harness/benchmark/2026-10-03-u14-stage-b"
    decision_prefix = "$WORKSPACES/westlake-harness/benchmark/2026-10-03-u14-stage-a-decision"
    for variant in ["common", "61b"]:
        source = stage_a / "window1" / variant / "composition.json"
        snapshot(source, "inputs/" + variant + "-stage-a-composition.json")
        value = json.loads(source.read_text())
        if (value["bundle_sha256"], value["base_bundle_sha256"]) != EXPECTED[variant]:
            raise ValueError("Exact armed U14/U13 variants changed")
        for name, expected in [("package", value["bundle_sha256"]), ("base_bundle", value["base_bundle_sha256"])]:
            if sha(expand(value[name]) / "bundle.json") != expected:
                raise ValueError("Persistent armed bundle changed")
        for name in ["package", "unarmed_package", "base_bundle"]:
            snapshot(expand(value[name]) / "bundle.json", "inputs/" + variant + "-" + name + "-bundle.json")
        snapshot(stage_a / "window1" / variant / "arming-proof.json", "inputs/" + variant + "-arming-proof.json")
        value.update(execution_enabled=False, stage_b_authorization=prefix + "/outer-stage-b-authorization-" + variant + ".json",
            decision_tag=variant, smoke_review_sha256=sha(review), reference_sha256=sha(reference),
            copy_limits=COPY_LIMITS, smoke_specs={}, recovery_smoke_specs={}, smoke_sha256={}, recovery_smoke_sha256={},
            stage_a_decision=decision_prefix + "/outer-stage-a-" + variant + ".json",
            stage_a_selection=dict(root="$WORKSPACES/westlake-harness-u7-executor/benchmark/2026-10-03-u14-stage-a-plan", pattern="window*/u14-A*/*/runner/**/record.json"),
            stage_a_status="future outer signed decision; no synthetic signoff used in production")
        recovery_path = snapshot(stage_a / "window1" / variant / "recovery-u13.json", variant + "/recovery-u13.json")
        recovered = json.loads(recovery_path.read_text())["boards"]
        for serial, identity in value["candidate_boards"].items():
            if identity["identity_assertions"] != 322 or identity["unique_paths"] != 320 or len(identity["expected"]) != 320:
                raise ValueError("Complete U14 identity map required")
            restore = recovered[serial]
            if restore["identity_assertions"] != 321 or restore["unique_paths"] != 319 or len(restore["expected"]) != 319:
                raise ValueError("Complete U13 identity map required")
            board = "5ea" if serial.startswith("5ea") else "5cd" if serial.startswith("5cd") else "61b"
            spec = snapshot(live_a / variant / ("smoke-" + board + ".json"), variant + "/smoke-" + board + ".json")
            spec_body = json.loads(spec.read_text())
            if spec_body.get("control_selftest") is not True or spec_body["probe"]["copy_limits"] != COPY_LIMITS or spec_body["probe"]["single_copy"] != ["libart.so", "libopenjdkjvm.so", *COPY_LIMITS]:
                raise ValueError("Reviewed copy limits or strict control health changed")
            expected_fp = {"runtime_fp": identity["fingerprints"]["runtime"]["sha256_12"], "boot_fp": identity["fingerprints"]["boot"]["sha256_12"]}
            if spec_body["expect"] != expected_fp:
                raise ValueError("Smoke identity binding differs")
            restored_spec = snapshot(live_a / variant / ("smoke-restored-" + board + ".json"), variant + "/restored-" + board + ".json")
            value["smoke_specs"][serial] = "smoke-" + board + ".json"
            value["recovery_smoke_specs"][serial] = "restored-" + board + ".json"
            value["smoke_sha256"][serial] = sha(spec)
            value["recovery_smoke_sha256"][serial] = sha(restored_spec)
            plan_path = prefix + "/" + variant + "/plan-" + board + ".json"
            window = prefix + "/" + variant + "/$U14_B_RUN_ID/" + board
            runner = prefix + "/" + variant + "/runner.py"
            plan = dict(serial=serial, lane="cx-t0", entry="90", board="$WORKSPACES/westlake-harness/.octos/boards/app-lighting.md",
                phase="B", execution_enabled=False, rollout_ready=False, why="Disabled U14 promotion preparation; no fresh outer decision or activation",
                package=value["package"], bundle_sha256=value["bundle_sha256"], package_manifest_sha256=value["native_manifest_sha256"], native_inputs_sha256=value["native_inputs_sha256"],
                out=window + "/runner", window_limit_minutes=30, stop_new_tests_by_minute=20, shards=[],
                offline_precheck=dict(hypothesis="Outer-signed U14 Stage A preserved all126 reference keys and strict process crypto health; fresh same-window controls may authorize U14 retention.",
                    evidence=[prefix + "/" + variant + "/composition.json", prefix + "/inputs/outer-smoke-review.json"], result="pending outer Stage A and Stage B authorization",
                    expect=dict(confirm="Exact322/320 candidate identity, strict copy ceilings and fresh same-window bright HW/ZZ allow retention after all signed Stage A gates.",
                        refute="Any wrong binding, badtag, stale/missing signoff or identity/smoke failure selects complete U13 rollback321/319.")),
                stage_a_decision=value["stage_a_decision"], smoke_spec=prefix + "/" + variant + "/" + value["smoke_specs"][serial],
                before_unlock_restored_spec=prefix + "/" + variant + "/" + value["recovery_smoke_specs"][serial],
                after_lock=["python3", runner, "hook", "--apply", "--serial", serial, "--root", window, "--plan", plan_path, "--stage-a-decision", value["stage_a_decision"]],
                before_unlock=["python3", runner, "review", "--serial", serial, "--root", window, "--plan", plan_path],
                batch_flags=["--hilog", "20", "--shots", "5,20"],
                candidate_identity={key: identity[key] for key in ["identity_assertions", "unique_paths", "fingerprints"]},
                restore=dict(state="U13", package=value["base_bundle"], bundle_sha256=value["base_bundle_sha256"], identity_assertions=321, unique_paths=319,
                    fingerprints=restore["fingerprints"], unconditional=False, failure_preserves_lock=True, condition="Every refusal restores; only fresh same-board/window outer signature permits complete U14 retention"),
                promotion_policy=dict(signature_wait_max_minutes=20, rollback_reserve_minutes=6, expiry="restore U13; identity failure preserves lock"))
            write(HERE / variant / ("plan-" + board + ".json"), plan)
        write(HERE / variant / "composition.json", value)
        write(HERE / variant / "future-stage-a-decision-template.json", dict(schema="outer-stage-a/v1", release="U14", phase="A", signed_by=None, signed_at=None,
            promotion_authorized=False, bundle_sha256=value["approved_unarmed_bundle_sha256"], native_manifest_sha256=value["native_manifest_sha256"], native_inputs_sha256=value["native_inputs_sha256"],
            effective_baseline_bundle_sha256=value["base_bundle_sha256"], reference_sha256=sha(reference), confirmed_regressions=[],
            stage_A_regression_verdict=dict(u14_reference_lit_total=126, measured=None, same_or_lit_within_k_of_n=None, confirmed_regressions=None),
            process_selftest_gate=dict(report=None, report_sha256=None, explanations=None, explanations_sha256=None, summary=None, summary_sha256=None,
                root=None, pattern=None, measured_records=[], tool=dict(path="$WORKSPACES/westlake-harness/scripts/lab/stage_a_selftest.py", sha256=sha(MASTER / "scripts/lab/stage_a_selftest.py"), exit_code=None))))
    for variant in ["common", "61b"]:
        snapshot(live_a / variant / "window_hook.py", "inputs/donor/u14-stage-a-backend-" + variant + ".txt")
    snapshot(live_a / "common/dispatch.py", "inputs/donor/u14-stage-a-dispatch.txt")
    write(HERE / "source-provenance.json", dict(files=provenance, execution_enabled=False, board_access=False))
    print("Prepared disabled U14 Stage B: 56974aa0/afb44370 -> rollback2abe4a49/0a31ad35; candidate322/320 restore321/319")


if __name__ == "__main__":
    main()
