"""Run the real CLI on actual T33 bytes and independently mutated copies."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[3]
SAMPLES = Path(os.environ.get("HOST_HAP_SAMPLE_ROOT", str(
    Path.home() / ".local/share/westlake/t33-demo-host-61b")))
REFERENCE = Path(os.environ.get("HOST_HAP_REFERENCE", str(
    ROOT / "benchmark/2026-10-20-t33-demo61b-host/static/reference.json")))
OUTPUT = Path(os.environ.get("HOST_HAP_TEST_OUTPUT", str(
    Path.home() / ".local/share/westlake/host-hap-preflight-tests")))


def invoke(case, intake, release, directory, expected=None):
    argv = [sys.executable, "-B", str(ROOT / "scripts/lab/host_hap_preflight.py"),
            "--intake", str(intake), "--release", str(release),
            "--reference", str(REFERENCE)]
    proc = subprocess.run(argv, capture_output=True)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "argv.json").write_text(json.dumps(argv, indent=2) + "\n")
    (directory / "stdout.json").write_bytes(proc.stdout)
    (directory / "stderr.txt").write_bytes(proc.stderr)
    (directory / "rc").write_text(str(proc.returncode) + "\n")
    result = json.loads(proc.stdout)
    if expected is None:
        assert proc.returncode == 0, proc.stderr.decode()
        assert result["status"] == "OFFLINE_EXACT_INPUTS_VERIFIED"
        assert result["bundle"]["uid"] == 20011206
        assert result["bundle"]["accessTokenId"] == 537243994
        assert result["power"] == {"timeout": 30000, "override": 86400000}
        assert result["hap"]["changed_members"] == ["ets/pages/Index.abc"]
        assert result["fresh_authorization"] is False
        assert result["deployment_verified"] is False and result["device_calls"] == 0
    else:
        assert proc.returncode != 0 and result["status"] == "REJECTED"
        assert expected in proc.stderr.decode(), proc.stderr.decode()
    return {"case": case, "rc": proc.returncode, "expected_error": expected,
            "stdout_sha256": hashlib.sha256(proc.stdout).hexdigest()}


def main(mode):
    assert mode in ("positive", "negative")
    # Missing real evidence must fail, never silently skip or synthesize success.
    assert (SAMPLES / "intake-01/installed-entry.hap").is_file(), "actual T33 sample required"
    run = OUTPUT / (mode + "-" + str(time.time_ns()))
    run.mkdir(parents=True)
    results = []
    if mode == "positive":
        results.append(invoke("actual-t33", SAMPLES / "intake-01",
                              SAMPLES / "release-01", run / "actual-t33"))
    else:
        cases = [
            ("missing-token", "accessTokenId missing/drift"),
            ("wrong-baseline", "wrong baseline/rollback HAP"),
            ("extra-member", "extra/missing HAP member"),
            ("wrong-runtime-path", "runtime baseline/path drift"),
            ("missing-power", "power fields missing/ambiguous"),
            ("missing-compat", "compat absence missing/ambiguous"),
        ]
        for case, error in cases:
            work = run / case
            intake, release = work / "intake", work / "release"
            shutil.copytree(SAMPLES / "intake-01", intake)
            shutil.copytree(SAMPLES / "release-01", release)
            if case == "missing-token":
                f = intake / "bundle.json"
                j = json.loads(f.read_text())
                del j["applicationInfo"]["accessTokenId"]
                f.write_text(json.dumps(j))
            elif case == "wrong-baseline":
                f = release / "rollback-exact.hap"
                f.write_bytes(f.read_bytes() + b"wrong-baseline")
            elif case == "extra-member":
                with zipfile.ZipFile(release / "candidate-signed.hap", "a") as z:
                    z.writestr("unexpected.txt", b"extra member")
            elif case == "wrong-runtime-path":
                f = intake / "runtime-correct/stdout"
                f.write_text(f.read_text().replace("/run.sh", "/wrong-run.sh"))
            elif case == "missing-power":
                f = intake / "hap-sha/stdout"
                f.write_text(f.read_text().replace("OverrideTimeout=", "MissingTimeout="))
            else:
                f = intake / "runtime-correct/stdout"
                f.write_text(f.read_text().replace("COMPAT_ABSENT\n", ""))
            results.append(invoke(case, intake, release, work / "receipt", error))
    (run / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "mode": mode, "cases": results}))


if __name__ == "__main__":
    for selected in sys.argv[1:] or ("positive", "negative"):
        main(selected)
