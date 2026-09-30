import copy
import json
from pathlib import Path
import unittest

import classify
import benign


HERE = Path(__file__).resolve().parent


def event(message, pid=123, tid=456, tag="App", number=1):
    return classify.parse(f"10-01 01:00:00.000 {pid} {tid} I C00f00/{tag}: {message}", number)


class PidTests(unittest.TestCase):
    def test_date_and_dedicated_main(self):
        events = [event("ActivityThread on dedicated pthread stack=8390896", number=1),
                  event("last app operation", number=2), event("CommitAndReleaseBuffer rc=0", pid=999, number=3)]
        result = classify.summarize(events, {123})
        self.assertEqual(123, events[0]["pid"])
        self.assertEqual(456, result["processes"][0]["java_main"]["tid"])
        self.assertEqual(2, result["processes"][0]["java_main_last"]["line"])
        self.assertEqual([], result["submit_success"])

    def test_reject_timestamp_as_pid_and_unattributed_lines(self):
        with self.assertRaises(ValueError):
            classify.scoped([event("log")], {"01:00:00.000"})
        self.assertIsNone(classify.parse("unprefixed stack frame", 1))
        self.assertEqual([], classify.scoped([event("later")], {123}, "10-01 00:59:59.999"))


class CohortTests(unittest.TestCase):
    def test_all_66_and_fatal_parent_exclusion(self):
        cohort = json.loads((HERE / "evidence/cohort.json").read_text())["cohort"]
        self.assertEqual(66, len(cohort))
        self.assertEqual(66, len({row["key"] for row in cohort}))
        self.assertEqual({"fd-AppManager", "fd-noice", "fd-organicmaps", "noice", "termux"}, {row["key"] for row in cohort if row["status"] == "selected"})
        gallery = next(row for row in cohort if row["key"] == "fd-gallery")
        self.assertIn("target-fatal", gallery["status"])
        self.assertEqual("excluded-visual-black", classify.eligibility("black", [123], []))
        self.assertEqual("excluded-no-live-target-at-t20", classify.eligibility("desktop", [], []))


class CategoryTests(unittest.TestCase):
    def test_five_positive_categories(self):
        samples = {
            "waiting-network": [event("waiting for network callback")],
            "waiting-permission-or-dialog": [event("permission request pending")],
            "window-without-frame": [event("createSession: published process window target session=1"), event("waiting for first buffer")],
            "caught-exception": [event("java.io.IOException: canceled due to missing SSLSockets", tag="SubscriptionRepository")],
            "other": [event("normal message")],
        }
        self.assertEqual(set(classify.CATEGORIES), set(samples))
        for expected, events in samples.items():
            self.assertEqual(expected, classify.category(classify.summarize(events, {123})))

    def test_transport_error_or_window_silence_is_not_wait_proof(self):
        result = classify.summarize([event("SocketTimeoutException"), event("createSession: published process window target session=1")], {123})
        self.assertEqual("other", classify.category(result))
        self.assertEqual(1, len(result["network_errors"]))


class MarkerTests(unittest.TestCase):
    def test_registration_callback_and_linking_not_submission(self):
        events = [event("eglSwapBuffers -> fn=00000001", tag="OH_RegHook"),
                  event("[class_linker.cc:10] ClassNotFoundException"),
                  event("activityResumed (first-frame): OH AbilityTransitionDone rc=0"),
                  event("CommitAndReleaseBuffer rc=0", pid=999)]
        result = classify.summarize(events, {123})
        self.assertEqual([], result["submit_success"])
        self.assertEqual([], result["exception_events"])
        self.assertEqual(1, len(result["lifecycle_callback"]))
        self.assertEqual("other", classify.category(result))

    def test_swap_entry_is_not_success(self):
        result = classify.summarize([event("[G2.14ax r2d SwapDmgKHR #0 pre-clear-sample] tl=ffffffff")], {123})
        self.assertEqual(1, len(result["swap_entered"]))
        self.assertEqual([], result["submit_success"])

    def test_real_replay_and_foreign_injection(self):
        for path in sorted((HERE / "evidence").glob("app-*.json")):
            row = json.loads(path.read_text())
            events = row["replay_events"]
            registry = json.loads(benign.REGISTRY.read_text())
            result = classify.summarize(events, set(row["pids"]), row["cutoff"], registry, row["context"])
            for field, references in row["facts"].items():
                if isinstance(references, list) and field != "processes":
                    self.assertEqual(references, [entry["line"] for entry in result[field]], (row["key"], field))
            self.assertEqual(row["facts"]["category"], classify.category(result))
            poisoned = copy.deepcopy(events) + [event("CommitAndReleaseBuffer rc=0", pid=999999)]
            self.assertEqual(result, classify.summarize(poisoned, set(row["pids"]), row["cutoff"], registry, row["context"]))
            self.assertEqual(row["facts"]["benign_noise"], result["benign_noise"])
            self.assertTrue(all(entry["pid"] in row["pids"] for entry in events))
        termux = json.loads((HERE / "evidence/app-termux.json").read_text())
        self.assertTrue(termux["facts"]["lifecycle_callback"])
        self.assertFalse(termux["facts"]["window_created"])
        self.assertFalse(termux["facts"]["swap_entered"])


