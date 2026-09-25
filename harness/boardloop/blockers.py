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
    if best is not None:
        return best["id"]
    return _family_row(category, identity, rows)


def _family_row(category: str, identity: str, rows: list[dict[str, Any]]) -> str | None:
    """Family-level fallback for maps whose rows are per-family, not per-symbol.

    The 2026-09-21 gap map aggregates: one ndk:libc-abi row for all libc ABI symbols,
    upcall:<lib>.so rows per library rather than per member. A per-symbol or per-member
    identity can never substring-match such rows, which read as unmapped even though the
    family is squarely on the map. Fallbacks map the identity to its family row; the
    returned id carries a family-level marker so downstream readers never mistake it
    for a direct row match.
    """
    ident = identity.strip()
    low = ident.lower()
    if category == "native-symbols":
        # libc/bionic ABI surface (properties, asserts, C++ runtime internals)
        if low.startswith("__system_property") or low in ("__assert",) or \
           "_znst6__ndk1" in low:
            for row in rows:
                if str(row.get("id", "")).startswith("ndk:libc-abi"):
                    return str(row["id"]) + " (family-level)"
        # NDK helpers that surface as symbols
        if ident.startswith(("AConfiguration", "ATrace_", "android_get_")):
            for row in rows:
                if str(row.get("id", "")).startswith("ndk:"):
                    return str(row["id"]) + " (family-level)"
    if category == "native-upcalls":
        # member identities look like "android.app.ActivityThread.nPurgePendingResources"
        # or "java.nio.MappedByteBuffer.load0"; the map's rows are per-.so
        if "." in ident and not ident.endswith(".so"):
            for row in rows:
                if str(row.get("id", "")).startswith("upcall:"):
                    return "upcall rows are per-.so in this map (family-level: no member row)"
    return None


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
