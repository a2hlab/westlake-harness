#!/usr/bin/env python3
"""Run the full spec-check suite; exceptions waive gate failures, never test verdicts."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import sys


REPO = Path(__file__).resolve().parents[2]
SELECTOR = re.compile(r"[A-Za-z_][A-Za-z0-9_:]*\Z")
TEST = re.compile(r"^test (\S+) \.\.\. (.*)$")
SUMMARY = re.compile(
    r"^test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; "
    r"(\d+) ignored; (\d+) measured; (\d+) filtered out;"
)
CATEGORIES = {"open-acceptance", "superseded-pin", "baked-path"}


def load_exceptions(path):
    registry = json.loads(Path(path).read_text())
    if not isinstance(registry, dict) or registry.get("schema_version") != 1:
        raise ValueError("invalid exception registry version")
    entries = registry.get("exceptions")
    if not isinstance(entries, list):
        raise ValueError("exceptions must be a list")
    exceptions = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("exception must be an object")
        selector = entry.get("selector")
        if not isinstance(selector, str) or not SELECTOR.fullmatch(selector):
            raise ValueError("exception requires an exact selector, not a pattern")
        if selector in exceptions:
            raise ValueError(f"duplicate exception: {selector}")
        if not isinstance(entry.get("category"), str) or entry["category"] not in CATEGORIES:
            raise ValueError(f"invalid category: {selector}")
        for field in ("reason", "removal_condition"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                raise ValueError(f"missing {field}: {selector}")
        evidence = entry.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"missing evidence: {selector}")
        for source in evidence:
            if (not isinstance(source, str) or not source.strip()
                    or Path(source).is_absolute() or ".." in Path(source).parts):
                raise ValueError(f"evidence must use repository-relative paths: {selector}")
        exceptions[selector] = entry
    return exceptions


def parse_results(stdout):
    results = {}
    totals = Counter()
    current = None
    summaries = 0
    suites = 0
    announced = 0
    for line in stdout.splitlines():
        running = re.fullmatch(r"running (\d+) tests?", line)
        if running:
            suites += 1
            announced += int(running.group(1))
        test = TEST.match(line)
        if test:
            if current is not None:
                raise ValueError(f"unfinished test: {current}")
            current, line = test.groups()
            if not SELECTOR.fullmatch(current) or current in results:
                raise ValueError(f"invalid or duplicate test: {current}")
        status = line.strip()
        if current is not None and (status in {"ok", "FAILED", "ignored"}
                                    or status.startswith("ignored, ")):
            results[current] = "ignored" if status.startswith("ignored") else status
            current = None
        summary = SUMMARY.match(line)
        if summary:
            verdict, passed, failed, ignored, measured, filtered = summary.groups()
            if current is not None or int(measured) or int(filtered):
                raise ValueError("incomplete or filtered test run")
            if (verdict == "FAILED") != (int(failed) > 0):
                raise ValueError("inconsistent test summary")
            totals.update({"ok": int(passed), "FAILED": int(failed), "ignored": int(ignored)})
            summaries += 1
    if (current is not None or not summaries or summaries != suites or not results
            or announced != len(results) or Counter(results.values()) != totals):
        raise ValueError("missing or inconsistent test results/summary")
    listed = set()
    for block in re.finditer(r"(?m)^failures:\n((?:\n|    [A-Za-z_][A-Za-z0-9_:]*\n)+)", stdout):
        listed.update(block.group(1).split())
    if listed != {name for name, status in results.items() if status == "FAILED"}:
        raise ValueError("failure list does not match test results")
    return results


def evaluate(completed, exceptions):
    results = parse_results(completed.stdout)
    failed = {name for name, status in results.items() if status == "FAILED"}
    expected_exit = 101 if failed else 0
    if completed.returncode != expected_exit:
        raise ValueError(f"unexpected Cargo exit: {completed.returncode}")
    for line in completed.stderr.splitlines():
        if line.startswith("error:") and not (
            failed and (line.startswith("error: test failed, to rerun pass ")
                        or re.fullmatch(r"error: \d+ targets? failed:", line))
        ):
            raise ValueError(f"Cargo infrastructure failure: {line}")
    messages = []
    unexpected = failed - exceptions.keys()
    unobserved = exceptions.keys() - results.keys()
    ignored = {name for name, status in results.items() if status == "ignored"}
    for selector in sorted(failed & exceptions.keys()):
        messages.append(f"EXCEPTED {selector} [{exceptions[selector]['category']}]")
    for selector in sorted(unexpected):
        messages.append(f"FAIL {selector}: not in exception registry")
    for selector in sorted(exceptions.keys() & results.keys()):
        if results[selector] == "ok":
            messages.append(f"STALE {selector}: passed; review and remove the exception")
    for selector in sorted(unobserved | ignored):
        messages.append(f"UNOBSERVED {selector}: absent or ignored, not a passing exception")
    rejected = bool(unexpected or unobserved or ignored)
    messages.append(
        f"GATE {'FAIL' if rejected else 'PASS'}: cargo_exit={completed.returncode} "
        f"passed={list(results.values()).count('ok')} failed={len(failed)} "
        f"excepted={len(failed & exceptions.keys())} unexpected={len(unexpected)}"
    )
    return int(rejected), messages


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--exceptions", type=Path)
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    registry = args.exceptions or repo / "knowledge/gates/spec-check-exceptions.json"
    try:
        exceptions = load_exceptions(registry)
        completed = subprocess.run(
            ["cargo", "test", "--color", "never", "--no-fail-fast", "--",
             "--format=pretty", "--test-threads=1"],
            cwd=repo / "tools/spec-checks", capture_output=True, text=True,
        )
        print(completed.stdout, end="")
        print(completed.stderr, end="", file=sys.stderr)
        exit_code, messages = evaluate(completed, exceptions)
        print("\n".join(messages))
        return exit_code
    except (OSError, ValueError) as error:
        print(f"GATE ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
