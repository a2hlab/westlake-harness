import argparse
import csv
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys


HERE = Path(__file__).resolve().parent
WORKSPACES = Path(os.environ.get("WORKSPACES", HERE.parents[3]))
BOARD = "61b0657200000000000000000324012c"
VERDICTS = {"own-content", "empty", "loading", "error", "blank", "launcher", "dead", "app_failed", "unknown"}
FACT_ROW = re.compile(r"^(\S+)\s+shots (\d+)/(\d+)\s+alive t5=(yes|no|\?)\s+t20=(yes|no|\?)\s+child_hilog=(\d+|\?)\s+(.+)$")


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tally_signoff(manifest, signoff):
    if manifest.get("schema") != "demo-baseline-manifest/v1":
        raise ValueError("wrong manifest schema")
    if signoff.get("schema") != "demo-t3-outer-signoff/v1" or signoff.get("board") != BOARD:
        raise ValueError("wrong t3 signoff schema/demo board")
    apps = manifest["apps"]
    keys = [app["key"] for app in apps]
    packages = [app["package"] for app in apps]
    if not apps or len(set(keys)) != len(keys) or len(set(packages)) != len(packages):
        raise ValueError("empty/duplicate selected key or package")
    judgments = signoff["verdicts"]
    if not isinstance(judgments, dict) or set(judgments) - set(keys):
        raise ValueError("signoff contains unknown/nonselected keys")
    allowed = {"lit", "lit_splash", "half_empty", "half_loading", "not_lit"}
    if any(value.get("verdict") not in allowed or not value.get("batch") for value in judgments.values()):
        raise ValueError("unsupported or incomplete outer verdict")
    groups = {name: [] for name in ("shown", "minimal", "errors")}
    rows = []
    for app in sorted(apps, key=lambda value: value["key"]):
        tier = app["historical_content_status"]
        if tier not in groups or app.get("counts_as_first_content") != (tier == "shown"):
            raise ValueError("inconsistent manifest content tier")
        judgment = judgments.get(app["key"])
        row = {"key": app["key"], "package": app["package"], "name": app["name_zh"],
               "historical_content_status": tier,
               "verdict": judgment["verdict"] if judgment else "pending",
               "batch": judgment["batch"] if judgment else None,
               "signed_lit": bool(judgment and judgment["verdict"] in {"lit", "lit_splash"})}
        if not judgment:
            row["reason"] = "no outer verdict in the pinned signoff; capture in progress is not signoff"
        rows.append(row)
        groups[tier].append(row)
    declared = manifest["summary"]
    expected = {"historical_first_content_packages": len(groups["shown"]),
                "pending_first_tap_packages": len(groups["minimal"]),
                "error_screen_packages": len(groups["errors"]), "distinct_packages": len(rows)}
    if any(declared.get(field) != count for field, count in expected.items()):
        raise ValueError("manifest summary/partition mismatch")
    games = manifest["signed_games"]
    if len(set(games)) != len(games) or set(games) - set(keys) or declared.get("required_signed_games") != len(games):
        raise ValueError("required-game scope mismatch")
    lookup = {row["key"]: row for row in rows}
    game_rows = [dict(lookup[key], interaction_verified=False) for key in sorted(games)]

    def counts(values):
        return {verdict: sum(row["verdict"] == verdict for row in values)
                for verdict in sorted(allowed | {"pending"})}

    tier_counts = {tier: {"total": len(values), "signed_lit": sum(row["signed_lit"] for row in values),
                          "verdict_counts": counts(values)} for tier, values in groups.items()}
    return {"schema": "demo-t3-tier-tally/v1", "execution_enabled": False, "board_access": False,
            "stability_verified": False, "board": BOARD,
            "counting_rule": "manifest tier shown AND exact outer verdict lit/lit_splash; never count empty-state tier toward first-content",
            "summary": {"selected_packages": len(rows), "signed_packages": len(judgments),
                        "pending_packages": len(rows) - len(judgments), "tiers": tier_counts,
                        "required_games": {"total": len(game_rows), "signed_lit": sum(row["signed_lit"] for row in game_rows),
                                           "verdict_counts": counts(game_rows)}},
            "first_content": {"total": len(groups["shown"]),
                              "signed_lit_keys": [row["key"] for row in groups["shown"] if row["signed_lit"]],
                              "rows": groups["shown"]},
            "empty_state": groups["minimal"], "error_screen": groups["errors"],
            "required_games": game_rows, "pending": [row for row in rows if row["verdict"] == "pending"],
            "scope_notes": ["128 canonical packages can represent 129 historical keys; aliases are not added",
                            "game verdicts are screenshot signoff only, not tap-interaction validation",
                            "not a two-round stability or post-reboot acceptance report",
                            "special_apps outside the selected manifest apps are excluded"]}


