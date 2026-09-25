"""§10.1 stage judgements P2/P3/P4a/P4b, each from its own oracle.

P2/P3 read lifecycle markers in the child log (the same markers westlake_gap.lifecycle
validated against known outcomes). P4a needs a view tree with meaningful geometry or text,
P4b needs RenderService visible nodes; both arrive as pre-parsed observations so the judgement
is testable without a board. A screenshot is never the sole evidence for any P4 stage.
"""

from __future__ import annotations

import re

#: Lifecycle markers shared with westlake_gap.lifecycle's rungs, restated as §10.1 stages.
_P2_BOUND = re.compile(r"sBindAppDone=true")
_P3_ACTIVITY = re.compile(r"DecorView|Unable to (?:start|instantiate) activity")
#: P3 failure is only an *explicit* activity-launch failure, not the word "activity" anywhere.
_P3_FAILED = re.compile(r"Unable to (?:start|instantiate) activity ComponentInfo")

PASS = "pass"
FAIL = "fail"
ORACLE_UNAVAILABLE = "oracle-unavailable"


def has_p2_marker(child_log: str) -> bool:
    """True once the bind-complete lifecycle marker has appeared in the log."""
    return _P2_BOUND.search(child_log) is not None


def p2(child_log: str) -> str:
    """P2: Application attached/created — lifecycle event and process survival."""
    return PASS if _P2_BOUND.search(child_log) else FAIL


def p3(child_log: str) -> str:
    """P3: first Activity created/resumed — activity/lifecycle trace, independent of P2."""
    if _P3_ACTIVITY.search(child_log) is None:
        return FAIL
    return FAIL if _P3_FAILED.search(child_log) else PASS


def p4a(view_tree: list[str] | None) -> str:
    """P4a: structural UI exists — populated view tree with meaningful geometry/text.

    ``view_tree`` is the parsed widget lines from the tap-channel dump; None means the oracle
    was not queried (no channel, no worker), which is oracle-unavailable rather than fail.
    """
    if view_tree is None:
        return ORACLE_UNAVAILABLE
    laid_out = [line for line in view_tree if re.search(r"rect=\[\d+,\d+ [1-9]\d*x[1-9]\d*\]", line)]
    return PASS if laid_out else FAIL


def p4b(rs_visible_nodes: int | None) -> str:
    """P4b: frame reached the compositor — RenderService visible-node count.

    ``None`` means hidumper could not be read on this board: oracle-unavailable.
    """
    if rs_visible_nodes is None:
        return ORACLE_UNAVAILABLE
    return PASS if rs_visible_nodes > 0 else FAIL


def judge(child_log: str, view_tree: list[str] | None, rs_visible_nodes: int | None) -> dict[str, str]:
    """All four stages, judged independently — a later stage never inherits an earlier verdict."""
    return {
        "P2": p2(child_log),
        "P3": p3(child_log),
        "P4a": p4a(view_tree),
        "P4b": p4b(rs_visible_nodes),
    }
