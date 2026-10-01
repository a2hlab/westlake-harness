"""Offline recovery of the eleven assigned U8 no-first-fatal records."""

import argparse
import base64
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/lab"))
import first_fatal
import termination_events


KEYS = ["cv2-com-nbossard-packlist", "cv2-com-nononsenseapps-notepad", "fd-fennec_fdroid",
        "fd-meet", "fd-musicplayer", "fd-plus", "cv2-com-bytehamster-flowitgame",
        "cv2-com-kaajjo-libresudoku", "firefox", "ppsspp", "toutiao"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(workspaces):
    facts_path = ROOT / "benchmark/2026-10-01-b10-libart-impact/bitvector-facts.json.gz.b64"
    facts = json.loads(gzip.decompress(base64.b64decode(facts_path.read_bytes())))
    index = {row["key"]: row for row in facts["rows"]}
    sign_path = workspaces / "westlake-harness/benchmark/2026-10-01-u8-sweep/outer-signoff.json"
    sign = json.loads(sign_path.read_text())
    signed = {row["key"]: row for row in sign["keys"]}
    rows = []
    for key in KEYS:
        prior = index[key]
        source = prior["source"]
        if not any(source.startswith(run + "/") for run in sign["runs"]):
            raise ValueError("Source is not a signed sequential attempt: " + key)
        directory = workspaces / source
        record = json.loads((directory / "record.json").read_text())
        if record["package"] != prior["package"] or record["apk_sha256"] != prior["apk_sha256"]:
            raise ValueError("Record identity mismatch: " + key)
        lines = (directory / "hilog.txt").read_text(errors="replace").splitlines()
        pids = set(prior["target_pids"])
        spawn = []
        for number, line in enumerate(lines, 1):
            event = termination_events.parse(line, number)
            if event and "APPSPAWN" in event["tag"]:
                match = re.search(r"Child process:" + re.escape(prior["package"]) + r" success pid:(\d+)\b", event["message"])
                if match and int(match[1]) in pids:
                    spawn.append(dict(event, victim_pid=int(match[1])))
        if {event["victim_pid"] for event in spawn} != pids:
            raise ValueError("No exact APPSPAWN target identity: " + key)
        start = max(event["line"] for event in spawn)
        events = [event for event in termination_events.analyze(lines, pids, prior["package"]) if event["line"] >= start]
        parsed = [event for number, line in enumerate(lines, 1) if number >= start
                  and (event := first_fatal.classify.parse(line, number))]
        fatal = first_fatal.analyze(parsed, pids)
        reduced = {field: fatal.get(field) for field in ("status", "terminal")}
        root = fatal.get("root") or {}
        reduced["root"] = {field: root.get(field) for field in ("status", "method", "event", "frames")}
        terminal = next((event for event in events if event["role"] == "terminal"), None)
        waits = [event for event in events if event["role"] == "wait-result"]
        if any(event["kind"] == "java-terminal" for event in events):
            group = "java-main-threw-system-exit-1"
        elif terminal and terminal["kind"] == "native-abort":
            group = "native-hwui-abort"
        elif terminal and terminal["kind"] == "system-exit":
            group = "system-exit-" + str(terminal["value"])
        elif any(event["kind"] == "appspawn-signal" and event["value"] == 9 for event in waits):
            group = "sigkill-sender-unknown"
        else:
            group = "unknown"
        own = [event for number, line in enumerate(lines, 1) if (event := termination_events.parse(line, number))
               and event["pid"] in pids and number >= start]
        context = [event for event in own if re.search(r"Exception:|Error:|StartAbility returned|nativeStartAbility|LoadLibrary failed", event["message"])
                   and not re.search(r"IFACE|VTBL|VTLEN|COROUTINE-FIX", event["message"])][-12:]
        snapshots = []
        inputs = [directory / "hilog.txt", directory / "record.json", directory / "diagnostics.json",
                  directory / "faults-before.txt", directory / "faults-after.txt"]
        for path in sorted(directory.glob("processes-*.txt")):
            inputs.append(path)
            contents = path.read_text().splitlines()
            matches = []
            for number, line in enumerate(contents, 1):
                fields = line.split()
                if fields and fields[0].isdigit() and int(fields[0]) in pids:
                    matches.append(dict(line=number, text=line))
            snapshots.append(dict(file=path.name, sha256=sha(path), lines=len(contents), target_rows=matches))
        faults = sorted(path for path in (directory / "faultlogs").rglob("*") if path.is_file())
        inputs.extend(faults)
        before = set((directory / "faults-before.txt").read_text().splitlines())
        after = set((directory / "faults-after.txt").read_text().splitlines())
        rows.append(dict(key=key, package=prior["package"], apk_sha256=prior["apk_sha256"], source=source,
                         target_pids=sorted(pids), signed=signed[key], group=group, spawn=spawn,
                         terminal=terminal, wait_results=waits, events=events, first_fatal=reduced,
                         preceding_context=context, last_app_events=own[-6:], snapshots=snapshots,
                         faultlogs=[str(path.relative_to(directory)) for path in faults],
                         new_fault_inventory=sorted(after - before),
                         inputs={str(path.relative_to(directory)): sha(path) for path in inputs}))
    counts = Counter(row["group"] for row in rows)
    return dict(schema="u8-no-fatal-terminations-v1", target_count=len(rows),
                bindings=dict(facts_sha256=sha(facts_path), signoff_sha256=sha(sign_path),
                              signoff_source=str(sign_path.relative_to(workspaces)), state=sign["state"]),
                groups=[dict(cause=group, count=count, keys=[row["key"] for row in rows if row["group"] == group])
                        for group, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))], rows=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspaces", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    arguments.output.write_text(json.dumps(collect(arguments.workspaces.resolve()), indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
