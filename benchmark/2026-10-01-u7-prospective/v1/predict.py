"""Reproduce and verify the authorized U7 T7d/J7b/N4-order prediction bundle."""

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
U6 = ROOT / "benchmark/2026-10-01-u6-prospective"
SCORING = ROOT / "benchmark/2026-10-01-u6-scoring"
VERSION = "u7-t7d-j7b-n4order-v1"
FLAKY = {"antennapod", "fd-noice", "fd-notes", "fd-uhabits"}
OVERRIDES = {
    "fd-gallery": ("none", "own-ui", "Expected past MediaStore permission and file URI operations; T7d component own UI"),
    "fd-libretube": ("none", "own-ui", "Expected past tagsoup XMLReader ICCE; T7d component own UI"),
    "noice": ("none", "own-ui", "Expected SSL-adapter fallback; T7d component welcome UI"),
    "wikipedia": ("unknown", "unlit", "Expected past tagsoup/SSLSockets; component white first page, root unproven (not established Compose failure)"),
    "x": ("unknown", "unlit", "Expected past getSignalStrength; component blank at t20, XLiteActivity NPE after capture; do not backdate the later crash"),
    "fd-reader": ("unknown", "unknown", "Expected past tagsoup XMLReader ICCE; no signed combined first-page outcome beyond it"),
    "fd-seal": ("unknown", "unknown", "Expected past host sidecar rejection; runtime first wall unknown, downloader payloads still quarantined"),
    "subwaysurfers": ("unity-mediandk-load", "unlit", "Expected JNI FatalError loading libunity -> missing libmediandk.so -> SIGABRT; U5 native unchanged"),
}


def read(path):
    return json.loads(path.read_text())


def encoded(value):
    return json.dumps(value, sort_keys=True, indent=2) + "\n"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(candidate, inputs):
    prior = read(U6 / "expected-run.json")
    if candidate["runtime_files"] != prior["runtime_files"] or len(candidate["runtime_files"]) != 119:
        raise ValueError("native/runtime drift from U6")
    if candidate["stubs_sha256"] != "d8b2406eb89d2947a8cb313a471d4858ff6be86018ece3bb5c2068a11b42ca2c":
        raise ValueError("wrong full-tagsoup T7d stubs")
    replaced = dict(prior["boot_files"])
    replaced.update(candidate["replacements"])
    if len(candidate["replacements"]) != 28 or len(replaced) != 36 or replaced != candidate["boot_files"]:
        raise ValueError("invalid T7d image replacement group")
    indexed = {row["key"]: row for row in inputs["apps"]}
    if len(inputs["apps"]) != 66 or set(indexed) != set(prior["apps"]):
        raise ValueError("input cohort mismatch")
    for key, row in indexed.items():
        facts = read(HERE / "evidence/inputs" / (key + ".json"))
        if not row["resolved"] or facts["scan_errors"] or facts["input_findings"] or not facts["metadata_inventory_matches"]:
            raise ValueError("unresolved input: " + key)
        if row["apk_sha256"] != facts["selected_apk"]["sha256"] or row["metadata_sha256"] != facts["metadata_sha256"]:
            raise ValueError("input pin drift: " + key)
        if row["sidecars"] != {item["path"]: item["sha256"] for item in facts["sidecars"]}:
            raise ValueError("external sidecar identity drift: " + key)
    return indexed


