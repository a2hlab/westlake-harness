#!/usr/bin/env python3
"""One-shot publication of existing host evidence, not a test or build runner."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--write", action="store_true")
    a = p.parse_args()
    if not a.write:
        p.error("publication requires --write; no files changed")
    out = Path(__file__).resolve().parent
    base = out.parent
    repo = base.parents[1]
    if (out / "manifest.json").exists():
        raise SystemExit("already published; do not overwrite frozen evidence")
    sha = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
    def put(name, value):
        (out / name).write_text(json.dumps(value, indent=2) + "\n")
    def portable(s):
        aliases = {
            str(repo): "$T4",
            str(repo.parent / "westlake-harness-video"): "$CC",
            str(repo.parent / "westlake-harness"): "$MAIN",
            str(Path.home()): "$HOME",
            "../westlake-harness-video": "$CC",
        }
        for old in sorted(aliases, key=len, reverse=True):
            s = s.replace(old, aliases[old])
        return s
    raw = base / ".private/host-06"
    receipt = json.loads((raw / "receipt.json").read_text())
    assert receipt["status"] == "HOST_ONLY_PASS"
    assert all(x["rc"] == 0 for x in receipt["commands"])
    for name, h in receipt["source_inputs"].items():
        assert sha(Path(name)) == h, name
    put("host-receipt.public.json", json.loads(portable(json.dumps(receipt))))
    peer = Path.home() / ".local/share/westlake/t29-codex-implementation-review"
    peer_rec = peer / "shim-delta-02/receipt.json"
    pr = json.loads(peer_rec.read_text())
    drift = []
    for pin in pr["pins"]:
        f = base / "shim" / pin["path"]
        if sha(f) != pin["sha256"]:
            drift.append(pin["path"])
    assert sorted(drift) == ["build_host.py", "test_route.c"], drift
    put("peer-delta.json", {
        "source": portable(str(peer_rec)), "source_sha256": sha(peer_rec),
        "status": pr["status"], "runtime_sources_equal_peer": True,
        "subsequent_test_only_changes": drift,
        "added_cases": ["layout_failure", "handle_failure", "native_convert_failure",
                        "request_positive_error"],
    })
    # Preserve actual checkpoint01 source bytes from the independently captured
    # snapshot; never reconstruct historical code from current edited files.
    history = base / ".private/checkpoint01-source"
    if not history.exists():
        shutil.copytree(peer / "shim-checkpoint-01/src/shim", history)
    previous = json.loads((base / "shim-checkpoint-01/manifest.json").read_text())
    count = 0
    for pin in previous:
        marker = "/shim/"
        if marker in pin["path"]:
            rel = pin["path"].split(marker, 1)[1]
            f = history / rel
            if not f.exists():
                # The peer source-only snapshot omitted JSON metadata. Reuse
                # current bytes only when they match the historical exact pin.
                existing = base / "shim" / rel
                assert sha(existing) == pin["sha256"], rel
                f.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(existing, f)
            assert sha(f) == pin["sha256"], str(f)
            count += 1
    raw_index = []
    for dirname in ["host-01", "host-02", "host-03", "host-04", "host-05",
                    "host-06", "host-06-launch", "checkpoint01-source"]:
        folder = base / ".private" / dirname
        if not folder.exists():
            continue
        for f in sorted(folder.rglob("*")):
            if f.is_file():
                raw_index.append({"path": str(f.relative_to(base)),
                                  "sha256": sha(f), "bytes": f.stat().st_size})
    put("raw-index.json", raw_index)
    samples = out / "evidence"
    samples.mkdir()
    for name in ["request_failure", "map_failure", "alloc_failure", "precheck_failure",
                 "abort_failure", "layout_failure", "handle_failure", "request_positive_error"]:
        src = raw / ("21-" + name + ".stderr")
        shutil.copyfile(src, samples / (name + ".txt"))
    shutil.copyfile(raw / "00-frozen.stdout", samples / "frozen.txt")
    for name in ["31-core-test.stdout", "33-yv12-test.stdout"]:
        shutil.copyfile(raw / name, samples / name)
    put("results.json", {
        "status": "HOST_ONLY_PASS_NOT_PRODUCTION",
        "logger_cases": len(receipt["logger_cases"]), "route_cases": len(receipt["route_cases"]),
        "commands": len(receipt["commands"]), "all_command_rc": 0,
        "failure_field_cases": 18,
        "host_receipt_sha256": sha(raw / "receipt.json"),
        "preserved_checkpoint01_source_files": count,
        "preserved_failures": [
            "host-02: missing observe29 link input",
            "host-05: Python expected Linux EPROTO=71, actual host EPROTO=100; C was correct",
        ],
        "frozen_registry": {"entries": 8, "checked": 30, "violations": 0},
        "baseline_source_pins": 24,
        "production": "PENDING_CC_FINAL_BRIDGE_THEN_EXACT_OWNER_BINDINGS_THEN_SHIM",
        "device_calls": 0,
    })
    sources = [f for f in (base / "shim").rglob("*")
               if f.is_file() and f.suffix in (".c", ".h", ".py", ".json")]
    files = sources + [f for f in out.rglob("*") if f.is_file()]
    rows = [{"path": str(f.relative_to(repo)), "sha256": sha(f), "bytes": f.stat().st_size}
            for f in sorted(files)]
    put("manifest.json", rows)
    (out / "SHA256SUMS").write_text("".join(f"{r['sha256']}  {r['path']}\n" for r in rows))
    paths = [r["path"] for r in rows] + [
        str((out / n).relative_to(repo)) for n in ["manifest.json", "SHA256SUMS", "landing-paths.txt"]]
    (out / "landing-paths.txt").write_text("\n".join(paths) + "\n")
    print(json.dumps({"files": len(paths), "payload": len(rows),
                      "manifest_sha256": sha(out / "manifest.json")}))


if __name__ == "__main__":
    main()
