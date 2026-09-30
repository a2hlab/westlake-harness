"""Print small, line-number-preserving known-answer fixtures from retained runs."""

import json
import os
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts/lab"))
import first_fatal


CASES = {
    "n5-localsend": ("westlake-harness-bms-deploy/benchmark/2026-10-01-n5-window/runs/n5-localsend/5ea34a4500000000000000001123012c/localsend", "signal", 39057, "ANativeWindow_getFormat"),
    "j6-reader": ("westlake-harness-bms-deploy/benchmark/2026-09-30-u4-sweep/j7b-verify-5cd/baseline-j6/20261001T023258-62a98314/5cd1e3dd00000000000000000923012c/fd-reader", "main_threw", 57611, "getVibratorIds"),
    "t7c-wikipedia": ("westlake-harness-wiki/benchmark/2026-09-30-dex2oat-l2/runs/t6-61b0657200000000000000000324012c-20261001T021447/batch/t6/61b0657200000000000000000324012c/wikipedia", "system-exit", 80745, "org.ccil.cowan.tagsoup.Parser"),
    "merged-burgerking": ("westlake-harness/benchmark/2026-10-01-split-apk-inputs/board-61b/20261001T030913-2fe88b61/61b0657200000000000000000324012c/burgerking", "system-exit", 57393, "libz.so"),
    "merged-mcdonalds": ("westlake-harness/benchmark/2026-10-01-split-apk-inputs/board-61b/20261001T030913-2fe88b61/61b0657200000000000000000324012c/mcdonalds", "main_threw", 57551, "DataSourceModuleProvider.v()"),
}


def collect(workspaces):
    result = {}
    for name, (relative, kind, number, needle) in CASES.items():
        record, events, pids, reports, disappeared, pins = first_fatal.load_run(workspaces / relative)
        terminal = next(event for event in events if event["line"] == number)
        selected = [event for event in events if event["pid"] in pids and first_fatal.classify.is_execution(event)
                    and (first_fatal.terminal_kind(event) or "DfxSignalHandler" in event["tag"]
                         or (event["tid"] == terminal["tid"] and abs(first_fatal.seconds(event["timestamp"]) - first_fatal.seconds(terminal["timestamp"])) <= 2))]
        for report in reports:
            report["frames"] = report["frames"][:6]
        result[name] = dict(source_root="WORKSPACES/" + relative, source=pins, key=record["key"], package=record["package"],
                            pids=sorted(pids), lines=[[event["line"], event["text"]] for event in selected], reports=reports, disappeared=disappeared,
                            expected=dict(kind=kind, terminal_line=number, root_needle=needle),
                            authority="outer ACK95 2026-10-01T04:18:16+0800; source lines independently read")
    return result


if __name__ == "__main__":
    print(json.dumps(collect(Path(os.environ.get("WORKSPACES", HERE.parents[2]))), indent=2, ensure_ascii=False))
