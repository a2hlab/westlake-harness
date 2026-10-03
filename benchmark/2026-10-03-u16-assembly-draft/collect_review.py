import json

from prepare import HERE, WS, portable, save, sha
from native_stage import MEMBER, STAGING


def main():
    binding = json.loads((HERE / "native-slot-binding.json").read_text())
    base = WS / binding["base"].removeprefix("$WORKSPACES/")
    abi = json.loads((HERE / "evidence/u16-abi-runtime.json").read_text())
    gates = json.loads((HERE / "native-gate-runs.json").read_text())
    old_source = base / "native/native-checks/u13-m1-compat-shim.cpp"
    new_source = STAGING / "native-checks/u13-m1-compat-shim.cpp"
    old_proof = HERE / "inputs/native-source/u15-m1-compat-shim.cpp"
    old_proof.write_text(portable(old_source.read_text()))
    old_lines, new_lines = old_source.read_text().splitlines(), new_source.read_text().splitlines()
    shifts = []
    for before_line, after_line in [(415, 421), (1408, 1334)]:
        previous = next(json.loads(row) for row in gates["findings_comparison"]["N1"]["removed_nonbinding_rows"]
            if json.loads(row)["detail"]["evidence"]["line"] == before_line)
        current = next(json.loads(row) for row in gates["findings_comparison"]["N1"]["candidate_nonbinding_changes"]
            if json.loads(row)["detail"]["evidence"]["line"] == after_line)
        if old_lines[before_line - 1].strip() != new_lines[after_line - 1].strip():
            raise ValueError("NOLOAD source text changed")
        stripped = json.loads(json.dumps(previous))
        stripped["detail"]["evidence"]["line"] = after_line
        if stripped != current:
            raise ValueError("Finding changed beyond source line")
        shifts.append(dict(before=previous, after=current, old_source=old_source, old_source_sha256=sha(old_source),
            old_snapshot=str(old_proof.relative_to(HERE)), old_snapshot_sha256=sha(old_proof),
            new_source=new_source, new_source_sha256=sha(new_source),
            new_snapshot="inputs/native-source/u13-m1-compat-shim.cpp",
            new_snapshot_sha256=sha(HERE / "inputs/native-source/u13-m1-compat-shim.cpp"), change="line only", approved_by=None))
    save("native-review.pending.json", dict(approved=False, execution_enabled=False, rollout_ready=False,
        baseline_runtime_sha256=binding["baseline_runtime_sha256"], candidate_runtime_sha256=binding["candidate_runtime_sha256"],
        native_manifest_sha256=binding["native_manifest_sha256"], native_inputs_sha256=binding["native_inputs_sha256"],
        abi_call_diffs=abi["call_diffs"], n1_line_shifts=shifts, equal_findings=202,
        request="Outer review of all three nonzero call sets and both NOLOAD line shifts; no exception transfer or apply"))
    withdrawn = WS / "westlake-inputs/generations/u16-flutter-impeller-libandroid-v1/payload/android/lib64/westlake_flutter/libandroid.so"
    old_flutter = base / "native/payload/android/lib64/westlake_flutter/libandroid.so"
    report = HERE / ".artifacts/flutter-arrival-abi.json"
    raw = HERE / ".artifacts/raw/flutter-arrival-abi.txt"
    evidence = HERE / "evidence/flutter-withdrawn-abi.txt"
    evidence.write_text(portable(raw.read_text()))
    flutter = json.loads(report.read_text())
    withdrawn_sha = "15e9885a2086ab854e4489fdaf3a39d74aa94c7155e9b7184d4ac2e3c281a85a"
    if flutter["new"]["sha256"] != withdrawn_sha:
        raise ValueError("Historical withdrawal diagnostic identity drift")
    if sha(old_flutter) != "9b8245022f9c98dac41a85acfa553e96e6385073fd7b15298199a1cce223647b":
        raise ValueError("Actual U15 Flutter identity drift")
    save("evidence/flutter-withdrawn-abi.json", flutter)
    save("flutter-withdrawal.json", dict(state="withdrawn by outer; not selected", decision="outer/user #90 2026-10-03 12:48",
        artifact=withdrawn, artifact_sha256=withdrawn_sha, baseline=old_flutter, baseline_sha256=sha(old_flutter),
        source_now_sha256=sha(withdrawn), source_now_selected=False,
        source_note="Donor may overwrite its release path; historical diagnostic binds its own old/new SHA, not current path bytes",
        removed=flutter["removed"], added=flutter["added"], call_diffs=flutter["call_diffs"], drift=flutter["drift"],
        command_exit_code=0, consumer_check="NOT_RUN: withdrawal diagnostic had no consumer arguments",
        raw=raw, raw_sha256=sha(raw), evidence=str(evidence.relative_to(HERE)), evidence_sha256=sha(evidence),
        report="evidence/flutter-withdrawn-abi.json", report_sha256=sha(HERE / "evidence/flutter-withdrawn-abi.json"),
        selected=False, staged=False, applied=False, execution_enabled=False, rollout_ready=False,
        pending="cc-t3 replacement built on U15 9b824502; removed must be empty and all three ATrace functions preserved"))
    if sha(STAGING / "payload/android/lib64/westlake_flutter/libandroid.so") != sha(old_flutter):
        raise ValueError("Withdrawn Flutter unexpectedly selected")
    if sha(STAGING / MEMBER) != binding["candidate_runtime_sha256"]:
        raise ValueError("Selected runtime changed")
    slots = json.loads((HERE / "native-slots.json").read_text())
    if slots["slots"][1]["state"] == "pending":
        slots["slots"][1].update(target="/system/android/lib64/westlake_flutter/libandroid.so",
            state="pending", sha256=None, applied=False, staged=False, withdrawn_sha256=withdrawn_sha,
            baseline_sha256=sha(old_flutter), blocker="15e9885a withdrawn: removed three U15 ATrace exports; corrected U15-based donor pending")
    save("native-slots.json", slots)
    print("REVIEW: 3 raw call-set differences + 2 line-only NOLOAD shifts; Flutter15e988 withdrawn, U15 9b82 retained")


if __name__ == "__main__":
    main()
