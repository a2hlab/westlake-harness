import argparse
import json
from pathlib import Path

from scan_window_consumers import digest, dynamic, symbols, MISSING_INLINE


HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    manifest_file = args.package / "package.json"
    manifest = json.loads(manifest_file.read_text())
    rows = []
    scanned = 0
    for name, expected in sorted(manifest["files"].items()):
        if not name.endswith(".so"):
            continue
        filename = args.package / name
        if digest(filename) != expected:
            raise ValueError("payload identity mismatch: " + name)
        scanned += 1
        needed = dynamic(filename)["needed"]
        if "libandroid.so" not in needed:
            continue
        imported = symbols(filename, False)
        rows.append({"member": name, "sha256": expected, "needed": needed,
                     "missing_inline_imported": MISSING_INLINE in imported})
    report = {"schema": "u11-owned-payload-inline-consumers-v1",
              "manifest_sha256": digest(manifest_file), "manifest_variant": manifest.get("variant"),
              "scope": "Every manifest-listed .so, including android/lib64 and descendants, route/system-side Westlake providers and zigzag members",
              "scanned_members": scanned, "needed_libandroid_members": len(rows), "consumers": rows,
              "missing_inline_consumers": [row for row in rows if row["missing_inline_imported"]],
              "outer_exception": "ACK(90) 2026-10-01T22:37:41+0800: single old weak JNI inline wrapper exception, conditional on owned payload UND=0",
              "condition_passed": not any(row["missing_inline_imported"] for row in rows),
              "board_touched": False}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ["manifest_sha256", "scanned_members", "needed_libandroid_members", "missing_inline_consumers", "condition_passed"]}))
    raise SystemExit(0 if report["condition_passed"] else 1)


if __name__ == "__main__":
    main()
