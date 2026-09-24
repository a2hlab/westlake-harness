"""First-blocker classification: child stderr + faultlog -> gap-map row id.

Reuses westlake_gap.lifecycle.first_blocker (log-order, not pattern-order, so an app that
crashed on one thing is not filed under another) for the child log, then folds in the device's
faultlog (cppcrash-<pid>-*) for native crashes the managed log never saw. The (category,
identity) pair is mapped onto a gap-map row id; anything unmappable is recorded `unmapped`
rather than forced onto a near miss.
"""

from __future__ import annotations

import re
from typing import Any

from westlake_gap import lifecycle

#: Native crash evidence from /data/log/faultlog/temp/cppcrash-<pid>-* — signal plus the first
#: faulting frame or abort reason, whichever the crash daemon recorded first.
_CRASH_REASON = re.compile(r"(?:Abort message|Reason):\s*'?([^\n']+)")
_CRASH_SIGNAL = re.compile(r"Signal:\s*(\w+)")


def _norm(text: str) -> str:
    return re.sub(r"\W+", " ", text).lower()


def map_to_gap_row(category: str | None, identity: str | None,
                   rows: list[dict[str, Any]]) -> str | None:
    """Map a (category, identity) blocker onto a gap-map row id, or None -> `unmapped`.

    A row claims the blocker only when its category matches and the blocker's identity names
    the row's item (either direction of containment, normalised). No match is a real result:
    forcing one would file the blocker under a gap it is not.
    """
    if not category or not identity:
        return None
    ident = _norm(identity)
    best: dict[str, Any] | None = None
    for row in rows:
        if row.get("category") != category:
            continue
        item = _norm(str(row.get("item", "")))
        if item and (item in ident or ident in item):
            if best is None or len(item) > len(_norm(str(best.get("item", "")))):
                best = row
    return best["id"] if best is not None else None


def classify(child_log: str, faultlog: str = "",
             gap_map: dict[str, Any] | None = None) -> dict[str, Any]:
    """The first uncaught exception or native crash, by evidence order.

    Child-log blockers and faultlog crashes each carry their own evidence; whichever the app
    hit first is the blocker. A native crash visible only in the faultlog outranks a later
    managed exception, because the managed report may be the app's own handler running after
    the fault (lifecycle.first_blocker's AnkiDroid caveat, applied across oracles).
    """
    category, identity = lifecycle.first_blocker(child_log)
    crash: dict[str, str] | None = None
    if faultlog:
        reason = _CRASH_REASON.search(faultlog)
        signal = _CRASH_SIGNAL.search(faultlog)
        detail = (reason.group(1).strip() if reason else None) or (
            "signal " + signal.group(1) if signal else "native crash")
        crash = {"category": "native-fault", "identity": detail}

    rows = (gap_map or {}).get("rows", [])
    blocker: dict[str, Any]
    if crash is not None and category is None:
        blocker = {"source": "faultlog", **crash}
    elif crash is not None and "native" in (category or ""):
        # Both oracles fired on the same fault; keep the faultlog's precise reason.
        blocker = {"source": "faultlog+child-log", "category": crash["category"],
                   "identity": crash["identity"]}
    elif category is not None:
        blocker = {"source": "child-log", "category": category, "identity": identity}
    else:
        blocker = {"source": "faultlog" if crash is not None else "none",
                   **(crash or {"category": None, "identity": None})}

    row_id = map_to_gap_row(blocker["category"], blocker["identity"], rows)
    return {**blocker, "gap_row": row_id if row_id is not None else (
        "unmapped" if blocker["category"] else None)}
