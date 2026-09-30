#!/usr/bin/env python3
"""Find target termination first, then its exception chain or fault-thread stack."""

import argparse
from datetime import datetime
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "benchmark/2026-10-01-u5-investigate"))
import benign
import classify


NONTERMINAL_SIGNALS = {4, 35, 42}
FATAL_SIGNALS = {6, 7, 8, 9, 11, 15, 31}
EXCEPTION = re.compile(r"(?:[\w.$]+\.)[\w$]*(?:Exception|Error)(?::|\b)")
STACK = re.compile(r"^(?:at |Caused by:|Suppressed:|\.\.\. \d+ more)")


def message(event):
    return event["message"].removeprefix("[stderr] ").strip()


@lru_cache(maxsize=65536)
def seconds(timestamp):
    return datetime.strptime("2000-" + timestamp, "%Y-%m-%d %H:%M:%S.%f").timestamp()


def terminal_kind(event):
    if not classify.is_execution(event):
        return None
    text = message(event)
    if text.startswith("at "):
        return None
    if "J_invokeStaticMain_main_threw" in text:
        return "main_threw"
    if "FATAL EXCEPTION:" in text:
        return "fatal-exception"
    if re.search(r"System\.exit (?:called|invoked)|^(?:Calling |Invoking )?System\.exit\(-?\d+\)", text):
        return "system-exit"
    if "W-ROOM-SURVIVE" not in text and re.search(r"(?:uncaughtException handler invoked|Uncaught exception in thread|UNCAUGHT EXCEPTION:)", text, re.I):
        return "uncaught-handler"
    signal = re.search(r"(?:signo\(|Fatal signal |signal\()(\d+)", text)
    if signal and ("DfxSignalHandler" in event["tag"] or "Fatal signal " in text):
        number = int(signal[1])
        if number in FATAL_SIGNALS and number not in NONTERMINAL_SIGNALS:
            return "signal"
    return None


def continuation(event):
    text = message(event)
    return bool(STACK.match(text) or EXCEPTION.match(text) or "[W-ROOM-SURVIVE]" in text or "Error was captured in composition" in text)


def exception_root(events, terminal, kind):
    thread = [event for event in events if (event["pid"], event["tid"]) == (terminal["pid"], terminal["tid"])
              and classify.is_execution(event)]
    index = next(number for number, event in enumerate(thread) if event["line"] == terminal["line"])
    chain = [terminal]
    if kind in {"main_threw", "fatal-exception", "uncaught-handler"}:
        for event in thread[index + 1:]:
            if seconds(event["timestamp"]) - seconds(terminal["timestamp"]) > 2 or not continuation(event):
                break
            chain.append(event)
    else:
        prefix = []
        for event in reversed(thread[:index]):
            if seconds(terminal["timestamp"]) - seconds(event["timestamp"]) > 2 or not continuation(event):
                break
            prefix.append(event)
        chain = list(reversed(prefix)) + chain
    exceptions = []
    suppressed_indent = None
    for event in chain:
        raw = event["message"].removeprefix("[stderr] ")
        indent = len(raw) - len(raw.lstrip())
        text = message(event)
        if suppressed_indent is not None and indent < suppressed_indent:
            suppressed_indent = None
        if text.startswith("Suppressed:"):
            suppressed_indent = indent
        if suppressed_indent is None and EXCEPTION.search(text) and not text.startswith("at "):
            exceptions.append(event)
    caused = [event for event in exceptions if message(event).startswith("Caused by:")]
    cause = caused[-1] if caused else exceptions[-1] if exceptions else None
    frames = []
    if cause:
        after = False
        for event in chain:
            if event["line"] == cause["line"]:
                after = True
            elif after and message(event).startswith("at "):
                frames.append(event)
            elif after and frames:
                break
    return dict(status="linked-exception" if cause else "unknown", event=cause, frames=frames[:6], chain=chain,
                method="Caused-by-chain" if caused else "same-TID-adjacent-exception" if cause else "no-adjacent-exception")


def crash_reports(lines, source, digest):
    streams = {}
    for number, line in enumerate(lines, 1):
        event = classify.parse(line, number)
        if event:
            if "DfxFaultLogger" not in event["tag"]:
                continue
            stream = (event["pid"], event["tid"])
            content = event["message"]
        else:
            stream, content = (0, 0), line.strip()
        streams.setdefault(stream, []).append(dict(line=number, text=line, message=content))
    reports = []
    for entries in streams.values():
        report = None
        fault_thread = False
        for index, entry in enumerate(entries):
            content = entry["message"]
            pid = re.match(r"Pid:\s*(\d+)\b", content)
            if pid:
                report = dict(pid=int(pid[1]), tid=None, timestamp=None, frames=[], source=source, sha256=digest, header=entry)
                for previous in entries[max(0, index - 5):index]:
                    stamp = re.search(r"Timestamp:\d{4}-(\d\d-\d\d \d\d:\d\d:\d\d\.\d+)", previous["message"])
                    if stamp:
                        report["timestamp"] = stamp[1]
                reports.append(report)
                fault_thread = False
            elif report and content.startswith("Fault thread info:"):
                fault_thread = True
            elif report and fault_thread:
                tid = re.match(r"Tid:\s*(\d+)\b", content)
                if tid and report["tid"] is None:
                    report["tid"] = int(tid[1])
                elif re.match(r"#\d+\s+pc\s", content):
                    report["frames"].append(entry)
                elif report["frames"]:
                    fault_thread = False
    return reports


