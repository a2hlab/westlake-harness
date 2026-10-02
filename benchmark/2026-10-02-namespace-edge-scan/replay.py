import hashlib
import json
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "scripts/lab/tests"))
import test_open_site_scan as answers


def sha(filename):
    return hashlib.sha256(filename.read_bytes()).hexdigest()


def portable(value):
    return value.replace(str(REPO) + "/", "$REPO/").replace(str(answers.WS), "$WORKSPACES")


def main():
    raw = HERE / ".artifacts/raw"
    evidence = HERE / "evidence"
    raw.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(exist_ok=True)
    rows = {}
    for name, filename in [("u9", answers.HOST), ("u10-r2", answers.R2), ("r3", answers.R3), ("spill677", answers.SPILL)]:
        if sha(filename) != answers.PINS[filename]:
            raise ValueError("known-answer input changed: " + name)
        output = raw / (name + ".json")
        command = [sys.executable, str(REPO / "scripts/lab/open_site_scan.py"), str(filename), "--json", str(output)]
        result = subprocess.run(command, capture_output=True, text=True)
        content = result.stdout + result.stderr
        (raw / (name + ".txt")).write_text(content)
        (evidence / (name + ".txt")).write_text(portable(content))
        if result.returncode != 0:
            raise RuntimeError("scanner listing failed: " + name)
        scan = json.loads(output.read_text())
        (evidence / (name + ".json")).write_text(portable(output.read_text()))
        rows[name] = {"input": portable(str(filename)), "sha256": sha(filename),
                      "command": [portable(argument) for argument in command], "exit_code": result.returncode,
                      "raw_sha256": sha(raw / (name + ".txt")), "display_sha256": sha(evidence / (name + ".txt")),
                      "sites": len(scan["binaries"][0]["sites"]), "namespace_edges": len(scan["binaries"][0]["namespace_edges"]),
                      "findings": scan["findings"]}
    assert len([row for row in rows["u10-r2"]["findings"] if row["kind"] == "INHERIT-REPEAT"]) == 1
    assert not any(row["kind"] == "INHERIT-REPEAT" for row in rows["r3"]["findings"])
    assert not any(row["kind"] == "INHERIT-AFTER-OPEN" and row["site"].endswith(("@0xccd8", "@0xccf0")) for row in rows["u9"]["findings"])
    receipt = {"mode": "offline-tool-known-answers", "device_io": False, "native_package_modified": False,
               "scanner_sha256": sha(REPO / "scripts/lab/open_site_scan.py"),
               "tests_sha256": sha(REPO / "scripts/lab/tests/test_open_site_scan.py"), "rows": rows,
               "limits": ["linear register resolution", "syntactic CFG may-path, not value-sensitive execution",
                          "one direct caller only", "unknown pointers and indirect calls are not owner proof",
                          "listing exit0 is not a namespace safety verdict; --strict retains its existing MULTI-NS meaning"]}
    (HERE / "results.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("KNOWN ANSWERS PASS: r2 repeat=1, r3 repeat=0; U9 ccd8/ccf0 after-open=0")


if __name__ == "__main__":
    main()
