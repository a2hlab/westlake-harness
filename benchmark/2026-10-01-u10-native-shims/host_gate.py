import argparse
import json
from pathlib import Path


def validate(report, candidate=False):
    required = {"removed", "added", "drift", "consumer_breaks", "call_diffs", "old", "new"}
    if not required.issubset(report):
        raise ValueError("incomplete host ABI report")
    for field in ["removed", "added", "drift", "consumer_breaks"]:
        if report[field]:
            raise ValueError("nonzero " + field)
    expected = [{"function": "StockCreateConfiguredNamespaces", "demangled": "StockCreateConfiguredNamespaces",
                 "added_callees": ["U10ShareResidentCompat"], "removed_callees": []}] if candidate else []
    if report["call_diffs"] != expected:
        raise ValueError("changes outside the exact resident-owner publication site")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text())
    candidate = json.loads(args.candidate.read_text())
    validate(baseline)
    validate(candidate, True)
    if baseline["old"] != candidate["old"]:
        raise ValueError("different deployed host identities")
    print("U10 RESIDENT HOST GATE PASS")


if __name__ == "__main__":
    main()
