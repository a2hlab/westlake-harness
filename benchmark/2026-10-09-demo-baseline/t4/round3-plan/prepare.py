import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
BASELINE = HERE.parents[1]
sys.path.insert(0, str(BASELINE / "t5"))
from build_seal import SERIAL, overlay_check, read_json, require


def pin(path):
    value = str(path.resolve())
    workspaces = Path(os.environ.get("WORKSPACES", BASELINE.parents[2]))
    if value.startswith(str(workspaces) + "/"):
        value = "$WORKSPACES" + value[len(str(workspaces)):]
    return {"path": value, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def build(manifest, tiers, overlays, bindings):
    require(tiers.get("schema") == "demo-shot-tiers/v1", "shot tier schema required")
    require(overlays.get("schema") == "demo-overlays/v1", "overlay schema required")
    slots = overlays.get("items", [])
    require(len(slots) == 2 and {row.get("id") for row in slots} == {"toutiao-route-b", "boatattack"}, "two overlay slots required")
    require(all(row.get("state") in {"pending", "active", "absent"} for row in slots), "invalid overlay slot state")
    ready = all(row["state"] != "pending" for row in slots)
    if ready:
        overlay_check(overlays)
    indexed = {}
    for row in tiers.get("apps", []):
        require(row["key"] not in indexed, "duplicate shot tier key")
        indexed[row["key"]] = row
    entries, packages = [], set()
    for app in manifest["apps"]:
        if not app.get("install", True):
            continue
        require(app["package"] not in packages, "duplicate manifest package")
        packages.add(app["package"])
        tier = indexed.pop(app["key"], None)
        require(tier is not None and tier["package"] == app["package"] and tier["apk_sha256"] == app["apk_sha256"],
                "shot tier identity mismatch: " + app["key"])
        require(type(tier["screenshot_seconds"]) is int and tier["screenshot_seconds"] in {10, 20}, "invalid screenshot delay")
        entries.append({"key": app["key"], "package": app["package"], "apk_sha256": app["apk_sha256"],
                        "version_code": app["version_code"], "input_root": app["input_root"],
                        "order": len(entries) + 1, "screenshot_seconds": tier["screenshot_seconds"],
                        "action": "launch-installed-only", "install": False, "uninstall": False,
                        "needs_first_tap": app.get("needs_first_tap", False), "tap": None,
                        "content_review": "pending-outer-screenshot-signoff", "game": app.get("is_game", False)})
    require(not indexed, "shot tiers include extra unselected keys")
    for row in slots:
        if row["state"] != "active":
            continue
        require(row["package"] not in packages, "overlay app duplicates manifest package")
        packages.add(row["package"])
        entries.append({"key": "toutiao" if row["id"] == "toutiao-route-b" else "BoatAttack",
                        "package": row["package"], "order": len(entries) + 1, "screenshot_seconds": 20,
                        "apk_sha256": row["apk_sha256"], "version_code": row["version_code"], "version_name": row["version_name"],
                        "overlay": row["id"], "action": "launch-existing-host-embedded" if row["id"] == "toutiao-route-b" else "launch-installed-only",
                        "launch_kind": row.get("launch_kind", "android-bms"), "host_package": row.get("host_package"), "install": False,
                        "uninstall": False, "tap": None, "content_review": "pending-outer-screenshot-signoff"})
    return {"schema": "demo-post-reboot-plan/v1", "serial": SERIAL, "lane": "cx-t0", "entry": 91,
            "round_id": 3, "kind": "post-reboot", "execution_enabled": False, "rollout_enabled": False,
            "state": "disabled-awaiting-outer-admission", "input_bindings": bindings,
            "seal_binding": None, "round1_signoff_binding": None, "outer_authorization": None,
            "before_reboot_boot_id": None, "after_reboot_boot_id": None,
            "pending": ["Outer binds final t3 signoff and final seal.json after coexistence review",
                        "cx-t0 binds production runner/smoke and per-window identity hooks before enabling",
                        "cc-t3/outer pins SAFE Route B launch/acceptance recipe; stock scripts killing appspawn-x are prohibited",
                        "Outer explicitly authorizes this demo-board reboot; generated plan never executes it"] +
                       ([] if ready else ["cc-t3/cc-wiki/outer resolve both overlay slots; regenerate before admission"]),
            "window_policy": {"limit_minutes": 45, "stop_new_keys_by_minute": 35,
                              "resume": "fresh authorized window, same post-reboot boot ID, remaining keys only; never reboot again silently"},
            "workflow": [
                {"step": 1, "action": "readonly-precheck", "requirements": ["exact 61b serial", "current seal selfcheck exit0", "final seal and input SHA pinned", "t3 all installation complete", "outer fresh reboot authorization"]},
                {"step": 2, "action": "acquire-exclusive-lock", "executor": "existing board_run / cx-t0", "checks": ["repeat readonly identity", "record boot ID before reboot"]},
                {"step": 3, "action": "reboot-once", "execution_enabled": False, "serial": SERIAL},
                {"step": 4, "action": "wait-readonly-ready", "timeout_seconds": 600, "poll_interval_seconds": 5,
                 "requirements": ["exact serial attached", "boot ID differs from before", "demo_selfcheck exit0 on effective overlays and package identities", "launcher ready and display unlocked through approved readiness checks"],
                 "no_manual_repair": True, "on_timeout": "aborted + timestamp + outer notification; retain lock until outer disposition; never pretend PASS"},
                {"step": 5, "action": "continuous-launch-and-capture", "entries": "apps", "reinstall": False,
                 "runtime_mutation": False, "automatic_taps": False, "snapshot": "snapshot_display",
                 "delay_origin": "production runner launch elapsed; fresh same-PID child/first-frame evidence retained",
                 "required_outputs": ["runner/<key>/record.json", "hilog.txt", "t10 or t20 screenshot", "facts.txt"],
                 "failure": "record first fatal/unknown and continue only while infra/identity safe; no wall fixes"},
                {"step": 6, "action": "interaction-and-toutiao-acceptance", "game_keys": [row["key"] for row in entries if row.get("game")],
                 "games": "approved actual control lookup + one action + before/after screenshot; pending without human review",
                 "empty_screens": "32 optional; no guessed coordinates; no empty/loading/error UI counted as content",
                 "toutiao": "approved SAFE Route B acceptance after reboot; no main appspawn-x kill/reinstall/runtime repair; raw output/exit + outer content review"},
                {"step": 7, "action": "readonly-final-selfcheck-and-unlock", "requirements": ["unchanged same post-reboot boot ID", "sealed effective identities exact", "retain facts/signoffs for round1+round3 k/n", "outer signs own-content screenshots"],
                 "identity_drift": "stop, retain evidence and notify outer; do not repair automatically"}
            ], "apps": entries, "overlay_slots": slots,
            "summary": {"selected_packages": len(entries), "capture_wait_seconds": sum(row["screenshot_seconds"] for row in entries),
                        "t10": sum(row["screenshot_seconds"] == 10 for row in entries),
                        "t20": sum(row["screenshot_seconds"] == 20 for row in entries), "overlays_ready": ready}}


def main():
    parser = argparse.ArgumentParser(description="Compile a disabled post-reboot plan, without device/VM transport")
    parser.add_argument("--manifest", type=Path, default=BASELINE / "demo-manifest.json")
    parser.add_argument("--tiers", type=Path, default=HERE.parent / "shot-tiers.json")
    parser.add_argument("--overlays", type=Path, default=BASELINE / "t5/overlay-inputs.json")
    parser.add_argument("--out", type=Path, default=HERE / "round3-plan.json")
    args = parser.parse_args()
    try:
        require(not args.out.exists(), "fresh output required")
        paths = {"manifest": args.manifest, "shot_tiers": args.tiers, "overlays": args.overlays}
        bindings = {name: pin(path) for name, path in paths.items()}
        tier_source = read_json(args.tiers).get("sources", [])
        require(tier_source and tier_source[0]["sha256"] == bindings["manifest"]["sha256"], "tier manifest binding differs")
        result = build(*(read_json(paths[name]) for name in ("manifest", "shot_tiers", "overlays")), bindings)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
        print(json.dumps({"status": "DISABLED_PLAN", "sha256": pin(args.out)["sha256"], **result["summary"]}))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print("REJECT " + str(error))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