def analyze(events, pids, reports=(), disappeared=(), registry=None, context=None, cutoff=None):
    scoped = classify.scoped(events, pids, cutoff) if pids else []
    terminals = [dict(kind=kind, event=event) for event in scoped if (kind := terminal_kind(event))]
    terminals.sort(key=lambda item: (item["event"]["timestamp"], item["event"]["line"]))
    output = dict(status="no-observed-termination", target_pids=sorted(pids), terminal=None, root=None,
                  later_terminals=[], noise_context=[], context=[], limitations=[])
    if not terminals:
        if disappeared:
            output.update(status="process-disappearance-cause-unknown", terminal=dict(kind="process-disappeared", snapshots=list(disappeared)))
        return output
    chosen = terminals[0]
    terminal = chosen["event"]
    output.update(status="termination-found", terminal=chosen, later_terminals=terminals[1:])
    if chosen["kind"] == "signal":
        matches = [report for report in reports if report["pid"] == terminal["pid"] and report["tid"] == terminal["tid"]
                   and report["timestamp"] and abs(seconds(report["timestamp"]) - seconds(terminal["timestamp"])) <= 10 and report["frames"]]
        external = [report for report in matches if not report["source"].startswith("hilog.txt:")]
        matches = external or matches
        if len(matches) == 1:
            output["root"] = dict(status="fault-thread-stack", method="PID-TID-time-bound-crash-report", report=matches[0], frames=matches[0]["frames"][:6])
        else:
            output["root"] = dict(status="unknown", method="missing-or-ambiguous-crash-report", frames=[])
    else:
        output["root"] = exception_root(scoped, terminal, chosen["kind"])
    nearby = [event for event in scoped if event["pid"] == terminal["pid"] and event["tid"] == terminal["tid"]
              and abs(seconds(event["timestamp"]) - seconds(terminal["timestamp"])) <= 2 and classify.is_execution(event)]
    protected = {item["event"]["line"] for item in terminals}
    if registry and context == registry["context"]:
        _, noise = benign.partition(nearby, registry, context)
        noise = [entry for entry in noise if entry["event"]["line"] not in protected]
    else:
        noise = []
    omitted = {entry["event"]["line"] for entry in noise}
    output["noise_context"] = noise
    output["context"] = [event for event in nearby if event["line"] not in omitted][-120:]
    output["limitations"] = ["Termination-linked evidence is not proof of the earliest nonfatal startup wall or t20 UI.",
                              "Adjacent exceptions are bounded to the same PID/TID and two seconds; review remains required."]
    return output


def processes(path, uid):
    if not path.exists():
        return None
    lines = path.read_text().splitlines()
    if not lines or not {"PID", "UID"} <= set(lines[0].split()):
        return None
    header = lines[0].split()
    result = set()
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < len(header) or not parts[header.index("PID")].isdigit():
            return None
        if parts[header.index("UID")] == str(uid):
            result.add(int(parts[header.index("PID")]))
    return result


def disappearance(bindings, before, after):
    if after is None:
        return []
    observed = set(before or set()) | {event["pid"] for event in bindings}
    result = []
    for pid in sorted(observed - after):
        source = "processes-t5.txt" if before is not None and pid in before else "hilog-package-binding"
        result.append(dict(pid=pid, before=source, after="processes-t20.txt",
                           binding_lines=[event["line"] for event in bindings if event["pid"] == pid]))
    return result


def load_run(folder):
    record_path, log_path = folder / "record.json", folder / "hilog.txt"
    record = json.loads(record_path.read_text())
    raw = log_path.read_bytes() if log_path.exists() else b""
    digest = hashlib.sha256(raw).hexdigest()
    pinned = (record.get("diagnostics") or {}).get("sha256")
    if pinned and digest != pinned:
        raise ValueError("hilog changed from diagnostic receipt")
    lines = raw.decode(errors="replace").splitlines()
    events = [event for number, line in enumerate(lines, 1) if (event := classify.parse(line, number))]
    binding = [event for event in events if "nativeOnScheduleLaunchApplication ENTRY bundle=" + record["package"] + " " in event["message"]]
    pids = {event["pid"] for event in binding}
    uid = (record.get("bms") or {}).get("uid")
    snapshots = {name: processes(folder / name, uid) for name in ["processes-t5.txt", "processes-t20.txt"]} if uid else {}
    for sample in snapshots.values():
        if sample is not None:
            pids.update(sample)
    if not pids:
        pids.update(pid for pid in record.get("observed_pids", []) if type(pid) is int and pid > 0)
    before, after = snapshots.get("processes-t5.txt"), snapshots.get("processes-t20.txt")
    disappeared = disappearance(binding, before, after)
    reports = load_reports(folder, lines, digest)
    return record, events, pids, reports, disappeared, dict(record_sha256=hashlib.sha256(record_path.read_bytes()).hexdigest(),
                                                          hilog_sha256=digest, diagnostic_hash_verified=bool(pinned), binding_lines=[event["line"] for event in binding])


def load_reports(folder, lines, digest):
    reports = []
    for path in sorted((folder / "faultlogs").glob("*")):
        if path.is_file():
            payload = path.read_bytes()
            reports.extend(crash_reports(payload.decode(errors="replace").splitlines(), str(path.relative_to(folder)), hashlib.sha256(payload).hexdigest()))
    reports.extend(crash_reports(lines, "hilog.txt:DfxFaultLogger", digest))
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--registry", type=Path, default=benign.REGISTRY)
    parser.add_argument("--cutoff")
    args = parser.parse_args()
    record, events, pids, reports, disappeared, pins = load_run(args.run)
    registry = json.loads(args.registry.read_text())
    result = analyze(events, pids, reports, disappeared, registry, registry["context"], args.cutoff)
    result.update(key=record["key"], package=record["package"], source=pins,
                  noise_policy="explicit-CLI-context-trim-only; never terminal selection or root removal",
                  registry_sha256=hashlib.sha256(args.registry.read_bytes()).hexdigest())
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