def build():
    candidate, inputs = read(HERE / "candidate.json"), read(HERE / "inputs.json")
    selected = validate(candidate, inputs)
    scored = read(SCORING / "SCORING.json")
    groups = read(HERE / "repair-catalog.json")["groups"]
    priors = {row["key"]: row for row in read(HERE / "evidence/component-priors.json")["rows"]}
    rows = []
    for old in scored["rows"]:
        key = old["key"]
        observed = old["review"].get("first_wall")
        wall = observed["id"] if observed else "unknown"
        visual = old["review"].get("t20")
        ui = "own-ui" if visual and visual["visual"] == "own-ui" else "unlit" if visual else "unknown"
        description = "Expected retained terminal-linked U6 wall: " + wall if wall not in {"none", "unknown"} else "No known first-page blocker expected" if wall == "none" else "Unresolved first cause; no relevant new repair"
        wall, ui, description = OVERRIDES.get(key, (wall, ui, description))
        if key in FLAKY:
            wall, ui, description = "unknown", "unknown", "Flaky first frame; keep single-attempt first wall and t20 uncertain"
        fixes = [group["id"] for group in groups if key in group["keys"]]
        entry = selected[key]
        facts = read(HERE / "evidence/inputs" / (key + ".json"))
        refs = [dict(source="benchmark/2026-10-01-u6-scoring/evidence/u6/" + key + ".json",
                     sha256=sha(SCORING / "evidence/u6" / (key + ".json")),
                     use="U6 observation only; its strict score is not changed", lines=observed["lines"] if observed else [])]
        if key in priors:
            component = priors[key]
            refs.append(dict(source="evidence/component-priors.json", key=key, record_sha256=component["record_sha256"],
                             log_sha256=component["hilog_sha256"], use="T7d on U5 J6, not a combined U7 outcome"))
        if key == "subwaysurfers":
            refs[0]["lines"] = [58959, 58960, 58962]
        rows.append(dict(version=VERSION, key=key, package=entry["package"], apk_sha256=entry["apk_sha256"],
                         sidecar_count=len(entry["sidecars"]), metadata_sha256=entry["metadata_sha256"],
                         candidate_sha256=sha(HERE / "candidate.json"), wall_id=wall, first_wall=description,
                         fix_ids=fixes, checkpoint_prediction="expected-crossing" if fixes else "not-applicable",
                         checkpoint_criteria={group["id"]: group["positive_evidence"] for group in groups if group["id"] in fixes},
                         t20_prediction=ui, flaky=key in FLAKY, input_findings=facts["input_findings"],
                         static_risks=[item["family"] for item in facts["native_and_dex_requirements"]],
                         u6_frozen_scores_unchanged=old["scores"], evidence=refs,
                         wall_criterion="Exact candidate/input/first attempt; target-PID termination before t20 and same-TID causal chain or bound native crash stack; no earlier warning substitution. Unknown stays unknown.",
                         checkpoint_criterion="Positive execution of each named operation, not absence of error or UI alone; input checkpoints need installed APK and exact native assembly readback plus launch binding.",
                         t20_criterion="First scheduled t20 screenshot with exact hash and outer visual signoff; alive/READY is not UI; four frozen-flaky keys remain unknown on a single attempt.",
                         provenance="Prospective combined U7; signed U6 and T7d-only component windows are labeled priors, not U7 results"))
    expected = dict(version=VERSION, runtime_files=candidate["runtime_files"], boot_files=candidate["boot_files"],
                    apps={key: {name: row[name] for name in ["package", "apk_sha256", "sidecars"]} for key, row in selected.items()})
    apps = dict(schema="bms-batch-apps-v1", apps=[dict(key=key, package=row["package"], apk_sha256=row["apk_sha256"],
                 launch_activity=row["launch_activity"], **({"native_sidecar_count": len(row["sidecars"])} if row["sidecars"] else {}))
                 for key, row in selected.items()])
    report = dict(version=VERSION, combined_u7_results_consumed=False, candidate_sha256=sha(HERE / "candidate.json"),
                  input_sha256=sha(HERE / "inputs.json"), u6_score_sha256=sha(SCORING / "SCORING.json"),
                  t20_counts=dict(Counter(row["t20_prediction"] for row in rows)), rows=rows)
    return report, expected, apps


def outputs():
    report, expected, apps = build()
    fields = ["version", "key", "package", "apk_sha256", "metadata_sha256", "candidate_sha256", "sidecar_count", "wall_id", "first_wall", "fix_ids", "checkpoint_prediction", "checkpoint_criteria", "t20_prediction", "flaky", "input_findings", "static_risks", "wall_criterion", "checkpoint_criterion", "t20_criterion", "evidence"]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    lines = ["# U7 T7d/J7b/N4-order frozen predictions", "", "Component priors are not combined U7 results. Exact input/candidate identity is mandatory.", "", "| key | first wall | checkpoints | t20 |", "|---|---|---|---|"]
    for row in report["rows"]:
        writer.writerow({field: json.dumps(row[field], sort_keys=True) if isinstance(row[field], (dict, list)) else row[field] for field in fields})
        lines.append("| " + " | ".join([row["key"], row["first_wall"], ", ".join(row["fix_ids"]) or "none", row["t20_prediction"]]) + " |")
    return {"PREDICTIONS.json": encoded(report), "PREDICTIONS.csv": stream.getvalue(), "PREDICTIONS.md": "\n".join(lines) + "\n",
            "expected-run.json": encoded(expected), "apps-u7.json": encoded(apps)}


def freeze(root=HERE):
    if (root / "FREEZE.json").exists():
        raise ValueError("already frozen; create a new version")
    for name, value in outputs().items():
        if (root / name).read_text() != value:
            raise ValueError("unreproduced prediction: " + name)
    paths = [path for path in root.rglob("*") if path.is_file() and path.suffix in {".py", ".json", ".csv", ".md"}
             and path.name not in {"VALIDATION.json", "README.md"} and "__pycache__" not in path.parts]
    paths += [SCORING / "SCORING.json", SCORING / "REVIEW.json", U6 / "PREDICTIONS.csv", U6 / "FREEZE.json"]
    paths += list((SCORING / "evidence/u6").glob("*.json"))
    return dict(version=VERSION, frozen_at=datetime.now(timezone.utc).isoformat(), combined_u7_results_consumed=False,
                composition_authority="outer ACK95 2026-10-01T04:57:34+0800, expedited 05:11:24",
                prediction_sha256=sha(root / "PREDICTIONS.csv"),
                files={str(path.relative_to(ROOT)): sha(path) for path in sorted(paths)})


def verify():
    frozen = read(HERE / "FREEZE.json")
    for name, digest in frozen["files"].items():
        if sha(ROOT / name) != digest:
            raise ValueError("frozen bytes changed: " + name)
    for name, value in outputs().items():
        if (HERE / name).read_text() != value:
            raise ValueError("reproduction mismatch: " + name)
    if sha(HERE / "PREDICTIONS.csv") != frozen["prediction_sha256"]:
        raise ValueError("CSV hash mismatch")
    return frozen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--freeze-receipt", action="store_true")
    args = parser.parse_args()
    print(encoded(verify() if args.verify else freeze() if args.freeze_receipt else outputs()), end="")


if __name__ == "__main__":
    main()
