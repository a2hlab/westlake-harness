#!/usr/bin/env python3
"""cluster_first_cause: wrapper exceptions never become the cluster key."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cluster_first_cause as cfc


def _result(cause_msg=None, frames=(), terminal_kind="main_threw", status="termination-found", chain=()):
    terminal = {"kind": terminal_kind, "event": {"message": "term", "pid": 1, "tid": 2, "line": 10, "timestamp": "t"}}
    if status == "no-observed-termination":
        terminal = {"kind": None, "event": {}}
    root = {"status": "linked-exception" if cause_msg else "unknown"}
    if cause_msg:
        root.update(event={"message": cause_msg, "line": 20},
                    frames=[{"message": f, "line": 21 + i} for i, f in enumerate(frames)],
                    chain=list(chain))
    return {"status": status, "terminal": terminal, "root": root}


class ClusterKeyTests(unittest.TestCase):
    def test_wrapper_runtime_exception_skipped(self):
        result = _result(
            cause_msg="Caused by: java.lang.IllegalStateException: This Activity already has an action bar supplied by the window decor.",
            frames=["at androidx.appcompat.app.AppCompatDelegateImpl.setSupportActionBar(AppCompatDelegateImpl.java:552)"])
        key = cfc.cluster_key(result)
        self.assertEqual(key["kind"], "java-cause")
        self.assertIn("action bar", key["cause"])
        self.assertIn("setSupportActionBar", key["first_frame"])

    def test_pure_wrapper_message_is_still_cause_if_only_cause(self):
        # wrapper exceptions ARE skipped only as keys when a deeper cause exists;
        # if the wrapper is the innermost cause itself it still is a valid key —
        # but the exception_root already picks the innermost, so a wrapper
        # reaching us means no deeper cause. It must NOT be flattened to RuntimeException.
        result = _result(
            cause_msg="Caused by: java.lang.UnsupportedOperationException: For security reasons, WebView is not allowed in privileged processes",
            frames=["at android.webkit.WebViewFactory.getProvider(WebViewFactory.java:273)"])
        key = cfc.cluster_key(result)
        self.assertEqual(key["kind"], "java-cause")
        self.assertIn("WebView", key["cause"])

    def test_no_cause_falls_back_to_signal(self):
        result = _result(cause_msg=None, terminal_kind="signal")
        result["terminal"]["event"]["message"] = "DFX_SignalHandler :: signo(11), si_code(1), pid(1), tid(2)."
        key = cfc.cluster_key(result)
        self.assertEqual(key["kind"], "signal")
        self.assertIn("signo(11)", key["cause"])

    def test_no_termination(self):
        result = _result(cause_msg=None, status="no-observed-termination")
        key = cfc.cluster_key(result)
        self.assertEqual(key["kind"], "no-observed-termination")

    def test_cluster_groups_same_signature(self):
        results = {
            "a": _result(cause_msg="Caused by: X", frames=["at foo.Bar(Bar.java:1)"]),
            "b": _result(cause_msg="Caused by: X", frames=["at foo.Bar(Bar.java:1)"]),
            "c": _result(cause_msg="Caused by: Y", frames=["at foo.Baz(Baz.java:2)"]),
        }
        clusters = cfc.cluster(results)
        counts = {c["signature"]["cause"]: c["count"] for c in clusters}
        self.assertEqual(counts.get("X"), 2)
        self.assertEqual(counts.get("Y"), 1)
        # wrapper wrapper: a RuntimeException wrapper must never appear as cause
        self.assertNotIn("java.lang.RuntimeException: Unable to start activity", counts)


if __name__ == '__main__':
    unittest.main()
