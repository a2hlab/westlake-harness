# Call the ORIGINAL bms_batch.runtime_fingerprint / boot_image_fingerprint through a read-only hdc shim.
# The shim only runs the exact read command the function issues (sha256sum ...), wrapped with the same
# remote-rc marker idea as Board.raw_shell, and records argv/stdout/stderr/rc for each call. No Board object,
# no lock, no device write. usage: fresh_fp.py <serial> <out dir> <repo root>
import json, subprocess, sys, uuid
from pathlib import Path
serial, out, repo = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(repo / "benchmark/2026-09-28-bms-route-deploy/batch")); sys.path.insert(0, str(repo / "scripts/lab"))
import bms_batch
class ReadOnlyShim:
    n = 0
    def shell(self, command, required=True, timeout=120):
        assert command.startswith("sha256sum "), "shim only allows the fingerprint read: " + command[:40]
        ReadOnlyShim.n += 1
        marker = "__G05_RC_" + uuid.uuid4().hex + "__"
        argv = ["hdc", "-t", serial, "shell", command + '; r=$?; printf "\\n' + marker + '%s\\n" "$r"']
        p = subprocess.run(argv, capture_output=True, timeout=timeout)
        text = p.stdout.decode("utf-8", "replace")
        tag = out / f"shim-{ReadOnlyShim.n:02d}"
        Path(str(tag) + ".argv.json").write_text(json.dumps(argv)); Path(str(tag) + ".stdout").write_bytes(p.stdout)
        Path(str(tag) + ".stderr").write_bytes(p.stderr); Path(str(tag) + ".rc").write_text(str(p.returncode))
        remote = text.rsplit(marker, 1)[1].strip() if marker in text else None
        Path(str(tag) + ".remote_rc").write_text(str(remote))
        return (int(remote) if remote not in (None, "") else p.returncode), text.split("\n" + marker)[0]
out.mkdir(parents=True, exist_ok=True)
board = ReadOnlyShim()
rt = bms_batch.runtime_fingerprint(board, out)
bt = bms_batch.boot_image_fingerprint(board, out)
r_lines = (out / "runtime-fingerprint.txt").read_text().splitlines(); b_lines = (out / "boot-image-fingerprint.txt").read_text().splitlines()
print(json.dumps({"runtime_fp": rt, "runtime_files": len([l for l in r_lines if l]), "boot_fp": bt, "boot_files": len([l for l in b_lines if l]),
                  "function_source": "benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py runtime_fingerprint/boot_image_fingerprint (imported unchanged)"}))
