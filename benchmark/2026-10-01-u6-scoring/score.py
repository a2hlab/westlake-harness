"""Offline, evidence-bound intake and independent-axis U6 scoring."""

import argparse
from collections import Counter
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN = HERE.parent / "2026-10-01-u6-prospective"
sys.path.insert(0, str(FROZEN))
sys.path.insert(0, str(HERE.parent / "2026-10-01-u5-investigate"))
sys.path.insert(0, str(ROOT / "scripts/lab"))
import benign
import classify
import forecast
import first_fatal


PREDICTION_SHA = "b9a414ed0b70134e2b9dbd54be91dd843e130c5d3020acf905577e17ef419746"
INTEREST = re.compile(r"Exception|Error|FATAL|Fatal|SIGSEGV|main_threw|symbol not found|dlopen.*fail|\bat |Caused by:|\[CHILD_CK\]|\[B8-|\[ONLINE-CM\]|createSession|first-frame|SwapDmg|eglSwap|CommitAndReleaseBuffer")


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def seal(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def verify_freeze():
    if sha(FROZEN / "PREDICTIONS.csv") != PREDICTION_SHA:
        raise ValueError("wrong frozen CSV")
    for path, expected in read(FROZEN / "FREEZE.json")["files"].items():
        if sha(ROOT / path) != expected:
            raise ValueError("frozen file changed: " + path)


def within(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("evidence path escapes run root")
    return path


def inventory(path):
    result = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 2 or not re.fullmatch(r"[a-f0-9]{64}", parts[0]) or parts[1] in result:
            raise ValueError("invalid/duplicate inventory entry: " + path.name)
        result[parts[1]] = parts[0]
    return result


def app_identity(record):
    sidecars = {}
    for item in record.get("native_sidecars", []):
        name = "lib/" + item["abi"] + "/" + item["name"]
        if name in sidecars:
            raise ValueError("duplicate sidecar")
        sidecars[name] = item["sha256"]
    return dict(package=record["package"], apk_sha256=record["apk_sha256"], sidecars=sidecars)


def installed_identity(record, identity):
    assembly = record.get("native_assembly") or {}
    if (record.get("install") or {}).get("success_text") is not True:
        return False
    if not identity["sidecars"]:
        return assembly.get("status") in {"verified", "not_needed"} and not assembly.get("files")
    if assembly.get("status") != "verified" or not all(item.get("verified") is True for item in assembly.get("files", [])):
        return False
    return app_identity(dict(record, native_sidecars=assembly.get("files", []))) == identity


def noise_registry(mode, runtime, boot, registry, expected):
    if mode == "u6" and runtime == expected["runtime_files"] and boot == expected["boot_files"]:
        projected = copy.deepcopy(registry)
        projected["context"] = dict(generation="U6", expected_run_sha256=sha(FROZEN / "expected-run.json"))
        return projected, "outer-ACK95-04:05-authorized-U5-to-frozen-U6-triage"
    baseline = ROOT / "benchmark/2026-09-30-u4-sweep/j6n4-scoring/evidence"
    if mode == "rehearsal" and runtime == inventory(baseline / "runtime-fingerprint.txt") and boot == inventory(baseline / "boot-image-fingerprint.txt"):
        return registry, "U5-baseline-rehearsal"
    return None, "disabled-candidate-mismatch"


def triage(events, pids, cutoff, registry):
    if not pids:
        return [], []
    scoped = [event for event in classify.scoped(events, pids, cutoff) if classify.is_execution(event)]
    kept, noise = benign.partition(scoped, registry, registry["context"]) if registry else (scoped, [])
    protected = [entry["event"] for entry in noise if first_fatal.terminal_kind(entry["event"])]
    kept = sorted(kept + protected, key=lambda event: event["line"])
    noise = [entry for entry in noise if not first_fatal.terminal_kind(entry["event"])]
    return kept, noise


def prepare(root, mode, indexed=None, attempt_paths=None):
    verify_freeze()
    expected = read(FROZEN / "expected-run.json")
    registry = read(benign.REGISTRY)
    selected, indices = indexed if indexed is not None else ({}, {})
    for path in sorted(root.glob("index-*.json")) if indexed is None else []:
        index = read(path)
        indices[path.name] = sha(path)
        for item in index["selected"]:
            if item["key"] in selected:
                raise ValueError("duplicate selected key: " + item["key"])
            selected[item["key"]] = (index, item)
    if set(selected) != set(expected["apps"]):
        raise ValueError("incomplete or unexpected cohort; need all 66 selected keys")
    attempts = {}
    for path in attempt_paths if attempt_paths is not None else (root / "runs").glob("*/*/*/record.json"):
        record = read(path)
        if record.get("clicked_at"):
            attempts.setdefault(record["key"], []).append((record["clicked_at"], path.resolve()))
    rows = []
    frozen_time = datetime.fromisoformat(read(FROZEN / "FREEZE.json")["frozen_at"]).timestamp()
    for key, (index, item) in sorted(selected.items()):
        path = within(root, item["record"])
        if sha(path) != item["record_sha256"]:
            raise ValueError("indexed record changed: " + key)
        record = read(path)
        if record["key"] != key or record["serial"] != index["serial"] or record["boot_id"] != index["boot_id"]:
            raise ValueError("index/record identity mismatch: " + key)
        clicked = attempts.get(key, [])
        first = bool(clicked) and min(clicked)[1] == path
        if clicked and not first:
            raise ValueError("selected retry instead of first attempt: " + key)
        runtime_path = path.parent.parent / "runtime-fingerprint.txt"
        boot_path = path.parent.parent / "boot-image-fingerprint.txt"
        runtime, boot = inventory(runtime_path), inventory(boot_path)
        runtime_ok = runtime == expected["runtime_files"] and boot == expected["boot_files"]
        applied_registry, policy = noise_registry(mode, runtime, boot, registry, expected)
        identity = app_identity(record)
        input_ok = identity == expected["apps"][key]
        log_path = path.parent / "hilog.txt"
        log_sha = sha(log_path) if log_path.exists() else None
        if log_sha and log_sha != (record.get("diagnostics") or {}).get("sha256"):
            raise ValueError("diagnostic log changed or not bound: " + key)
        log_lines = log_path.read_text(errors="replace").splitlines() if log_sha else []
        events = [event for number, line in enumerate(log_lines, 1)
                  if (event := classify.parse(line, number))] if log_sha else []
        binding = [event for event in events if "nativeOnScheduleLaunchApplication ENTRY bundle=" + record["package"] + " " in event["message"]]
        pids = {event["pid"] for event in binding}
        uid = (record.get("bms") or {}).get("uid")
        snapshots = {name: first_fatal.processes(path.parent / name, uid) for name in ["processes-t5.txt", "processes-t20.txt"]} if uid else {}
        for sample in snapshots.values():
            if sample is not None:
                pids.update(sample)
        before, after = snapshots.get("processes-t5.txt"), snapshots.get("processes-t20.txt")
        disappeared = first_fatal.disappearance(binding, before, after)
        shots = [shot for shot in record.get("screenshots", []) if shot.get("scheduled_seconds") == 20 and shot.get("captured")]
        if len(shots) > 1:
            raise ValueError("ambiguous t20: " + key)
        shot = shots[0] if shots else None
        image_path = path.parent / "t20.jpeg"
        cutoff = None
        if shot:
            if sha(image_path) != shot["sha256"]:
                raise ValueError("t20 image changed: " + key)
            if shot.get("remote_stat"):
                cutoff = datetime.fromtimestamp(int(shot["remote_stat"].split()[1]), timezone(timedelta(hours=8))).strftime("%m-%d %H:%M:%S") + ".999"
        kept, noise = triage(events, pids, cutoff, applied_registry)
        reports = first_fatal.load_reports(path.parent, log_lines, log_sha)
        termination = first_fatal.analyze(events, pids, reports, disappeared=disappeared, registry=applied_registry,
                                          context=applied_registry["context"] if applied_registry else None, cutoff=cutoff)
        installed = installed_identity(record, identity)
        issues = []
        for ok, issue in [(runtime_ok, "candidate-mismatch"), (input_ok, "input-mismatch"), (first, "no-timed-first-attempt"),
                          (installed, "installation-unverified"), (bool(pids), "no-target-pid-binding"),
                          (bool(log_sha), "no-log"), (bool(cutoff), "no-t20-time-bound")]:
            if not ok:
                issues.append(issue)
        after_freeze = bool(record.get("clicked_at", 0) > frozen_time)
        if mode == "u6" and not after_freeze:
            issues.append("not-after-freeze")
        rows.append(dict(key=key, record=item["record"], record_sha256=sha(path), log=str(log_path.relative_to(root)),
                         log_sha256=log_sha, runtime_sha256=sha(runtime_path), boot_sha256=sha(boot_path),
                         runtime_count=len(runtime), boot_count=len(boot), first_attempt=first,
                         identity=identity, input_comparable=input_ok, candidate_comparable=runtime_ok,
                         identity_verified=mode == "u6" and runtime_ok and input_ok and installed and after_freeze,
                         issues=issues, target_pids=sorted(pids), binding_lines=[event["line"] for event in binding],
                         process_snapshots_sha256={name: sha(path.parent / name) for name in snapshots if (path.parent / name).exists()},
                         log_complete=bool((record.get("diagnostics") or {}).get("complete")), cutoff=cutoff,
                         t20_sha256=shot["sha256"] if shot else None,
                         t20_path=str(image_path.relative_to(root)) if shot else None,
                         t20_elapsed_seconds=shot.get("elapsed_seconds") if shot else None,
                         noise_policy=policy, noise=noise,
                         termination=termination,
                         fatal=[item["event"] for item in ([termination["terminal"]] if termination["terminal"] else []) + termination["later_terminals"] if item.get("event")],
                         candidates=[event for event in kept if INTEREST.search(event["message"])],
                         allowed_evidence_lines=[event["line"] for event in kept]))
    return dict(schema_version=1, mode=mode, status="review-required" if mode == "u6" else "structure-only-not-U6-results",
                prediction_sha256=PREDICTION_SHA, registry_sha256=sha(benign.REGISTRY), indices=indices,
                cohort=len(rows), rows=rows)


def review_template(prepared):
    return dict(prepared_sha256=seal(prepared), outer_signoff=None, complete=False,
                rows=[dict(key=row["key"], record_sha256=row["record_sha256"], log_sha256=row["log_sha256"],
                           first_wall=None, checkpoints=[], t20=None) for row in prepared["rows"]])


def checked_lines(claim, row):
    lines = claim.get("lines", [])
    if not lines or any(type(line) is not int or line not in row["allowed_evidence_lines"] for line in lines):
        raise ValueError("claim cites absent, foreign, noise or post-capture log lines: " + row["key"])
    if not claim.get("rationale"):
        raise ValueError("reviewed evidence needs rationale: " + row["key"])


def observation(row, review):
    if review["record_sha256"] != row["record_sha256"] or review["log_sha256"] != row["log_sha256"]:
        raise ValueError("review is not bound to selected record/log")
    result = dict(identity_verified=row["identity_verified"], first_attempt=row["first_attempt"],
                  positive_crossings=[], old_wall_reproduced=[])
    wall = review.get("first_wall")
    if wall:
        checked_lines(wall, row)
        if not wall.get("id") or wall["id"] == "unknown":
            raise ValueError("confirmed first wall needs an ID")
        if wall["id"] == "none" and row["termination"]["terminal"]:
            raise ValueError("no-wall claim conflicts with terminal target failure")
        if wall["id"] != "none" and row["termination"]["terminal"]:
            terminal_line = row["termination"]["terminal"].get("event", {}).get("line")
            if terminal_line not in wall["lines"]:
                raise ValueError("fatal wall review must cite the selected termination, not just an earlier error")
        if row["cutoff"] and row["log_complete"]:
            result.update(first_wall_confirmed=True, first_wall_id=wall["id"])
    for checkpoint in review.get("checkpoints", []):
        checked_lines(checkpoint, row)
        field = {"crossed": "positive_crossings", "old-wall-reproduced": "old_wall_reproduced"}.get(checkpoint.get("outcome"))
        if not field:
            raise ValueError("checkpoint outcome must be positive crossing or reproduced old wall")
        if row["cutoff"] and row["log_complete"]:
            result[field].append(checkpoint["fix_id"])
    shot = review.get("t20")
    if shot:
        if not row["t20_sha256"] or shot.get("sha256") != row["t20_sha256"] or not shot.get("description"):
            raise ValueError("outer screenshot review is unbound")
        if shot.get("visual") not in {"own-ui", "not-own-ui", "white", "black", "desktop", "crash"}:
            raise ValueError("unknown visual review category")
        result.update(t20_reviewed=True, own_ui=shot["visual"] == "own-ui")
    return result


def score(prepared, reviewed):
    verify_freeze()
    if prepared["mode"] != "u6" or prepared["prediction_sha256"] != PREDICTION_SHA:
        raise ValueError("rehearsal cannot be scored as U6")
    if not reviewed.get("complete") or not reviewed.get("outer_signoff") or reviewed.get("prepared_sha256") != seal(prepared):
        raise ValueError("need complete outer signoff bound to prepared evidence")
    predictions = {row["key"]: row for row in read(FROZEN / "PREDICTIONS.json")["rows"]}
    observations = {row["key"]: row for row in prepared["rows"]}
    reviews = {row["key"]: row for row in reviewed["rows"]}
    if len(observations) != len(prepared["rows"]) or len(reviews) != len(reviewed["rows"]) or set(observations) != set(predictions) or set(reviews) != set(predictions):
        raise ValueError("need exactly 66 unique reviewed keys")
    rows = []
    for key, prediction in predictions.items():
        row, review = observations[key], reviews[key]
        if any(item["fix_id"] not in prediction["fix_ids"] for item in review.get("checkpoints", [])):
            raise ValueError("checkpoint not in frozen row: " + key)
        observed = observation(row, review)
        rows.append(dict(key=key, scores=forecast.score_reviewed(prediction, observed),
                         observation=observed, review=review, issues=row["issues"]))
    return dict(status="outer-reviewed-U6", prediction_sha256=PREDICTION_SHA, prepared_sha256=seal(prepared),
                review_sha256=seal(reviewed), outer_signoff=reviewed["outer_signoff"],
                counts={axis: dict(Counter(row["scores"][axis] for row in rows)) for axis in ["first_wall", "checkpoints", "t20"]}, rows=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--mode", choices=["rehearsal", "u6"], required=True)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--template", action="store_true")
    args = parser.parse_args()
    prepared = prepare(args.source.resolve(), args.mode)
    result = score(prepared, read(args.review)) if args.review else review_template(prepared) if args.template else prepared
    print(encoded(result), end="")


if __name__ == "__main__":
    main()
