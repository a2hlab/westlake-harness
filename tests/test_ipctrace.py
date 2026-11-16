from __future__ import annotations

import unittest

from westlake_gap.ipctrace import classify_trace, join_gap_map, observe, parse_dump

# Shape of `am trace-ipc stop --dump-file` on Android 16 (frames trimmed): one app-initiated AIDL call,
# one call the framework makes during resume with no app frame, a Settings read through the
# hand-written ContentProviderProxy, and another process that must not leak into the app's rows.
DUMP = """Binder transaction traces for all processes.

Traces for process: system
Count: 1
Trace: java.lang.Throwable
\tat android.os.BinderProxy.transact(BinderProxy.java:568)
\tat com.android.internal.statusbar.IStatusBar$Stub$Proxy.setTopAppHidesStatusBar(IStatusBar.java:2053)
\tat com.android.server.wm.DisplayPolicy.updateSystemBarsLw(DisplayPolicy.java:2784)

Traces for process: org.example.app
Count: 3
Trace: java.lang.Throwable
\tat android.os.BinderProxy.transact(BinderProxy.java:568)
\tat android.app.IActivityManager$Stub$Proxy.getRunningAppProcesses(IActivityManager.java:7000)
\tat android.app.ActivityManager.getRunningAppProcesses(ActivityManager.java:4000)
\tat org.example.app.Main.onCreate(Main.java:12)
\tat android.app.Activity.performCreate(Activity.java:9000)

Count: 1
Trace: java.lang.Throwable
\tat android.os.BinderProxy.transact(BinderProxy.java:568)
\tat android.view.IWindowSession$Stub$Proxy.relayout(IWindowSession.java:1800)
\tat android.view.ViewRootImpl.relayoutWindow(ViewRootImpl.java:10000)
\tat android.view.ViewRootImpl.performTraversals(ViewRootImpl.java:3500)
\tat android.os.Looper.loop(Looper.java:330)

Count: 2
Trace: java.lang.Throwable
\tat android.os.BinderProxy.transact(BinderProxy.java:568)
\tat android.content.ContentProviderProxy.call(ContentProviderNative.java:740)
\tat android.provider.Settings$NameValueCache.getStringForUser(Settings.java:3500)
\tat android.provider.Settings$Global.getStringForUser(Settings.java:19000)
"""


class IpcTraceTest(unittest.TestCase):
    def test_dump_is_grouped_by_process(self) -> None:
        processes = parse_dump(DUMP)
        self.assertEqual({"system", "org.example.app"}, set(processes))
        self.assertEqual([3, 1, 2], [t["count"] for t in processes["org.example.app"]])

    def test_app_frame_is_the_nearest_non_framework_caller(self) -> None:
        call = classify_trace(parse_dump(DUMP)["org.example.app"][0]["frames"])
        self.assertEqual(("android.app.IActivityManager", "getRunningAppProcesses", "activity"),
                         (call["interface"], call["method"], call["service"]))
        self.assertEqual("org.example.app.Main.onCreate(Main.java:12)", call["app_frame"])

    def test_framework_initiated_call_has_no_app_frame(self) -> None:
        call = classify_trace(parse_dump(DUMP)["org.example.app"][1]["frames"])
        self.assertEqual("window", call["service"])
        self.assertIsNone(call["app_frame"])
        self.assertTrue(call["framework_entry"].startswith("android.view.ViewRootImpl.relayoutWindow"))

    def test_settings_reads_are_attributed_to_the_settings_provider(self) -> None:
        call = classify_trace(parse_dump(DUMP)["org.example.app"][2]["frames"])
        self.assertEqual(("android.content.IContentProvider", "call", "settings-provider"),
                         (call["interface"], call["method"], call["service"]))

    def test_observe_counts_only_the_app_process(self) -> None:
        observed = observe(DUMP, "org.example.app")
        self.assertEqual(6, observed["summary"]["binder_calls"])
        self.assertEqual(0, observed["summary"]["unparsed_traces"])
        self.assertEqual({"activity", "window", "settings-provider"},
                         {s["service"] for s in observed["services"]})
        window = next(s for s in observed["services"] if s["service"] == "window")
        self.assertFalse(window["app_initiated"])

    def test_join_marks_reached_rows_and_framework_implied_services(self) -> None:
        gap_map = {"app": {"package": "org.example.app"},
                   "rows": [{"id": "svc:activity", "effort": "verify", "app_calls": ["getRunningAppProcesses"]},
                            {"id": "svc:location", "effort": "S", "app_calls": ["getLastKnownLocation"]},
                            {"id": "pm:call:queryBroadcastReceivers", "effort": "M"},
                            {"id": "svc:layout_inflater", "aosp_contract": "Landroid/view/LayoutInflater; needs binder(s) [] (x)"},
                            {"id": "jar:x"}]}
        joined = join_gap_map(observe(DUMP, "org.example.app"), gap_map)
        self.assertEqual(["svc:activity"], [r["id"] for r in joined["reached"]])
        self.assertEqual(["pm:call:queryBroadcastReceivers", "svc:location"], [r["id"] for r in joined["not_reached"]])
        self.assertEqual(["svc:layout_inflater"], [r["id"] for r in joined["not_observable"]])
        self.assertEqual(["getRunningAppProcesses"], joined["reached"][0]["app_calls_observed"])
        self.assertEqual({"window", "settings-provider"},
                         {u["service"] for u in joined["observed_but_not_in_map"]})


if __name__ == "__main__":
    unittest.main()
