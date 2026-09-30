"""Compare static predictions with separately stored U5 training observations."""

import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCANNER = ROOT / "benchmark/2026-09-29-static-wall-prediction"
sys.path.insert(0, str(SCANNER))
from rules_u5_feedback import FAMILIES
from scan_u5_feedback import file_digest, write_json


def main():
    document = json.loads((HERE / "static-facts.json").read_text())
    predictions = json.loads((HERE / "PREDICTIONS.json").read_text())
    review_root = ROOT / "benchmark/2026-09-30-u4-sweep/j6n4-scoring"
    review = json.loads((review_root / "review.json").read_text())
    rows = {row["key"]: row for row in predictions["rows"]}
    known = []
    for family in review["missed_signatures"]:
        for key in family["keys"]:
            log = review_root / "evidence/logs" / (key + ".json")
            excerpt = json.loads(log.read_text())
            record = json.loads((review_root / "evidence/records" / (key + ".json")).read_text())
            witnesses = [row for row in excerpt if any(needle in row["text"] for needle in family["needles"])]
            known.append(dict(key=key, family=family["id"],
                              covered=family["id"] in {risk["family"] for risk in rows[key]["app_wall_risks"]},
                              apk_matches_u5=rows[key]["scanned_apk_sha256"] == record["apk_sha256"],
                              input_blocked=bool(rows[key]["input_findings"]),
                              log=str(log.relative_to(ROOT)), log_sha256=file_digest(log),
                              original_line_witnesses=witnesses[:8]))
    affected = {family: [row["key"] for row in predictions["rows"] if any(risk["family"] == family for risk in row["app_wall_risks"])]
                for family in FAMILIES}
    inputs = {category: [row["key"] for row in predictions["rows"] if any(item["category"] == category for item in row["input_findings"])]
              for category in ["split-key", "non-aarch64-sidecar", "apk-pin-mismatch"]}
    result = dict(version=predictions["version"], status="retrospective-training-coverage-not-accuracy",
                  cohort=len(rows), dex_members=sum(len(row["dex"]) for row in document["apps"]),
                  scan_errors={row["entry"]["key"]: row["scan_errors"] for row in document["apps"] if row["scan_errors"]},
                  risk_keys=sum(bool(row["app_wall_risks"]) for row in predictions["rows"]),
                  input_blocked_keys=sum(bool(row["input_findings"]) for row in predictions["rows"]),
                  prediction_counts=dict(collections.Counter(row["prediction"] for row in predictions["rows"])),
                  input_categories=inputs, rule_affected_keys=affected, known_misses=known,
                  known_misses_covered=sum(row["covered"] for row in known),
                  frozen_csv_sha256=predictions["frozen_csv_sha256"],
                  predictions_csv_sha256=file_digest(HERE / "PREDICTIONS.csv"),
                  predictions_json_sha256=file_digest(HERE / "PREDICTIONS.json"),
                  static_facts_sha256=file_digest(HERE / "static-facts.json"))
    write_json(HERE / "results.json", result)
    lines = ["# U5-feedback-v1 rule catalog", "", "Static risks and observed training signatures are separate. All calls/imports below are requirements, not proof of startup execution or first-wall order.", ""]
    for family, rule in FAMILIES.items():
        expected = next(item["keys"] for item in review["missed_signatures"] if item["id"] == family)
        lines.extend([f"## {family}", "", f"- Observed signature: `{rule['signature']}`.",
                      f"- Static condition: {rule['condition']}.", f"- Requirement: {rule['requirement']}.",
                      "- Known missed keys: " + ", ".join(f"`{key}`" for key in expected) + ".",
                      f"- All static matches ({len(affected[family])}): " + ", ".join(f"`{key}`" for key in affected[family]) + ".", ""])
        for key in expected:
            risk = next(item for item in rows[key]["app_wall_risks"] if item["family"] == family)
            witness = risk["evidence"][-1] if family == "private-runtime-reload" else risk["evidence"][0]
            source = (f"{witness['dex']} sha={witness['dex_sha256'][:12]} method={witness['method']} offset={witness['offset']} dexdump-line={witness['line']}"
                      if "dex" in witness else f"{witness['path']} sha={witness['sha256'][:12]}")
            observed = next(item for item in known if item["key"] == key and item["family"] == family)
            numbers = ",".join(str(item["line"]) for item in observed["original_line_witnesses"])
            lines.append(f"- `{key}`: `{source}`; original U5 log lines `{numbers}` (full witnesses in results.json).")
        lines.append("")
    lines.extend(["## Input layer", "", "| Category | Keys |", "|---|---|"])
    for category, keys in inputs.items():
        lines.append(f"| {category} | " + ", ".join(keys) + " |")
    lines.extend(["", "Subway retains both split and pin-drift flags. `noice` and `x` have null apps.json pins, resolved from metadata; null is not a mismatching pin. `fd-client` has one APK and seven DEX files: multidex is not split.", "",
                  "## Re-evaluation criterion", "", "For each risk, require the exact consumer/API signature in an APK/sidecar/generation-bound target PID. JNI and Java causal context must also share a TID. Absence of a signature is unknown, not a pass; require positive execution beyond the matching operation to show crossing. Earlier failures mask later risks. Evaluate t20 independently by the outer reviewer's actual screenshot, never from process survival. Input-blocked keys are excluded from runtime-wall scoring until their input identity is repaired and re-frozen.", ""])
    (HERE / "RULES.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
