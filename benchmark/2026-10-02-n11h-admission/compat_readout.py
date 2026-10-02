import argparse
import json
from pathlib import Path
import re

from settings import load


RULE = "knowledge/smoke/n11h-compat-readout.json"
HEADER = re.compile(r"^\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+\s+(\d+)\s+(\d+)\s+[VDIWEF]\s+[^:]+:\s*(.*)$")


def classify(lines, pid, tid=None, branch="ordinary"):
    if pid <= 0 or (tid is not None and tid <= 0) or branch not in {"ordinary", "private", "no-bridge"}:
        raise ValueError("positive known PID/TID and explicit branch required")
    rule = load(RULE)
    events, unscoped = [], []
    for number, line in enumerate(lines, 1):
        if rule["marker"] not in line:
            continue
        matched = HEADER.match(line)
        if not matched:
            unscoped.append(number)
            continue
        if int(matched[1]) != pid or (tid is not None and int(matched[2]) != tid):
            continue
        message = matched[3].split(rule["marker"], 1)[1].strip()
        kind = "malformed"
        if re.fullmatch(rule["verified_pattern"], message):
            addresses = re.findall(r"(?:abort|getter|gnu)=(0x[0-9a-fA-F]+)", message)
            if all(int(address, 16) != 0 for address in addresses):
                kind = "verified"
        elif re.fullmatch(rule["inherit_unavailable_pattern"], message):
            kind = "inherit-unavailable"
        elif any(re.fullmatch(pattern, message) for pattern in rule["unavailable_patterns"]):
            kind = "unavailable"
        events.append(dict(line=number, pid=pid, tid=int(matched[2]), kind=kind, message=message))
    kinds = {event["kind"] for event in events}
    if unscoped or "malformed" in kinds or ("verified" in kinds and "unavailable" in kinds):
        state = "MIXED_OR_MALFORMED"
    elif branch != "ordinary" and kinds:
        state = "MIXED_OR_MALFORMED"
    elif "inherit-unavailable" in kinds:
        state = "INHERIT_UNAVAILABLE"
    elif kinds == {"verified"}:
        state = "QUERY_VERIFIED"
    elif kinds == {"unavailable"}:
        state = "QUERY_UNAVAILABLE"
    else:
        state = "UNOBSERVED" if branch == "ordinary" else "SKIPPED_DECLARED_BRANCH"
    return dict(schema_version=1, device_access=False, pid=pid, tid=tid, declared_branch=branch,
                state=state, interpretation=rule["interpretation"][state], events=events,
                unscoped_marker_lines=unscoped, query_verified=state == "QUERY_VERIFIED",
                compat_success=None, relocation_success=None, smoke_verdict=None,
                smoke_failure_from_this_readout=False, exit_zero_is_not_compat_success=True)


def main():
    parser = argparse.ArgumentParser(description="Offline compat diagnostic, NOT a smoke PASS evaluator")
    parser.add_argument("--hilog", type=Path, required=True)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--tid", type=int)
    parser.add_argument("--branch", choices=["ordinary", "private", "no-bridge"], default="ordinary")
    args = parser.parse_args()
    try:
        result = classify(args.hilog.read_text(errors="replace").splitlines(), args.pid, args.tid, args.branch)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