class BenignSupportTests(unittest.TestCase):
    def test_support_and_normalization(self):
        registry = json.loads(benign.REGISTRY.read_text())
        inputs = {row["key"]: row for row in registry["source_pins"]}
        self.assertEqual(24, len(inputs))
        self.assertEqual(17, len(registry["signatures"]))
        for row in registry["signatures"]:
            self.assertGreaterEqual(row["distinct_app_count"], 3)
            self.assertEqual(row["distinct_app_count"], len({item["package"] for item in row["supports"].values()}))
            self.assertEqual(row["occurrence_count"], sum(item["count"] for item in row["supports"].values()))
            self.assertEqual(3, len({example["package"] for example in row["examples"]}))
            for example in row["examples"]:
                source = inputs[example["key"]]
                self.assertEqual("own-ui", source["visual"])
                self.assertIn(example["event"]["pid"], source["pids"])
                self.assertEqual(row["signature"], benign.signature(example["event"]))
        self.assertEqual(benign.signature(event("token=0x7f01234567 pid=123")), benign.signature(event("token=0x7e98765432 pid=987", pid=987)))


class BenignSafetyTests(unittest.TestCase):
    def test_coroutine_stack_requires_caught_probe_context(self):
        registry = json.loads(benign.REGISTRY.read_text())
        header = registry["signatures"][-1]["examples"][0]["event"]
        stack = dict(header, line=header["line"]+1, message="[stderr] java.lang.ClassNotFoundException: kotlinx.coroutines.CoroutineStart")
        kept, noise = benign.partition([header, stack], registry, benign.CONTEXT)
        self.assertFalse(kept)
        self.assertEqual(2, len(noise))
        self.assertEqual(([stack], []), benign.partition([stack], registry, benign.CONTEXT))
        other_thread = dict(stack, tid=stack["tid"]+1)
        self.assertEqual([other_thread], benign.partition([header, other_thread], registry, benign.CONTEXT)[0])
        boundary = dict(stack, message="new operation")
        self.assertEqual([boundary, stack], benign.partition([header, boundary, stack], registry, benign.CONTEXT)[0])

    def test_fatal_and_context_never_waived(self):
        registry = json.loads(benign.REGISTRY.read_text())
        sample = registry["signatures"][0]["examples"][0]["event"]
        kept, noise = benign.partition([sample], registry, benign.CONTEXT)
        self.assertEqual([], kept)
        self.assertEqual(sample, noise[0]["event"])
        unsupported = copy.deepcopy(registry)
        unsupported["signatures"][0]["distinct_app_count"] = 2
        self.assertEqual(([sample], []), benign.partition([sample], unsupported, benign.CONTEXT))
        self.assertEqual(([sample], []), benign.partition([sample], registry, dict(benign.CONTEXT, generation="U6")))
        terminal = event("J_invokeStaticMain_main_threw: fatal")
        corrupt = copy.deepcopy(registry)
        corrupt["signatures"].append({"id": "bad", "signature": benign.signature(terminal), "distinct_app_count": 24, "enabled_for_triage": True})
        self.assertEqual(([terminal], []), benign.partition([terminal], corrupt, benign.CONTEXT))
        unknown = event("java.lang.NoClassDefFoundError: android.net.ssl.SSLSockets", tag="SubscriptionRepository")
        self.assertEqual(([unknown], []), benign.partition([unknown], registry, benign.CONTEXT))


if __name__ == "__main__":
    unittest.main()
