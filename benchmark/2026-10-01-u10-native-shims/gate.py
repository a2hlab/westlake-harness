import argparse
import json
from pathlib import Path


NEW_EXPORTS = {"android_dlopen_ext", "__gnu_strerror_r"}


def validate(report, expected_added):
    required = {"removed", "added", "drift", "consumer_breaks", "call_diffs", "old", "new"}
    if not required.issubset(report):
        raise ValueError("incomplete ABI report")
    if set(report["added"]) != set(expected_added):
        raise ValueError("unexpected export additions")
    for field in ["removed", "drift", "consumer_breaks", "call_diffs"]:
        if report[field]:
            raise ValueError("nonzero " + field)
    return True


def main():
    parser = argparse.ArgumentParser(description="Reject every ABI/call/consumer regression")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text())
    candidate = json.loads(args.candidate.read_text())
    validate(baseline, set())
    validate(candidate, NEW_EXPORTS)
    if baseline["old"] != candidate["old"]:
        raise ValueError("different deployment identities")
    if not candidate.get("consumers"):
        raise ValueError("consumer replay missing")
    print("U10 SHIM GATE PASS")


if __name__ == "__main__":
    main()
