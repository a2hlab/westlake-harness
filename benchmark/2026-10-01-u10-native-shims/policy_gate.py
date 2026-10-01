import argparse
import json
from pathlib import Path


POLICY_READER = "_ZN8westlake12nativeloader12_GLOBAL__N_19OwnPolicyILm6EEENSt3__h6vectorINS3_12basic_stringIcNS3_11char_traitsIcEENS3_9allocatorIcEEEENS8_ISA_EEEERKNS3_5arrayINS3_17basic_string_viewIcS7_EEXT_EEE"
POLICY_FUNCTIONS = {"CreateClassLoaderNamespace", "OpenNativeLibrary"}


def validate(report, candidate=False):
    required = {"removed", "added", "drift", "consumer_breaks", "call_diffs", "old", "new"}
    if not required.issubset(report):
        raise ValueError("incomplete policy ABI report")
    for field in ["removed", "added", "drift", "consumer_breaks"]:
        if report[field]:
            raise ValueError("nonzero " + field)
    differences = report["call_diffs"]
    if not candidate:
        if differences:
            raise ValueError("baseline call difference")
        return True
    if len(differences) != 2 or {row["function"] for row in differences} != POLICY_FUNCTIONS:
        raise ValueError("policy differences must be exactly the two policy readers")
    for row in differences:
        if row["removed_callees"] != [POLICY_READER] or row["added_callees"] != [POLICY_READER.replace("ILm6E", "ILm7E")]:
            raise ValueError("unexpected policy callee change")
    return True


def main():
    parser = argparse.ArgumentParser(description="Permit only the exact six-to-seven policy instantiation")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text())
    candidate = json.loads(args.candidate.read_text())
    validate(baseline)
    validate(candidate, True)
    if baseline["old"] != candidate["old"]:
        raise ValueError("different deployed loader identities")
    print("U10 POLICY GATE PASS")


if __name__ == "__main__":
    main()