def pinned(binding, base):
    if not isinstance(binding, dict) or set(binding) != {"path", "sha256"}:
        raise ValueError("evidence requires exact path/sha256 binding")
    value = binding["path"].replace("$WORKSPACES/", str(WORKSPACES) + "/").replace("$HOME/", str(Path.home()) + "/")
    path = Path(value)
    if not path.is_absolute():
        path = base / path
    if not re.fullmatch(r"[0-9a-f]{64}", binding["sha256"] or "") or digest(path) != binding["sha256"]:
        raise ValueError("evidence SHA mismatch: " + binding["path"])
    return path


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp needs timezone")
    return parsed


def facts(path):
    rows, identity, frozen, total = {}, {}, None, None
    for line_number, line in enumerate(path.read_text(errors="backslashreplace").splitlines(), 1):
        match = FACT_ROW.fullmatch(line)
        if match:
            key, captured, slots, alive5, alive20, child, status = match.groups()
            if key in rows or int(captured) > int(slots):
                raise ValueError("duplicate/impossible facts row: " + key)
            rows[key] = {"line": line_number, "raw": line, "captured": int(captured), "slots": int(slots)}
        elif line.startswith(("RUNTIME ", "BOOTIMAGE ")):
            label = line.split()[0]
            match = re.search(r"fingerprint=([a-f0-9]{12,64})(?:\s|$)", line)
            if not match or label in identity:
                raise ValueError("missing/duplicate facts fingerprint")
            identity[label] = match.group(1)
        elif line.startswith("FROZEN "):
            match = re.search(r"violations=(\d+)(?:\s|$)", line)
            if not match or frozen is not None:
                raise ValueError("missing/duplicate frozen facts")
            frozen = int(match.group(1))
        elif line.startswith("TOTAL "):
            match = re.search(r"keys=(\d+) screenshots_captured=(\d+)/(\d+)", line)
            if not match or total is not None:
                raise ValueError("missing/duplicate facts total")
            total = tuple(map(int, match.groups()))
        elif not line.strip() or line.startswith(("TOOL ", "  ")):
            continue
        else:
            raise ValueError("unsupported facts line: " + line)
    if total != (len(rows), sum(row["captured"] for row in rows.values()), sum(row["slots"] for row in rows.values())):
        raise ValueError("facts totals incomplete or inconsistent")
    if set(identity) != {"RUNTIME", "BOOTIMAGE"} or frozen != 0:
        raise ValueError("facts identity missing or frozen violation")
    return rows, identity


def tap_map(value, base):
    if value.get("status") == "no_control":
        pinned(value["view_tree"], base)
        return dict(value, verified=False)
    if value.get("status") != "performed" or value.get("coordinate_status") != "verified-view-tree":
        raise ValueError("tap map is not a recorded view-tree action")
    if not (value.get("control_id") or value.get("control_text")):
        raise ValueError("tap map lacks control id/text")
    coordinates = value.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) != 2 or any(type(axis) is not int for axis in coordinates):
        raise ValueError("tap coordinates require two integers")
    if not (0 <= coordinates[0] < 1200 and 0 <= coordinates[1] < 1920):
        raise ValueError("tap coordinate out of bounds")
    for field in ("view_tree", "before", "after", "action_record"):
        pinned(value[field], base)
    return dict(value, verified=True)


def game_tap(value, base):
    if not value:
        return {"status": "pending-human-tap-review"}
    before, after = pinned(value["before"], base), pinned(value["after"], base)
    changed = digest(before) != digest(after)
    if value.get("human_verdict") == "changed" and not changed:
        raise ValueError("changed game verdict contradicts identical screenshots")
    return dict(value, status="pass" if changed and value.get("action") and value.get("human_verdict") == "changed" else "failed-or-unreviewed")


