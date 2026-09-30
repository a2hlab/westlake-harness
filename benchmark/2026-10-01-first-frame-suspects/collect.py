"""Collect retained U6 and T7d attempts without modifying their logs or inputs."""

import argparse
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts/lab"))
import scan_first_frame


def collect(u6, t7d):
    rows = []
    for cohort, root, pattern in [("u6", u6, "*/*/*/*/record.json"), ("t7d", t7d, "*/*/*/record.json")]:
        for path in sorted(root.glob(pattern)):
            row = scan_first_frame.extract(path.parent)
            row.update(cohort=cohort, source=str(path.parent.relative_to(root)), attempt_id=cohort + ":" + str(path.parent.relative_to(root)))
            rows.append(row)
        count = sum(row["cohort"] == cohort for row in rows)
        if count != (66 if cohort == "u6" else 12):
            raise ValueError("unexpected retained cohort: " + cohort + "=" + str(count))
    return dict(schema=1, rule_version="first-frame-suspects-v1", observations=rows,
                scanner_sha256=scan_first_frame.sha(ROOT / "scripts/lab/scan_first_frame.py"),
                fatal_sha256=scan_first_frame.sha(ROOT / "scripts/lab/first_fatal.py"),
                parser_sha256=scan_first_frame.sha(ROOT / "benchmark/2026-10-01-u5-investigate/classify.py"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspaces", type=Path, default=ROOT.parent)
    args = parser.parse_args()
    u6 = args.workspaces / "westlake-harness-bms-deploy/benchmark/2026-10-01-u6-sweep"
    candidates = list((args.workspaces / "westlake-harness-wiki/benchmark/2026-09-30-dex2oat-l2/runs").glob("*20261001T042555/batch"))
    if len(candidates) != 1:
        raise ValueError("need exact T7d retained batch")
    print(json.dumps(collect(u6, candidates[0]), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
