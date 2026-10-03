import os
from pathlib import Path
import shutil
import sys
import tempfile

from native_static import capture
from prepare import HERE, REPO, save


def main():
    previous = HERE / "validation-runs.json"
    historical = HERE / "inputs/history-v1/validation-runs.json"
    if previous.exists() and not historical.exists():
        historical.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(previous, historical)
    os.environ["CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER"] = "/usr/bin/cc"
    contracts = ["specs/u16-assembly-draft/" + name + ".spec.md" for name in ["t1-inputs", "t2-bake", "t3-native", "t4-native-pair"]]
    records = [capture("u16-a3-tests-mac", [sys.executable, HERE / "test_draft.py"]),
        capture("u16-a3-tests-rust", ["cargo", "test", "--manifest-path", "tools/spec-checks/Cargo.toml", "--test", "u16_assembly_draft"]),
        capture("u16-a3-lint", ["agent-spec", "lint", *contracts, "--min-score", "0.7"])]
    for contract in contracts:
        records.append(capture("u16-a3-lifecycle-" + Path(contract).stem, ["agent-spec", "lifecycle", contract,
            "--code", "tools/spec-checks", "--change", "benchmark/2026-10-03-u16-assembly-draft",
            "--change", "specs/u16-assembly-draft", "--change", "tools/spec-checks/tests/u16_assembly_draft.rs",
            "--format", "json", "--run-log-dir", HERE / ".artifacts/spec-logs/pair"]))
    cold = Path(tempfile.mkdtemp(prefix="u16-pair-cold-")) / "repo/benchmark/2026-10-03-u16-assembly-draft"
    shutil.copytree(HERE, cold, ignore=shutil.ignore_patterns(".artifacts", "__pycache__"))
    records.append(capture("u16-a3-tests-cold", [sys.executable, cold / "test_draft.py"]))
    save("validation-runs.json", dict(records=records, cold_root=cold, cold_artifacts_present=False,
        expected_python_tests=21, expected_rust_tests=4, execution_enabled=False, rollout_ready=False, board_access=False,
        vm_access=False, remote_access=False, linker=os.environ["CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER"]))
    if any(row["exit_code"] != 0 for row in records):
        raise SystemExit("Offline tests or contracts failed; retain raw output")
    print("OFFLINE: Mac21 / Rust4 / cold21 / lint4 / lifecycle4 all exit0; native gate rejection is separate")


if __name__ == "__main__":
    os.chdir(REPO)
    main()
