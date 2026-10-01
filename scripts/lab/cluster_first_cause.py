#!/usr/bin/env python3
"""Cluster first_fatal results by innermost Caused-by + its first 'at' frame.

Wrapping-layer exceptions (RuntimeException 'Unable to start/resume activity',
ActivityThread performLaunch/resume frames) are skipped: the cluster key is
the innermost cause message and the first frame after it that does not come
from the wrapping stack.
"""
import json
import re
from pathlib import Path

WRAPPER_EXCEPTION = re.compile(
    r"java\.lang\.RuntimeException: Unable to (start|resume) activity|"
    r"java\.lang\.RuntimeException: Unable to instantiate (activity|application|service)|"
    r"java\.lang\.IllegalStateException: Unable to get property|"
    r"android\.app\.ActivityThread\$|"
    r"java\.lang\.IllegalArgumentException: Service not registered")


def _root_cause(result):
    root = result.get("root") or {}
    if root.get("status") != "linked-exception":
        return None, None
    event = root.get("event") or {}
    cause_msg = (event.get("message") or "").removeprefix("[stderr] ").strip()
    cause_msg = re.sub(r"^Caused by:\s*", "", cause_msg)
    frames = root.get("frames") or []
    first_frame = None
    for frame in frames:
        text = (frame.get("message") or "").removeprefix("[stderr] ").strip()
        if text.startswith("at "):
            first_frame = text
            break
    if not first_frame:
        after = False
        chain = root.get("chain") or []
        for entry in chain:
            if entry.get("line") == event.get("line"):
                after = True
                continue
            if after:
                text = (entry.get("message") or "").removeprefix("[stderr] ").strip()
                if text.startswith("at "):
                    first_frame = text
                    break
                if text and not text.startswith(("Caused by:", "Suppressed:", "... ")):
                    break
    return cause_msg, first_frame


def is_wrapper(cause_msg):
    return bool(cause_msg and WRAPPER_EXCEPTION.search(cause_msg))


def cluster_key(result):
    """(cause, frame) pair for clustering; never the wrapper exception."""
    terminal = result.get("terminal") or {}
    terminal_kind = terminal.get("kind")
    cause_msg, first_frame = _root_cause(result)
    if cause_msg and not is_wrapper(cause_msg):
        return {
            "kind": "java-cause",
            "cause": cause_msg,
            "first_frame": first_frame,
            "terminal_kind": terminal_kind,
        }
    if terminal_kind == "signal":
        event = terminal.get("event") or {}
        return {
            "kind": "signal",
            "cause": (event.get("message") or "")[:120],
            "first_frame": None,
            "terminal_kind": terminal_kind,
        }
    if terminal_kind == "system-exit":
        event = terminal.get("event") or {}
        return {
            "kind": "system-exit",
            "cause": (event.get("message") or "")[:120],
            "first_frame": None,
            "terminal_kind": terminal_kind,
        }
    if result.get("status") == "process-disappearance-cause-unknown":
        return {
            "kind": "process-disappeared",
            "cause": "process disappeared without cause",
            "first_frame": None,
            "terminal_kind": terminal_kind,
        }
    if terminal_kind is None and result.get("status") == "no-observed-termination":
        return {
            "kind": "no-observed-termination",
            "cause": "",
            "first_frame": None,
            "terminal_kind": None,
        }
    return {
        "kind": "unknown",
        "cause": cause_msg or "",
        "first_frame": first_frame,
        "terminal_kind": terminal_kind,
    }


def cluster(results_by_key):
    buckets = {}
    for key, result in results_by_key.items():
        entry = cluster_key(result)
        sig = json.dumps({k: v for k, v in entry.items() if k != "terminal_kind"}, sort_keys=True, ensure_ascii=False)
        buckets.setdefault(sig, {"signature": entry, "keys": []})["keys"].append(key)
    clusters = []
    for sig, bucket in sorted(buckets.items(), key=lambda item: (-len(item[1]["keys"]), item[0])):
        clusters.append({"signature": bucket["signature"], "count": len(bucket["keys"]), "keys": sorted(bucket["keys"])})
    return clusters


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path, help="JSON map {key: first_fatal_result}")
    args = parser.parse_args()
    data = json.loads(args.results.read_text())
    print(json.dumps(cluster(data), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
