# Generate COMMERCIAL-G05 public outputs from captured private receipts (read-only preflight; no device writes).
# usage: gen.py <out dir> <start epoch> <end epoch>; private root from COMMERCIAL_G01_PRIVATE (spare-preflight dir).
import hashlib, json, os, re, sys
P = os.environ["COMMERCIAL_G01_PRIVATE"]; RAW = os.path.join(P, "raw"); OUT, T0, T1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
HOME = os.path.expanduser("~"); HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, "../../../.."))
def rb(n): return open(os.path.join(RAW, n), "rb").read()
def rt(n): return rb(n).decode("utf-8", "replace")
def ref(n): b = rb(n); return {"alias": "$COMMERCIAL_G05_PRIVATE/raw/" + n, "sha256": hashlib.sha256(b).hexdigest(), "size": len(b)}
def alias(a): return a.replace(HOME, "$HOME")
def repo_ref(rel): b = open(os.path.join(REPO, rel), "rb").read(); return {"alias": rel, "sha256": hashlib.sha256(b).hexdigest(), "size": len(b)}
ids = sorted({f.rsplit(".", 1)[0] if not f.endswith(".invalid.json") else f[:-len(".invalid.json")] for f in os.listdir(RAW)
              if f.endswith((".argv.json",))} | set())
ids = sorted({f[:-len(".argv.json")] for f in os.listdir(RAW) if f.endswith(".argv.json")})
NOTE = {"q09-hilog-tail-ro": "hilog -x with -t/-z combination rejected by hilog (CODE -31); read-only, no log retained; kept as failure",
        "o02-board-run-dispatch-dryrun": "plan shape error: before_unlock given as list of lists; kept", "o03-board-run-disabled-refusal": "same plan shape error; kept",
        "o05-board-run-disabled-refusal": "expected: execution_enabled=false -> REFUSE, no lock taken"}
rec = []
for i in ids:
    inv = os.path.exists(os.path.join(RAW, i + ".invalid.json")); rc = int(rt(i + ".rc").strip())
    out = rt(i + ".stdout")
    cls = "INVALID_LOCAL" if inv else ("FAILED_KEPT" if (rc != 0 and i not in ("o05-board-run-disabled-refusal",)) or "CODE: -31" in out else ("EXPECTED_REFUSAL" if i == "o05-board-run-disabled-refusal" else "OK"))
    refs = [ref(i + e) for e in (".argv.json", ".stdout", ".stderr", ".rc", ".invalid.json") if os.path.exists(os.path.join(RAW, i + e))]
    rec.append({"id": i, "argv": [alias(a) for a in json.loads(rt(i + ".argv.json"))], "rc": rc, "class": cls,
                "status_note": json.loads(rt(i + ".invalid.json"))["note"] if inv else NOTE.get(i, "ok"), "raw_refs": refs})
