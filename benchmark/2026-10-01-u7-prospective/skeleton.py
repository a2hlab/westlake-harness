"""Reproduce an unfrozen cohort; never write a forecast or accept device evidence."""

import argparse
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
U6 = HERE.parent / "2026-10-01-u6-prospective"
U6_CSV_SHA256 = "b9a414ed0b70134e2b9dbd54be91dd843e130c5d3020acf905577e17ef419746"


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_priors():
    if digest(U6 / "PREDICTIONS.csv") != U6_CSV_SHA256:
        raise ValueError("U6 frozen CSV changed")
    freeze = read(U6 / "FREEZE.json")
    for relative, expected in freeze["files"].items():
        if digest(HERE.parents[1] / relative) != expected:
            raise ValueError("U6 frozen evidence changed: " + relative)
    for source in read(HERE / "evidence/source-priors.json")["sources"]:
        lines = source["lines"]
        if [entry["line"] for entry in lines] != list(range(1, len(lines) + 1)):
            raise ValueError("source line sequence changed")
        content = "\n".join(entry["text"] for entry in lines) + "\n"
        if hashlib.sha256(content.encode()).hexdigest() != source["sha256"]:
            raise ValueError("source snapshot changed")
    return freeze


def build():
    verify_priors()
    catalog = read(HERE / "repair-catalog.json")
    groups = catalog["t7d"]["groups"]
    rows = []
    for prior in read(U6 / "PREDICTIONS.json")["rows"]:
        key = prior["key"]
        repairs = [group["id"] for group in groups if key in group["keys"]]
        if key in catalog["n6"]["keys"]:
            repairs.append(catalog["n6"]["id"])
        rows.append({
            "key": key,
            "package": prior["package"],
            "status": "draft-not-frozen",
            "u6_reference_only": {
                "apk_sha256": prior["apk_sha256"],
                "projected_wall": prior["first_wall"],
                "projected_t20": prior["t20_prediction"],
                "input_findings": prior["input_findings"],
                "flaky": prior["flaky"],
            },
            "u6_measured_first_wall": None,
            "u6_score": {"first_wall": "pending", "checkpoints": "pending", "t20": "pending"},
            "candidate_repair_ids": repairs,
            "u7_input_identity": None,
            "u7_first_wall_prediction": None,
            "u7_checkpoint_predictions": None,
            "u7_t20_prediction": None,
            "criteria": {
                "first_wall": "First scheduled attempt, exact composed generation and input; target-PID causal fatal attribution, not nearest warning. Host input rejection is a separate pre-launch wall.",
                "checkpoints": "Positive execution beyond EACH named operation; missing old errors, masked paths and exports alone are not success. See repair-catalog.json for per-operation evidence.",
                "t20": "First scheduled t20 image, exact input/run, outer signed own-content review; alive/READY and component tests are not combined U7 success. Flaky remains explicit.",
            },
            "pending": ["U6 full measured run and outer signoff", "T7d/N6 board results", "final U7 composition and input revalidation"],
        })
    return {
        "schema_version": 1,
        "version": "u7-skeleton-v0",
        "status": "draft-not-frozen",
        "u6_csv_sha256": U6_CSV_SHA256,
        "u6_json_sha256": digest(U6 / "PREDICTIONS.json"),
        "catalog_sha256": digest(HERE / "repair-catalog.json"),
        "source_priors_sha256": digest(HERE / "evidence/source-priors.json"),
        "rows": rows,
    }


def readiness(intake):
    required = read(HERE / "intake.json")
    missing = []
    for section in ("u6_scoring", "u7_prediction"):
        values = intake.get(section, {})
        if not isinstance(values, dict):
            values = {}
        for name in required[section]:
            receipt = values.get(name)
            if not isinstance(receipt, dict) or not receipt.get("evidence") or not receipt.get("reviewer"):
                missing.append(section + "." + name)
    return {"missing": missing, "ready_for_evidence_review": not missing, "freeze_authorized": False,
            "note": "Checklist completeness only; evidence content and bindings require review. No freeze operation exists here."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--readiness", action="store_true")
    args = parser.parse_args()
    if args.check:
        if read(HERE / "SKELETON.json") != build():
            raise ValueError("draft reproduction mismatch")
        if (HERE / "PREDICTIONS.csv").exists() or (HERE / "FREEZE.json").exists():
            raise ValueError("unexpected frozen output in skeleton")
        print("PASS: 66-key unfrozen skeleton reproduces")
    if args.readiness:
        result = readiness(read(HERE / "intake.json"))
        print(json.dumps(result, indent=2))
        return 2 if result["missing"] else 0
    if not args.check:
        print(json.dumps(build(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
