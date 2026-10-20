#!/usr/bin/env python3
"""Offline fixtures only. Fake transport; never invokes HDC."""
import argparse
import contextlib
import copy
import hashlib
import io
import json
import subprocess
import sys
import time
from pathlib import Path
from unittest import mock
import collect_prefix
import rollback_core


def main():
    p = argparse.ArgumentParser()
    for key in ("repo", "window", "out"):
        p.add_argument("--"+key, type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    c = json.loads((a.window/"context.json").read_text())
    plan = json.loads((a.window/"apply/plan.json").read_text())
    raw = (a.window/"fresh-admission-read/read.stdout").read_text()
    passed = []
    # Archived actual baseline read used only as an offline parse fixture.
    for bridge_after, shim_after in ((False, False), (False, True), (True, False), (True, True)):
        text = raw
        for key, enabled in (("bridge", bridge_after), ("shim", shim_after)):
            if enabled:
                text = text.replace(plan[key+"_before_sha"], plan[key+"_after_sha"])
        ad, _, budget = rollback_core.fill(a.repo, c, c["holder"], text, c["start"]+1300, plan)
        assert ad["fresh_three_slot_receipt_sha256"] is None and budget["recovery_remaining_seconds"] == 500
        passed.append(f"offline_known_pair_{int(bridge_after)}{int(shim_after)}")
    for name, text, changed in (
        ("foreign_sha", raw.replace(plan["bridge_before_sha"], "a"*64), plan),
        ("foreign_holder", raw, dict(plan, holder="other")),
        ("changed_metadata", raw, dict(plan, shim_metadata="644:20011300:20011300")),
    ):
        try:
            rollback_core.fill(a.repo, c, c["holder"], text, c["start"]+1300, changed)
        except ValueError:
            passed.append(name)
        else:
            raise AssertionError(name)
    payload = b"offline fixture, not a device log\n"
    h = hashlib.sha256(payload).hexdigest()
    for scenario in ("success", "postguard_missing", "prefix_changed", "transport_rc0_error"):
        dest = a.out/scenario
        counts = {"device": 0}
        def fake_run(argv, **kw):
            text = ""
            if "board_note.sh" in " ".join(argv):
                text = c["holder"]+"\n"
            elif "recv" in argv:
                counts["device"] += 1
                Path(argv[-1]).write_bytes(payload)
            else:
                counts["device"] += 1
                script = argv[-1]
                if scenario == "transport_rc0_error":
                    text = "Connect server failed\n"
                elif "recheck.raw" in script:
                    if scenario == "postguard_missing":
                        text = "T30_LOG_REMOTE_RC=1\n"
                    else:
                        text = "PREFIX_SHA="+("f"*64 if scenario == "prefix_changed" else h)
                        text += f"\nSOURCE=1:2:{len(payload)}\nT30_LOG_COMPLETE\nT30_LOG_REMOTE_RC=0\n"
                elif "mkdir " in script:
                    text = f"PREFIX_SHA={h}\nT30_LOG_COMPLETE\nT30_LOG_REMOTE_RC=0\n"
                else:
                    text = f"SOURCE=1:2:{len(payload)}\nT30_LOG_COMPLETE\nT30_LOG_REMOTE_RC=0\n"
            kw["stdout"].write(text.encode())
            return subprocess.CompletedProcess(argv, 0)
        argv = ["collect_prefix.py", "--context", str(a.window/"context.json"),
                "--boot", plan["boot"], "--parent", "10049", "--parent-birth", "20675",
                "--host", "9837", "--host-birth", "20423", "--child", "30000",
                "--child-birth", "30001", "--out", str(dest.absolute()), "--execute"]
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(collect_prefix.subprocess, "run", fake_run), \
             mock.patch.object(collect_prefix.time, "time", return_value=c["start"]+100):
            try:
                collect_prefix.main()
            except ValueError:
                assert scenario != "success"
            else:
                assert scenario == "success"
        r = json.loads((dest/"result.json").read_text())
        if scenario == "success":
            assert r["sha256"] == h and r["prefix_recheck_equal"]
        else:
            assert r["status"] == "INCOMPLETE_EVIDENCE_RETAINED"
            if scenario != "transport_rc0_error":
                assert (dest/"selected.raw").read_bytes() == payload
                assert r["transfer_verified"]
        passed.append("fake_transport_"+scenario)
    result = dict(status="OFFLINE_ONLY_NO_DEVICE", passed=len(passed), cases=passed,
                  actual_device_calls=0)
    (a.out/"results.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
