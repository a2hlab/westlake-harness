import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from collect import HERE, REPO, WS, portable, sha


def execute(name, command):
    result = subprocess.run([str(value) for value in command], cwd=REPO, capture_output=True, text=True, errors="replace")
    text = result.stdout + result.stderr
    raw = HERE / ".artifacts" / (name + ".txt")
    raw.write_text(text)
    (HERE / "evidence" / (name + ".txt")).write_text(portable(text))
    print(text, end="")
    if result.returncode:
        raise RuntimeError(name + " exit=" + str(result.returncode))
    return dict(command=[portable(value) for value in command], exit_code=result.returncode,
                raw_path=portable(raw), raw_sha256=sha(raw), evidence="evidence/" + name + ".txt")


def listing():
    paths = [path for path in HERE.rglob("*") if path.is_file() and not any(name in path.parts for name in [".artifacts", "__pycache__"])]
    paths += list((REPO / "specs/u12-disappeared").glob("*.spec.md"))
    paths.append(REPO / "tools/spec-checks/tests/u12_disappeared.rs")
    target = HERE / "landing-paths.txt"
    if target not in paths:
        paths.append(target)
    target.write_text("\n".join(sorted(str(path.relative_to(REPO)) for path in paths)) + "\n")
    return target


def main():
    records = [
        execute("python-tests", [sys.executable, HERE / "test_analysis.py", "-v"]),
        execute("rust-tests", ["cargo", "test", "--manifest-path", REPO / "tools/spec-checks/Cargo.toml", "--test", "u12_disappeared"]),
        execute("spec-lint", ["agent-spec", "lint", REPO / "specs/u12-disappeared/t1-evidence.spec.md", "--min-score", "0.7"]),
        execute("spec-lifecycle", ["agent-spec", "lifecycle", REPO / "specs/u12-disappeared/t1-evidence.spec.md", "--code", REPO / "tools/spec-checks", "--format", "json"]),
    ]
    target = listing()
    with tempfile.TemporaryDirectory(prefix="u12-disappeared-landing-") as scratch:
        root = Path(scratch)
        for name in target.read_text().splitlines():
            output = root / name
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / name, output)
        records.append(execute("isolated-landing-tests", [sys.executable, root / HERE.relative_to(REPO) / "test_analysis.py", "-v"]))
    (HERE / "validation.json").write_text(json.dumps(dict(execution_enabled=False, gates=records,
        original_staged_paths_sha256=sha(subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=REPO)),
        tools={name: dict(path=portable(Path(shutil.which(name)).resolve()), sha256=sha(Path(shutil.which(name)).resolve()))
               for name in ["llvm-readelf", "agent-spec"]}), indent=2) + "\n")
    (HERE / "evidence/preflight.txt").touch()
    target = listing()
    record = execute("preflight", [sys.executable, WS / "westlake-harness/scripts/lab/land.py", REPO, target.relative_to(REPO), "-m", "x", "--preflight"])
    value = json.loads((HERE / "validation.json").read_text())
    value["gates"].append(record)
    (HERE / "validation.json").write_text(json.dumps(value, indent=2) + "\n")


if __name__ == "__main__":
    main()
