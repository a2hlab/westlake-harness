"""Generate and freeze U6-T7c/J7b predictions before the combined sweep."""

import argparse
import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from decisions import DECISIONS, decision

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
U5 = ROOT / "benchmark/2026-09-30-u4-sweep"
VERSION = "u6-t7c-j7b-v1"
OLD_CSVS = {
    "benchmark/2026-09-30-u4-sweep/J6N4-PREDICTIONS.csv": "bae8fd74ffdcba3aa5ea05688fcc0c516169f0b0cfcc29d46249c7352fc6a26d",
    "benchmark/2026-10-01-u5-feedback-v1/PREDICTIONS.csv": "97014f7146fcbe1ba5c8285cf1112a9c2653ea1f46385836d3eb3a10365ac739",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def encoded(value):
    return json.dumps(value, sort_keys=True, indent=2) + "\n"


def expected_run(candidate, facts):
    def inventory(path):
        return {line.split()[1]: line.split()[0] for line in path.read_text().splitlines() if line.strip()}
    runtime = inventory(U5 / "j6n4-scoring/evidence/runtime-fingerprint.txt")
    runtime["/system/android/framework/oh-adapter-runtime.jar"] = candidate["j7b_sha256"]
    boot = inventory(U5 / "j6n4-scoring/evidence/boot-image-fingerprint.txt")
    for path, sha in candidate["boot_files"].items():
        boot["/system/android/framework/" + path] = sha
    apps = {row["entry"]["key"]: dict(package=row["entry"]["package"],
            apk_sha256=row["selected_apk"]["sha256"],
            sidecars={item["path"]: item["sha256"] for item in row["sidecars"]}) for row in facts["apps"]}
    return dict(version=VERSION, runtime_files=runtime, boot_files=boot, apps=apps)


def check_run(expected, observed):
    if observed != expected:
        raise ValueError("U6 candidate/input identity mismatch; do not score a T7d/N5 or different-input run against this freeze")


def build():
    candidate = read(HERE / "candidate.json")
    facts = read(HERE / "input-facts.json")
    if candidate["version"] != VERSION or candidate["boot_variant"] != "T7c":
        raise ValueError("Wrong candidate version")
    prior = read(U5 / "J6N4-SCORING.json")
    fixes = read(HERE / "api-repairs.json")
    flaky = {row["key"] for row in read(HERE / "evidence/flaky-keys.json")["keys"]}
    inputs = {row["entry"]["key"]: row for row in facts["apps"]}
    if len(inputs) != 66 or set(inputs) != {row["key"] for row in prior["rows"]}:
        raise ValueError("Cohort mismatch")
    rows = []
    components = read(HERE / "evidence/component-priors.json")
    for old in prior["rows"]:
        key = old["key"]
        static = inputs[key]
        if key in flaky:
            chosen = decision("uncertain", "unknown", "Flaky first-frame result; no deterministic first-wall prediction",
                              ["J7-appwidget"] if key == "fd-uhabits" else [],
                              note="At least three same-state repetitions per side for attribution; one first attempt is not a rate")
        elif old["observed"]["own_ui"]:
            chosen = decision("retain-ui", "none", "No first-page blocking wall expected", ui="own-ui",
                              note="Preserve U5 own UI; combined U6 may still regress, this is not a new light")
        else:
            if key not in DECISIONS:
                raise ValueError("Missing reviewed prediction: " + key)
            chosen = dict(DECISIONS[key])
        if not set(chosen["fix_ids"]) <= set(fixes):
            raise ValueError("Unknown repair ID")
        if static["input_findings"]:
            chosen = {**chosen, "kind": "input-blocked", "wall_id": "input-sidecar-rejection",
                      "first_wall": "Host sidecar inventory/ELF validation still rejects; repair not physically complete",
                      "t20_prediction": "unknown", "rationale": chosen["rationale"] + "; current input findings take precedence"}
        if static["scan_errors"]:
            raise ValueError("Incomplete static input scan: " + key)
        source = U5 / "j6n4-scoring/evidence/logs" / (key + ".json")
        excerpts = read(source) if source.exists() else []
        witnesses = [row for row in excerpts if any(needle in row["text"] for needle in chosen["signature_needles"])]
        prior_refs = [dict(source="benchmark/2026-09-30-u4-sweep/J6N4-SCORING.json", key=key,
                           record_sha256=old["source"]["record_sha256"],
                           t20_sha256=old["source"].get("t20_sha256"))]
        for component, by_key in components.items():
            if key in by_key:
                prior_refs.append(dict(source="evidence/component-priors.json", component=component, key=key,
                                       log_sha256=by_key[key]["raw_sha256"]))
        rows.append(dict(version=VERSION, key=key, package=static["entry"]["package"],
                         apk_sha256=static["selected_apk"]["sha256"], candidate_sha256=digest(HERE / "candidate.json"),
                         baseline_u5_wall=chosen.pop("prior_wall") or old["current_u4_wall"],
                         baseline_label_note="Reviewed U5 correction where supplied; otherwise unchanged historical wall/UI label, not a new runtime assertion",
                         **chosen, flaky=key in flaky, input_findings=static["input_findings"],
                         static_risks=[risk["family"] for risk in static["native_and_dex_requirements"]],
                         evidence=prior_refs, u5_line_witnesses=witnesses[:6],
                         checkpoint_criterion="Require target-PID positive execution beyond each named repaired operation, not absence of the old error; installed pinned APK plus verified native inventory for input checkpoints",
                         wall_criterion="Identify the first causal startup blocker in the target PID, with same-TID exception context; signature occurrence alone or a caught background warning does not establish a first wall",
                         t20_criterion="First scheduled t20, APK/candidate-bound screenshot; outer visual review of own content vs launcher/white/black/crash. Alive/READY is not own UI. Flaky rows stay unknown for single-attempt forecasts",
                         provenance="prospective for combined U6; U5/T7c-only/J7b-only are labeled prior component evidence"))
    return dict(version=VERSION, candidate_sha256=digest(HERE / "candidate.json"),
                input_facts_sha256=digest(HERE / "input-facts.json"),
                prior_score_sha256=digest(U5 / "J6N4-SCORING.json"), rows=rows), expected_run(candidate, facts)


def csv_text(report):
    fields = ["version", "key", "package", "apk_sha256", "candidate_sha256", "baseline_u5_wall", "kind", "wall_id", "first_wall", "fix_ids", "signature_needles", "t20_prediction", "flaky", "input_categories", "static_risks", "checkpoint_criterion", "wall_criterion", "t20_criterion", "rationale"]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in report["rows"]:
        data = {key: row[key] for key in fields if key in row}
        for key in ["fix_ids", "signature_needles", "static_risks"]:
            data[key] = "; ".join(data[key])
        data["input_categories"] = "; ".join(item["category"] for item in row["input_findings"])
        writer.writerow(data)
    return stream.getvalue()


def score_reviewed(row, observation):
    result = dict(first_wall="unknown", checkpoints="unknown", t20="unknown")
    if not observation.get("identity_verified") or not observation.get("first_attempt"):
        return result
    if row["wall_id"] != "unknown" and observation.get("first_wall_confirmed"):
        result["first_wall"] = "hit" if observation.get("first_wall_id") == row["wall_id"] else "false_positive"
    required = set(row["fix_ids"])
    passed = set(observation.get("positive_crossings", []))
    failed = set(observation.get("old_wall_reproduced", []))
    if not required:
        result["checkpoints"] = "not-applicable"
    elif required & passed & failed:
        result["checkpoints"] = "unknown"
    elif required <= passed:
        result["checkpoints"] = "hit"
    elif required & failed:
        result["checkpoints"] = "false_positive"
    if not row["flaky"] and row["t20_prediction"] != "unknown" and observation.get("t20_reviewed"):
        expected = row["t20_prediction"] == "own-ui"
        if isinstance(observation.get("own_ui"), bool):
            result["t20"] = "hit" if observation["own_ui"] == expected else "false_positive"
    return result


def outputs():
    report, binding = build()
    lines = ["# U6-T7c/J7b v1 frozen first-wall forecast", "", "Component tests are prior evidence, not a completed combined U6 run. T7d/N5 are not interchangeable with this version.", "", "| key | prediction | first wall / expected crossing | repairs | t20 forecast |", "|---|---|---|---|---|"]
    for row in report["rows"]:
        lines.append(f"| {row['key']} | {row['kind']} | {row['first_wall']} | {', '.join(row['fix_ids']) or 'none'} | {row['t20_prediction']} |")
    return {"PREDICTIONS.json": encoded(report), "PREDICTIONS.csv": csv_text(report),
            "PREDICTIONS.md": "\n".join(lines) + "\n", "expected-run.json": encoded(binding)}


def verify():
    freeze = read(HERE / "FREEZE.json")
    for relative, expected in freeze["files"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError("Frozen file changed: " + relative)
    for relative, expected in OLD_CSVS.items():
        if digest(ROOT / relative) != expected:
            raise ValueError("Historical CSV changed: " + relative)
    for name, content in outputs().items():
        if (HERE / name).read_text() != content:
            raise ValueError("Forecast replay differs: " + name)
    return freeze


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--verify", action="store_true")
    group.add_argument("--check-run", type=Path)
    args = parser.parse_args()
    if args.verify or args.check_run:
        verify()
        if args.check_run:
            check_run(read(HERE / "expected-run.json"), read(args.check_run))
        print("PASS frozen U6 forecast and identity")
        return
    if (HERE / "FREEZE.json").exists():
        raise ValueError("Already frozen; create another version instead of overwriting")
    for name, content in outputs().items():
        (HERE / name).write_text(content)
    if args.freeze:
        paths = [path for path in HERE.rglob("*") if path.is_file() and path.suffix in {".py", ".json", ".csv", ".md", ".txt"} and "validation" not in path.parts and path.name not in {"README.md", "HANDOFF.md", "landing-paths.txt"}]
        freeze = dict(version=VERSION, frozen_at=datetime.now(timezone.utc).isoformat(),
                      files={str(path.relative_to(ROOT)): digest(path) for path in sorted(paths)},
                      historical_csvs=OLD_CSVS, prediction_sha256=digest(HERE / "PREDICTIONS.csv"),
                      combined_u6_outcomes_consumed=False)
        (HERE / "FREEZE.json").write_text(encoded(freeze))
        print(encoded(freeze))


if __name__ == "__main__":
    main()
