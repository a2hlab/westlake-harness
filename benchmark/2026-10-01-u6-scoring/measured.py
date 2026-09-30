"""Adapt the four outer-signed U6 shards without modifying retained runs."""

import argparse
from pathlib import Path

import score


SHARDS = {"5cd": 22, "61b": 22, "5ea": 16, "5ea-resume": 6}


def discover(root):
    selected, pins, paths = {}, {}, []
    for shard, count in SHARDS.items():
        summaries = list((root / shard).glob("*/*/summary.json"))
        if len(summaries) != 1:
            raise ValueError("need exactly one signed run summary in " + shard)
        summary_path = summaries[0]
        summary = score.read(summary_path)
        records = summary["records"]
        if len(records) != count:
            raise ValueError("signed shard cohort mismatch: " + shard)
        for filename in ["summary.json", "plan.json", "baseline.json", "facts.txt"]:
            path = summary_path.with_name(filename)
            pins[str(path.relative_to(root))] = score.sha(path)
        for record in records:
            key = record["key"]
            if key in selected:
                raise ValueError("duplicate key in signed shards: " + key)
            path = summary_path.parent / key / "record.json"
            if score.read(path) != record:
                raise ValueError("record differs from completed summary: " + key)
            selected[key] = (dict(serial=record["serial"], boot_id=record["boot_id"]),
                             dict(key=key, record=str(path.relative_to(root)), record_sha256=score.sha(path)))
        paths.extend((root / shard).glob("*/*/*/record.json"))
    if len(paths) != 66 or len(selected) != 66:
        raise ValueError("unexpected extra records or missing keys in signed run")
    return (selected, pins), paths


def prepare(root):
    indexed, paths = discover(root)
    return score.prepare(root, "u6", indexed, paths)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--template", action="store_true")
    args = parser.parse_args()
    prepared = prepare(args.source.resolve())
    result = score.score(prepared, score.read(args.review)) if args.review else score.review_template(prepared) if args.template else prepared
    print(score.encoded(result), end="")


if __name__ == "__main__":
    main()