b0 = rt("q01-boot-before.stdout").split(); b1 = rt("q10-boot-after.stdout").split()
sysl = [l.strip() for l in rt("q02-system.stdout").splitlines()]
mem = dict(re.findall(r"^(\w+):\s+(\d+) kB", rt("q03-mem-disk.stdout"), re.M))
data = re.search(r"^\S+\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+/system/android/lib64/libandroid.so", rt("q03-mem-disk.stdout"), re.M)
ps = rt("q04-ps.stdout").splitlines()
names = [l.split()[5] for l in ps[1:] if len(l.split()) > 5]
fresh = {
 "serial": "5ea34a4500000000000000001123012c", "connection": "USB Connected (hdc list targets -v)",
 "boot_id_before": b0[0], "boot_id_after": b1[0], "boot_same": b0[0] == b1[0], "uptime_s_before": float(b0[1]), "uptime_s_after": float(b1[1]),
 "lock_holder": None, "lock_note": "board_note.sh held -> rc 1, no holder; last board LOCK/UNLOCK pair 2026-10-19T17:08:39 (outer clock fix)",
 "system": {"fullname": sysl[0], "product_model": sysl[1], "api": sysl[2], "kernel": sysl[3], "selinux": sysl[4]},
 "memory_kB": {k: int(mem[k]) for k in ("MemTotal", "MemAvailable") if k in mem},
 "data_partition": {"size": data.group(1), "used": data.group(2), "avail": data.group(3), "use": data.group(4), "note": "the /data block device as listed by df via its /system/android bind mount"} if data else None,
 "process_count": len(ps) - 1,
 "host_parent_child": {"appspawn-x_running": "appspawn-x" in names, "native_appspawn_pid": next((l.split()[0] for l in ps if l.split()[5:6] == ["appspawn"]), None),
                       "note": "no appspawn-x host/parent/child process present at sample time; /system/bin/appspawn-x is bind-mounted from sda63"},
 "runtime_deploy": {"bind_mounts_seen": len(re.findall(r" on /system/(android|bin/appspawn-x|lib64/(appspawn|westlake|libwestlake))", rt("q08-mounts-runtime.stdout"))),
                    "route_a": sorted(set(re.findall(r"/system/lib64/westlake/route-a/([0-9a-f]{64})", rt("q08-mounts-runtime.stdout")))),
                    "board_runtime_fingerprint_file": "absent (/data/local/tmp/runtime-fingerprint.txt)",
                    "last_recorded_fp": {"runtime": "9745004d10ce", "bootimage": "ee927db88a67", "source": "2026-10-13 r6 smoke group-0 facts.txt (historical, NOT fresh)"}},
 "genshin_installed": "yuanshen" in rt("q06-bm-genshin.stdout").lower().replace("grep_rc", ""),
 "bundles_dump_lines": int(rt("q06-bm-genshin.stdout").split()[-1]),
 "relevant_installed": [l.strip() for l in rt("q07-bm-boat-a2hlab.stdout").splitlines() if l.strip()],
}
plan_files = ["plan/board-run-genshin-5ea.disabled.json", "plan/smoke-genshin-5ea.json", "plan/manifest-genshin.json", "plan/genshin.keys"]
plan = {
 "status": "READY_DISABLED", "execution_enabled": False,
 "entry": "python3 scripts/lab/board_run.py <plan> --detach   (from the repo root; flip execution_enabled only after outer approval)",
 "files": [repo_ref("benchmark/2026-10-21-commercial-game/spare-preflight/" + f) for f in plan_files] + [repo_ref("benchmark/2026-10-21-commercial-game/spare-preflight/tools/rollback_genshin.sh")],
 "fixed_by_board_run": ["LOCK via board_note.sh, UNLOCK in finally (lock retained if before_unlock rc!=0)", "activation_smoke gate first (fingerprints + zigzag launch-only control); FAIL stops",
                        "bms_batch --execute --reinstall --hilog --shots 5,20 per shard", "window_limit_minutes 30, stop_new_tests_by_minute 20 (=1200 s)"],
 "derived_bms_batch_argv": ["python3", "benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py", "--execute", "--serial", "5ea34a4500000000000000001123012c", "--lane", "cc-video",
                            "--manifest", "<plan/manifest-genshin.json>", "--input-root", "$HOME/.local/share/westlake/commercial-game-20261021/spare-preflight/input-root",
                            "--keys", "genshin", "--reinstall", "--hilog", "--shots", "5,20", "--out", "<out>/01-genshin", "--stop-new-keys-at", "<lock_epoch+1200>"],
 "offline_validation": ["o01-bms-batch-resolve-inputs (rc 0: APK selected by SHA, input_sha256 fe623c5b…, split_hint false, native_sidecars [])",
                        "o04-board-run-dispatch-dryrun (rc 0)", "o05-board-run-disabled-refusal (REFUSE, no lock)"],
 "rollback": "before_unlock = tools/rollback_genshin.sh 5ea…: bm uninstall -n com.miHoYo.Yuanshen, read back bm dump, rc 0 only if absent (else lock retained); no runtime/data reset needed because nothing else is written",
 "evidence_collected_in_window": ["bms_batch record.json/facts.txt (install readback, PID, alive t5/t20)", "t5/t20 screenshots with focus", "hilog reset before launch + dump after wait + new faultlogs"],
 "unknown": ["fresh runtime/bootimage fingerprints (re-derived by the smoke gate; historical values may differ -> stop)",
             "whether t20 shows Genshin first screen (board_run fixes --shots 5,20 and default --wait 15; no plan-level override)",
             "whether the BMS/APK installer extracts the 32 arm64 libs itself (no sidecars provided)",
             "whether appspawn-x starts on demand for the first Android launch after this boot (zigzag control in the smoke gate answers it first)"],
 "not_in_scope": ["login, clicks beyond launch, full content download, runtime replacement, 61b"],
}
res = {"token": "COMMERCIAL-G05", "status": "FRESH_READ_OK_PLAN_READY_DISABLED", "runtime_verdict": "NOT_TESTED", "device_writes": 0,
       "contract": "specs/commercial-game-round1/t5-spare-preflight.spec.md @ b3971d0379",
       "input": {"apk_sha256": "abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc", "package": "com.miHoYo.Yuanshen", "source": "COMMERCIAL-G03 a3c45bd667"},
       "elapsed": {"start_epoch": T0, "end_epoch": T1, "seconds": T1 - T0, "budget_seconds": 600},
       "fresh": fresh, "plan": plan,
       "limits": ["read-only hdc shell only: no lock, install, click, reboot, file write, REA; 61b untouched",
                  "6 first sample commands failed locally (zsh did not split $H; device not contacted) and are kept INVALID_LOCAL",
                  "hilog read failed (option combination); not retried"],
       "next_action": "Outer: review plan/, set execution_enabled true under the G06 contract, run board_run.py --detach from the repo root on 5ea; if the plan-level shots/wait override is wanted, Codex adds it to board_run.py first.",
       "command_receipts": rec}
json.dump(res, open(os.path.join(OUT, "results.json"), "w"), indent=1, ensure_ascii=False)
print("gen ok", T1 - T0, "s", len(rec), "receipts")