def observation(app, judgment, row, base, group, seen, prescreen=False):
    if judgment is None:
        return {"verdict": "unknown", "reason": "missing outer content signoff", "facts": row}
    if judgment.get("content_verdict") not in VERDICTS:
        raise ValueError(app["key"] + ": legacy lit is ambiguous; explicit content_verdict required")
    if (judgment.get("package"), judgment.get("apk_sha256")) != (app["package"], app["apk_sha256"]):
        raise ValueError(app["key"] + ": signed identity differs")
    record_path = pinned(judgment["record"], base)
    if record_path.is_symlink() or record_path.resolve() in seen:
        raise ValueError("reused/symlink candidate record")
    seen.add(record_path.resolve())
    record = read(record_path)
    if (record.get("key"), record.get("package"), record.get("apk_sha256")) != (app["key"], app["package"], app["apk_sha256"]):
        raise ValueError(app["key"] + ": candidate record identity differs")
    shots = record.get("screenshots") or []
    if (sum(bool(item.get("captured")) for item in shots), len(shots)) != (row["captured"], row["slots"]):
        raise ValueError("facts/record screenshot counts differ")
    result = {"verdict": judgment["content_verdict"], "facts": row, "record": judgment["record"]}
    if judgment.get("first_fatal"):
        pinned(judgment["first_fatal"], base)
        result["first_fatal"] = judgment["first_fatal"]
    if judgment.get("tap_map"):
        result["tap_map"] = tap_map(judgment["tap_map"], base)
        mapping = result["tap_map"]
        if mapping.get("verified"):
            before, after = pinned(mapping["before"], base), pinned(mapping["after"], base)
            if before.resolve().parent != record_path.resolve().parent or after.resolve().parent != record_path.resolve().parent:
                raise ValueError("tap map screenshots belong to another run")
            if not any(item.get("captured") and item.get("sha256") == digest(before) and Path(item["path"]).name == before.name for item in shots):
                raise ValueError("tap map before image is not a captured candidate image")
            action = read(pinned(mapping["action_record"], base))
            if (action.get("key"), action.get("package"), action.get("coordinates")) != (app["key"], app["package"], mapping["coordinates"]):
                raise ValueError("tap action record identity/coordinates differ")
    if result["verdict"] == "own-content":
        image = pinned(judgment["screenshot"], base)
        actual_phase = judgment.get("phase")
        expected_phases = {"t10", "t20"} if group == "stable" else {"t20"}
        matches = [item for item in shots if Path(item["path"]).name == image.name and item.get("captured") and item.get("sha256") == digest(image)]
        if prescreen and actual_phase == "post-tap":
            mapping = result.get("tap_map") or {}
            if not mapping.get("verified") or mapping["after"] != judgment["screenshot"]:
                raise ValueError("post-tap content lacks recorded tap map")
        elif not matches or image.resolve().parent != record_path.resolve().parent:
            raise ValueError("signed picture does not belong to candidate record")
        elif actual_phase not in expected_phases or image.stem != actual_phase or judgment.get("startup_manual_steps") != 0:
            result.update(verdict="unknown", reason="not an unaided grouped-time content observation")
        result["screenshot"] = judgment["screenshot"]
    return result


def cycle(cycle_input, apps, groups, base, seen, expected_identity, board, prescreen=False):
    found, receipts, boot, accept = {}, [], None, None
    for segment in cycle_input.get("segments") or []:
        facts_path, signoff_path = pinned(segment["facts"], base), pinned(segment["signoff"], base)
        if facts_path.resolve() in seen or signoff_path.resolve() in seen:
            raise ValueError("facts/signoff path reused")
        seen.update((facts_path.resolve(), signoff_path.resolve()))
        rows, identity = facts(facts_path)
        signed = read(signoff_path)
        if identity != expected_identity or signed.get("identity_before") != identity or signed.get("identity_after") != identity:
            raise ValueError("unified baseline drift or missing before-after identity")
        if (signed.get("schema"), signed.get("round_id"), signed.get("board"), signed.get("signer")) != (
                "demo-stability-signoff/v2", cycle_input["id"], board, "outer(claude)"):
            raise ValueError("wrong round/board or unsigned observation")
        timestamp(signed["signed_at"])
        if not signed.get("boot_id") or (boot and signed["boot_id"] != boot):
            raise ValueError("missing/inconsistent boot id")
        boot = signed["boot_id"]
        judgments = signed["keys"]
        if not set(judgments).issubset(rows):
            raise ValueError("signoff key absent from facts")
        for key, row in rows.items():
            if key not in apps or key in found:
                raise ValueError("unknown/duplicate candidate key: " + key)
            found[key] = observation(apps[key], judgments.get(key), row, signoff_path.parent, groups[key], seen, prescreen)
            found[key].update(facts_source=segment["facts"], signoff_source=segment["signoff"])
            if not prescreen and cycle_input["id"] == 3 and apps[key].get("is_game"):
                found[key]["interaction"] = game_tap((judgments.get(key) or {}).get("interaction"), signoff_path.parent)
        if not prescreen and cycle_input["id"] == 3 and signed.get("toutiao_acceptance"):
            if accept is not None:
                raise ValueError("duplicate Toutiao acceptance")
            value = signed["toutiao_acceptance"]
            log = pinned(value["stdout_stderr"], signoff_path.parent)
            passed = value.get("exit_code") == 0 and value.get("human_verdict") == "pass" and value.get("mode") == "post-reboot-live" and log.stat().st_size > 0
            passed = passed and any(Path(arg).name == "toutiao_accept.sh" for arg in value.get("argv", []))
            accept = {"status": "pass" if passed else "failed-or-unreviewed", "receipt": value}
        receipts.append(segment)
    return found, boot, accept, receipts


