"""Reproduce an exploratory target shortlist and independent lit controls."""

import argparse
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts/lab"))
import scan_first_frame as scan


def read(path):
    return json.loads(path.read_text())


def build():
    data = read(HERE / "evidence/observations.json")
    review = read(HERE / "evidence/review.json")
    reviews = {row["attempt_id"]: row for row in review["rows"]}
    if len(reviews) != 78 or len(data["observations"]) != 78:
        raise ValueError("expected all 78 retained attempts and reviews")
    if {row["attempt_id"] for row in data["observations"]} != set(reviews):
        raise ValueError("review coverage changed")
    cohorts = {name: [row for row in data["observations"] if row["cohort"] == name] for name in ["u6", "t7d"]}
    if len(cohorts["u6"]) != 66 or len({row["key"] for row in cohorts["u6"]}) != 66 or len(cohorts["t7d"]) != 12:
        raise ValueError("cohort keys or retry coverage changed")
    for name, path in [("scanner_sha256", "scripts/lab/scan_first_frame.py"), ("fatal_sha256", "scripts/lab/first_fatal.py"),
                       ("parser_sha256", "benchmark/2026-10-01-u5-investigate/classify.py")]:
        if data[name] != scan.sha(ROOT / path):
            raise ValueError("replay source changed: " + path)
    rows = []
    for observed in data["observations"]:
        label = reviews[observed["attempt_id"]]
        if label["t20_sha256"] != observed["t20_sha256"]:
            raise ValueError("review capture identity changed")
        score = scan.suspicion(observed["observation"]) if observed["observation"] else None
        if score != observed["suspicion"]:
            raise ValueError("stored score differs from rule")
        rows.append(dict(attempt_id=observed["attempt_id"], key=observed["key"], package=observed["package"],
                         cohort=observed["cohort"], visual=label["visual"], target_pids=observed["target_pids"],
                         eligibility=scan.eligibility(observed, label["visual"]),
                         score=score["score"] if score else None, score_reasons=score["reasons"] if score else [],
                         counts=observed["observation"]["counts"] if observed["observation"] else None,
                         termination_status=observed["termination"]["status"],
                         foreground_confirmed=observed["screenshots_foreground_confirmed"],
                         evidence=dict(record_sha256=observed["record_sha256"], hilog_sha256=observed["hilog_sha256"],
                                       t20_sha256=observed["t20_sha256"], source=observed["source"])))
    targets = [row for row in rows if row["eligibility"] == "candidate-not-proven"]
    targets.sort(key=lambda row: (-row["score"], row["key"], row["attempt_id"]))
    keys = []
    for row in targets:
        if row["key"] not in keys:
            keys.append(row["key"])
    controls = [row for row in rows if row["visual"] == "own-ui"]
    high_controls = [row for row in controls if row["score"] is not None and row["score"] >= 20]
    return dict(rule_version=data["rule_version"], status="exploratory-rule-fails-lit-negative-controls-not-a-gate",
                source_sha256=dict(observations=scan.sha(HERE / "evidence/observations.json"), review=scan.sha(HERE / "evidence/review.json")),
                counts=dict(attempts=len(rows), u6=66, t7d=12, target_attempts=len(targets), target_keys=len(keys),
                            negative_control_attempts=len(controls), control_low_score=len(controls) - len(high_controls),
                            control_high_score_false_alarms=len(high_controls)),
                n9_target_keys=keys, targets=targets, negative_controls=controls, high_score_controls=high_controls,
                limitations=["No explicit executed present/finishDrawing markers in these logs: absence is unknown, not zero frames.",
                             "VSync request volume does not distinguish a stuck first frame from a lit animation/camera.",
                             "Target eligibility uses reviewed white images separately; it is not independent predictive accuracy.",
                             "All attempts and retries are retained; different app keys/generations are not a controlled identical-input experiment.",
                             "Target screenshot foreground gates are unconfirmed; verify surface ownership on N9, not just white image size.",
                             "No N9 deployment or expected unlock is authorized; preserve original t20 without nudge."], rows=rows)


def outputs():
    result = build()
    lines = ["# N9 first-frame investigation targets", "", "Exploratory scores failed lit negative controls; this is a target shortlist, not a detector or deploy manifest.", "",
             "Seven keys; repeated fd-noice attempts remain separate. Zero score does not rule out the symptom.", "",
             "| cohort / attempt | key | PID(s) | score | VSync request / callback | present / finishDrawing |", "|---|---|---|---:|---:|---|"]
    for row in result["targets"]:
        counts = row["counts"]
        lines.append(f"| {row['cohort']} / {row['evidence']['source'].split('/')[0]} | {row['key']} | {','.join(map(str, row['target_pids']))} | {row['score']} | {counts['vsync_request_ok']} / {counts['vsync_callback']} | unknown / unknown |")
    lines += ["", "## Lit negative controls", "", "| cohort | key | score | VSync request / callback | result at score >= 20 |", "|---|---|---:|---:|---|"]
    for row in result["negative_controls"]:
        counts = row["counts"]
        lines.append(f"| {row['cohort']} | {row['key']} | {row['score']} | {counts['vsync_request_ok']} / {counts['vsync_callback']} | {'false alarm' if row['score'] >= 20 else 'low'} |")
    lines += ["", "## Excluded reviewed-white attempts", "", "| cohort | key | exclusion |", "|---|---|---|"]
    for row in result["rows"]:
        if row["visual"] == "white" and row["eligibility"] != "candidate-not-proven":
            lines.append(f"| {row['cohort']} | {row['key']} | {row['termination_status']} |")
    lines += ["", "Raw evidence, all 78 rows, capture hashes, per-PID counts and retained retries: results.json and evidence/observations.json.", ""]
    return {"results.json": json.dumps(result, indent=2, sort_keys=True) + "\n", "N9-TARGETS.md": "\n".join(lines)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = outputs()
    if args.check:
        for name, content in rendered.items():
            if (HERE / name).read_text() != content:
                raise ValueError("report reproduction mismatch: " + name)
        print("PASS: 78 attempts, seven target keys, honest lit-control failures")
    else:
        print(json.dumps(rendered))


if __name__ == "__main__":
    main()
