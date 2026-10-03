import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from prepare import HERE, REPO, portable, sha, write


def capture(name, command):
    command = [str(item) for item in command]
    result = subprocess.run(command, cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    raw = HERE / ".artifacts/raw" / (name + ".txt")
    evidence = HERE / "evidence" / (name + ".txt")
    raw.parent.mkdir(parents=True, exist_ok=True)
    evidence.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(result.stdout)
    evidence.write_text(portable(result.stdout.decode("utf-8", errors="backslashreplace")))
    record = dict(command=command, exit_code=result.returncode, raw=raw, raw_sha256=sha(raw),
        evidence=evidence, evidence_sha256=sha(evidence))
    print(name + " exit=" + str(result.returncode), flush=True)
    return record


def archive(name):
    source = HERE / name
    target = HERE / "inputs/history-p1p2" / name
    if source.exists() and not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def main():
    for name in ["vm-replay.json", "validation-runs.json", "preflight.json", "results.json"]:
        archive(name)
    write(HERE / "vm-replay.json", dict(command=["WORKSPACES=$HOME/orca/workspaces", "bash",
        "benchmark/2026-10-03-u14-stage-b/replay-known-answers.sh", "vm"], exit_code=None,
        status="pending outer replay after P1/P2 correction", actual_vm_replay=False,
        historical_receipt="inputs/history-p1p2/vm-replay.json", historical_tests=16,
        expected_tests=23, board_access=False, execution_enabled=False))
    os.environ["CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER"] = "/usr/bin/cc"
    os.environ["WORKSPACES"] = str(REPO.parent)
    contracts = ["specs/u14-stage-b/" + name + ".spec.md" for name in ["t1-binding", "t2-promotion", "t3-wiring"]]
    records = [capture("p1p2-tests-mac", ["bash", HERE / "replay-known-answers.sh", "mac"]),
        capture("p1p2-tests-rust", ["cargo", "test", "--manifest-path", "tools/spec-checks/Cargo.toml", "--test", "u14_stage_b"]),
        capture("p1p2-lint", ["agent-spec", "lint", *contracts, "--min-score", "0.7"])]
    for contract in contracts:
        records.append(capture("p1p2-lifecycle-" + Path(contract).stem, ["agent-spec", "lifecycle", contract,
            "--code", "tools/spec-checks", "--change", "benchmark/2026-10-03-u14-stage-b",
            "--change", "specs/u14-stage-b", "--change", "tools/spec-checks/tests/u14_stage_b.rs",
            "--format", "json", "--run-log-dir", HERE / ".artifacts/spec-logs/p1p2"]))
    cold = Path(tempfile.mkdtemp(prefix="u14-p1p2-cold-")) / "repo/benchmark/2026-10-03-u14-stage-b"
    shutil.copytree(HERE, cold, ignore=shutil.ignore_patterns(".artifacts", "__pycache__"))
    records.append(capture("p1p2-tests-cold", [sys.executable, cold / "test_promotion_u14.py"]))
    write(HERE / "validation-runs.json", dict(records=records, expected_python_tests=23, expected_rust_tests=3,
        cold_artifacts_present=False, vm_access=False, board_access=False, execution_enabled=False,
        source_sha256={name: sha(HERE / name) for name in ["review_wait_u14.py", "promotion_hook_u14_runtime.py", "test_promotion_u14.py"]}))
    if any(record["exit_code"] != 0 for record in records):
        raise SystemExit("Offline validation failed; raw output retained")
    print("P1/P2: Mac23 / Rust3 / cold23 / lint3 / lifecycle3 exit0; fresh VM pending outer")


if __name__ == "__main__":
    main()