def summarize(path):
    document, base = read(path), path.parent
    if document.get("schema") != "demo-stability-input/v2" or document.get("board") != BOARD:
        raise ValueError("wrong input schema/demo board")
    mode = document.get("policy")
    if mode != "accelerated-61b-two-rounds":
        raise ValueError("latest policy requires exactly two 61b acceptance rounds")
    manifest_path, groups_path = pinned(document["manifest"], base), pinned(document["groups"], base)
    manifest, group_table = read(manifest_path), read(groups_path)
    selected = [row for row in manifest["apps"] if row.get("install") is True]
    apps = {row["key"]: row for row in selected}
    if not apps or len(apps) != len(selected) or len({row["package"] for row in apps.values()}) != len(apps):
        raise ValueError("empty/duplicate package manifest")
    groups = {row["key"]: row["group"] for row in group_table["apps"]}
    if len(groups) != len(group_table["apps"]) or set(groups) != set(apps) or group_table["manifest"]["sha256"] != document["manifest"]["sha256"] or set(groups.values()) - {"stable", "edge"}:
        raise ValueError("group/manifest binding or scope differs")
    for row in group_table["apps"]:
        if (row.get("package"), row.get("apk_sha256")) != (apps[row["key"]]["package"], apps[row["key"]]["apk_sha256"]):
            raise ValueError("group package/APK identity differs")
    rounds = document["rounds"]
    if [row.get("id") for row in rounds] != [1, 3] or [row.get("kind") for row in rounds] != ["t3", "post-reboot"]:
        raise ValueError("two explicit slots required: t3 round1/post-reboot round3")
    observed, round_receipts, prescreens, aborts = {}, [], {}, []
    seen = set()
    accept = {"status": "pending-post-reboot-toutiao-acceptance"}
    boots = []
    for row in rounds:
        status = row.get("status")
        if status not in {"complete", "partial", "pending", "aborted"}:
            raise ValueError("unsupported round status")
        found, boot, receipt = {}, None, None
        if status == "aborted":
            duration = (timestamp(row["aborted_at"]) - timestamp(row["reboot_requested_at"])).total_seconds()
            if row["id"] != 3 or row.get("reason") != "board-unavailable-after-reboot" or duration < 600 or row.get("board_returned") is not False:
                raise ValueError("invalid post-reboot ten-minute abort")
            pinned(row["hdc_evidence"], base)
            aborts.append({"aborted_at": row["aborted_at"], "reason": row["reason"], "hdc_evidence": row["hdc_evidence"], "requires_outer_notification": True})
        if status in {"pending", "aborted"} and row.get("segments"):
            raise ValueError("non-run slot cannot carry observations")
        if status in {"complete", "partial"}:
            if not row.get("segments") or not document.get("expected_identity"):
                raise ValueError("recorded cycle requires actual segments/identity")
            found, boot, receipt, _ = cycle(row, apps, groups, base, seen, document["expected_identity"], BOARD)
        observed[row["id"]] = found
        round_receipts.append({"id": row["id"], "status": status, "boot_id": boot, "observed_keys": sorted(found)})
        if boot:
            boots.append((row["id"], boot))
        if receipt:
            accept = receipt
    normal_boots = {boot for number, boot in boots if number < 3}
    if len(normal_boots) > 1 or (any(number == 3 for number, boot in boots) and next(boot for number, boot in boots if number == 3) in normal_boots):
        raise ValueError("wrong reboot boundary")
    for screen in document.get("prescreens", []):
        if screen.get("board") not in {"5ea", "5cd"} or not screen.get("expected_identity"):
            raise ValueError("prescreen requires independent spare-board identity")
        found, boot, receipt, _ = cycle(screen, apps, groups, base, seen, screen["expected_identity"], screen["board"], True)
        for key, value in found.items():
            prescreens.setdefault(key, []).append(dict(value, board=screen["board"], prescreen_id=screen["id"]))
    stable, unstable = [], []
    for key, app in sorted(apps.items()):
        required = [1, 3]
        values = [dict(observed[number].get(key, {"verdict": "unknown", "reason": "missing facts/signoff"}), round=number) for number in required]
        count = sum(value["verdict"] == "own-content" for value in values)
        unknown = sum(value["verdict"] == "unknown" for value in values)
        screen_values = prescreens.get(key, [])
        screen_known = [value for value in screen_values if value["verdict"] != "unknown"]
        screen_lit = sum(value["verdict"] == "own-content" for value in screen_known)
        all_fail = bool(screen_known) and not screen_lit and len(screen_known) == len(screen_values)
        included = count == len(required) and not aborts and not all_fail
        result = dict(app, group=groups[key], required_rounds=required, k=count, n=len(required),
                      k_of_n=f"{count}/{len(required)}", unknown_n=unknown, observations=values,
                      prescreen={"k": screen_lit, "n": len(screen_known), "unknown_n": len(screen_values)-len(screen_known),
                                 "all_observed_failed": all_fail, "observations": screen_values},
                      status="stable-content" if included else "unstable-or-incomplete")
        (stable if included else unstable).append(result)
    games = [{"key": row["key"], **observed[3].get(row["key"], {}).get("interaction", {"status": "pending-human-tap-review"})}
             for row in stable if row.get("is_game")]
    pending = any(row["unknown_n"] for row in stable + unstable)
    complete = not aborts and not pending and rounds[0]["status"] == rounds[1]["status"] == "complete"
    summary = {"selected_packages": len(apps), "retained_packages": len(stable), "unstable_or_incomplete": len(unstable),
               "packages_with_unknown": sum(row["unknown_n"] > 0 for row in stable + unstable), "aborted": bool(aborts),
               "all_listed_games_interactive": all(row["status"] == "pass" for row in games), "toutiao_post_reboot": accept["status"]}
    return {"schema": "demo-stability-report/v2", "execution_enabled": False, "promotion_authorized": False,
            "policy": mode, "state": "aborted" if aborts else ("complete" if complete else "incomplete"),
            "board": BOARD, "manifest": document["manifest"], "groups": document["groups"], "summary": summary,
            "rounds": round_receipts, "stable": stable, "unstable": unstable, "game_interactions": games,
            "toutiao_acceptance": accept, "aborts": aborts, "requires_outer_notification": bool(aborts),
            "release_ready_for_outer_review": complete and all(row["status"] == "pass" for row in games) and accept["status"] == "pass",
            "public_claim": "关键应用多轮验证、其余有历史多轮证据"}


