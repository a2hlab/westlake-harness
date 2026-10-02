import json
from pathlib import Path
import subprocess
import tempfile

from common import HERE, REPO, capture, portable, save, sha

README_ROW = "| **`benchmark/2026-10-03-u14-final-assembly/`** | **Single disabled U14 native/JAR/27-image batch; actual two-run receipts, U13 static comparison, 159 rebind previews and explicit new review items.** |"
DIGEST_ROW = "- U14单一禁用装配(2026-10-03,cx-bms):实际hw248两遍compiler/tee/session0，27镜像相对U13变19件，严格复现26/27；实际build receipt verified不等于backtrace例外获批。完整Mac门159旧finding仅preview，新N1=44、新N2=1(Flutter新增libc++在域外)，全部保留REJECT；新strong UND有字节provider，weak loader/compiler hooks无provider不能偷算强缺符号或owner可见。T4b须实际新OAT重绑BUILD，旧绑定拒项保留。见benchmark/2026-10-03-u14-final-assembly/。"


def main():
    save("documentation.json", dict(readme_additions=[README_ROW], digest_additions=[DIGEST_ROW]))
    records = [capture("tests-rust", ["cargo", "test", "--manifest-path", REPO / "tools/spec-checks/Cargo.toml", "--test", "u14_final_assembly", "--", "--nocapture"])]
    listed = sorted(path.relative_to(REPO).as_posix() for path in HERE.rglob("*") if path.is_file() and ".artifacts" not in path.parts and "__pycache__" not in path.parts and path.name not in ["landing-paths.txt", "listing-receipt.json"])
    listed += ["specs/u14-final-assembly/project.spec.md", "specs/u14-final-assembly/t1-compose.spec.md", "specs/u14-final-assembly/t2-evidence.spec.md", "tools/spec-checks/tests/u14_final_assembly.rs"]
    with tempfile.TemporaryDirectory(prefix="u14-cold-") as directory:
        root = Path(directory)
        for name in listed:
            source, destination = REPO / name, root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
        script = root / HERE.relative_to(REPO) / "test_assembly.py"
        process = subprocess.run(["python3", script], capture_output=True, text=True, errors="replace")
        output = HERE / "evidence/tests-cold.txt"
        output.write_text(portable(process.stdout + process.stderr))
        records.append(dict(name="cold-listed-files-only", exit_code=process.returncode, evidence=output.relative_to(HERE), private_artifacts_present=False))
        if process.returncode:
            raise ValueError("Cold tests failed")
    save("test-summary.json", dict(records=records, python_tests=12, rust_selectors=2, cold_python_tests=12))
    listed = sorted(set(listed + ["benchmark/2026-10-03-u14-final-assembly/evidence/tests-cold.txt", "benchmark/2026-10-03-u14-final-assembly/test-summary.json", "benchmark/2026-10-03-u14-final-assembly/listing-receipt.json"]))
    listing = HERE / "landing-paths.txt"
    listing.write_text("\n".join(listed) + "\n")
    save("listing-receipt.json", dict(listing_sha256=sha(listing), paths=len(listed), files=[dict(path=name, sha256=sha(REPO / name), bytes=(REPO / name).stat().st_size) for name in listed if not name.endswith("/listing-receipt.json")],
        execution_enabled=False, git_index_write=False))
    print("LANDING paths=" + str(len(listed)) + " sha256=" + sha(listing))


if __name__ == "__main__":
    main()
