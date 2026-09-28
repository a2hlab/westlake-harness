#!/usr/bin/env python3
"""Fn06 canonical JSONL evidence structural replay gate.

This host tool validates provenance-independent event structure and joins. It does not
issue a device PASS; Action-specific semantic verifiers may consume its validated events.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REQUIRED = {
    "schemaVersion", "source", "bootId", "generation", "requestId",
    "seq", "monotonicNs", "kind", "payload",
}
ALLOWED_ACTIONS = {f"Fn06.A{i:02d}" for i in range(1, 8)}


def load_events(path: Path) -> list[dict]:
    events = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_no}: invalid JSON: {exc}") from exc
        missing = REQUIRED - set(item)
        if missing:
            raise ValueError(f"line {line_no}: missing fields {sorted(missing)}")
        if item["schemaVersion"] != 1:
            raise ValueError(f"line {line_no}: unsupported schemaVersion")
        if not isinstance(item["payload"], dict):
            raise ValueError(f"line {line_no}: payload must be object")
        if not all(isinstance(item[k], int) and item[k] >= 0
                   for k in ("generation", "seq", "monotonicNs")):
            raise ValueError(f"line {line_no}: generation/seq/monotonicNs must be uint")
        events.append(item)
    if not events:
        raise ValueError("event file is empty")
    return events


def validate(events: list[dict]) -> None:
    identities = Counter(
        (e["source"], e["bootId"], e["generation"], e["requestId"], e["seq"])
        for e in events
    )
    duplicates = [key for key, count in identities.items() if count != 1]
    if duplicates:
        raise ValueError(f"duplicate event identities: {duplicates[:3]}")
    by_source: dict[str, list[dict]] = {}
    for event in events:
        by_source.setdefault(str(event["source"]), []).append(event)
    if len(by_source) < 2:
        raise ValueError("at least two independent sources are required")
    for source, rows in by_source.items():
        ordered = sorted(rows, key=lambda e: (e["bootId"], e["generation"],
                                               e["requestId"], e["seq"]))
        times = [row["monotonicNs"] for row in ordered]
        if times != sorted(times):
            raise ValueError(f"source {source}: monotonicNs regressed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", required=True, choices=sorted(ALLOWED_ACTIONS))
    parser.add_argument("--events", required=True, type=Path)
    args = parser.parse_args()
    try:
        events = load_events(args.events)
        validate(events)
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"STRUCTURE_PASS action={args.action} events={len(events)} "
          f"sources={len({e['source'] for e in events})}")
    print("VERDICT_CEILING=STRUCTURAL_REPLAY_ONLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