def write_outputs(report, output):
    if output.exists():
        raise ValueError("fresh output directory required")
    output.mkdir(parents=True)
    for name, payload in (("stability.json", report), ("final-demo-manifest.json", {"schema": "demo-stable-set/v2",
                          "execution_enabled": False, "promotion_authorized": False, "apps": report["stable"],
                          "summary": report["summary"], "policy": report["policy"], "release_ready_for_outer_review": report["release_ready_for_outer_review"]}),
                          ("unstable.json", {"apps": report["unstable"]})):
        (output / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    with (output / "k-of-n.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        fields = ["key", "package", "group", "k", "n", "k_of_n", "unknown_n", "status"]
        writer.writerow(fields)
        for row in report["stable"] + report["unstable"]:
            writer.writerow([row[field] for field in fields])


def main():
    parser = argparse.ArgumentParser(description="Offline grouped demo stability; never invokes hdc/SSH or changes boards")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = summarize(args.input.resolve())
        write_outputs(report, args.out)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print("REJECT: " + str(error), file=sys.stderr)
        return 2
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
    if report["requires_outer_notification"]:
        print("ABORT: reboot timeout; notify outer with recorded timestamp; no silent retry", file=sys.stderr)
    return 0 if report["state"] == "complete" else 1


if __name__ == "__main__":
    sys.exit(main())
