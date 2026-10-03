import os
from pathlib import Path
import shutil
import sys
import tempfile

from common import HERE, REPO, capture, load, save


def main():
    records = []
    os.environ["CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER"] = "/usr/bin/cc"
    records.append(capture("test-python", [sys.executable, "-m", "unittest", "discover", "-s", HERE, "-p", "test_*.py", "-v"]))
    records.append(capture("test-u14-existing", [sys.executable, REPO / "benchmark/2026-10-03-u14-on-u13-base/test_binding.py"]))
    records.append(capture("syntax-u14", ["bash", "-n", REPO / "benchmark/2026-10-03-u14-on-u13-base/replay-production.sh"]))
    records.append(capture("syntax-u15", ["bash", "-n", REPO / "benchmark/2026-10-03-u15-final-assembly/replay-production.sh"]))
    records.append(capture("test-rust", ["cargo", "test", "--manifest-path", REPO / "tools/spec-checks/Cargo.toml", "--test", "u15_on_u14_base", "--", "--nocapture"]))
    specs = REPO / "specs/u15-on-u14-base"
    records.append(capture("lint", ["agent-spec", "lint", specs / "t1-binding.spec.md", specs / "t2-replay.spec.md", "--min-score", "0.7"]))
    for name in ["t1-binding", "t2-replay"]:
        changes = ["benchmark/2026-10-03-u15-on-u14-base", "specs/u15-on-u14-base", "tools/spec-checks/tests/u15_on_u14_base.rs", "README.md"]
        if name == "t2-replay":
            changes += ["benchmark/2026-10-03-u14-on-u13-base/replay-production.sh", "benchmark/2026-10-03-u15-final-assembly/replay-production.sh", ".octos/OPS-RUNBOOK.md"]
        records.append(capture("lifecycle-" + name, ["agent-spec", "lifecycle", specs / (name + ".spec.md"), "--code", REPO / "tools/spec-checks",
            *[item for change in changes for item in ["--change", change]]]))
    with tempfile.TemporaryDirectory(prefix="u15-u14-cold-") as temporary:
        cold = Path(temporary)
        for relative in (HERE / "landing-paths.txt").read_text().splitlines():
            destination = cold / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / relative, destination)
        records.append(capture("test-cold", [sys.executable, "-m", "unittest", "discover", "-s", cold / HERE.relative_to(REPO), "-p", "test_*.py", "-v"]))
    save("validation-runs.json", records)
    if any(row["exit_code"] for row in records):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
