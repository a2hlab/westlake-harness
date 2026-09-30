import copy
import json
from pathlib import Path
import unittest

import report
import rules


def method(owner, name, descriptor="()V", calls=None, code=True):
    return dict(id=owner + "->" + name + descriptor, owner=owner, name=name, descriptor=descriptor,
                dex="classes.dex", dex_sha256="a" * 64, code=code, calls=calls or [], constants=[], branches=0)


def call(owner, name, descriptor="()V"):
    return dict(owner=owner, name=name, descriptor=descriptor, target=owner + "->" + name + descriptor,
                line=12, offset="0010", opcode="invoke-virtual", instruction="invoke-virtual {}")


class RuleTests(unittest.TestCase):
    def test_direct_helper_callback_and_wrong_signature(self):
        owner = "Ltest/Main;"
        classes = {owner: "Landroid/app/Activity;"}
        start = call(owner, "startActivity", "(Landroid/content/Intent;)V")
        create = method(owner, "onCreate", "(Landroid/os/Bundle;)V", [call(owner, "route")])
        helper = method(owner, "route", calls=[start, call(owner, "finish")])
        helper["branches"] = 1
        methods = {item["id"]: item for item in [create, helper]}
        result = rules.inspect_activity("test.Main", classes, methods)
        self.assertEqual(len(result["starts"]), 1)
        self.assertTrue(result["starts"][0]["conditional"])
        self.assertEqual(len(result["finishes"]), 1)
        create["calls"] = [call(owner, "startActivity", "(Ljava/lang/String;)V")]
        self.assertEqual(rules.inspect_activity("test.Main", classes, methods)["status"], "no-lifecycle-start-found")
        create["calls"] = []
        self.assertFalse(rules.inspect_activity("test.Main", classes, methods)["starts"])

    def test_inherited_modern_native_and_missing(self):
        classes = {"Ltest/Main;": "Ltest/Base;", "Ltest/Base;": "Landroid/app/Activity;", "Ltest/Launcher;": "Landroidx/activity/result/ActivityResultLauncher;"}
        base = method("Ltest/Base;", "onResume", calls=[call("Ltest/Launcher;", "launch", "(Ljava/lang/Object;)V")])
        methods = {base["id"]: base}
        result = rules.inspect_activity("test.Main", classes, methods)
        self.assertEqual(result["starts"][0]["kind"], "activity-result-launch")
        base["code"] = False
        self.assertEqual(rules.inspect_activity("test.Main", classes, methods)["status"], "unknown-bounded-analysis")
        self.assertEqual(rules.inspect_activity("absent.Main", classes, methods)["status"], "unknown-missing-class")

    def test_alias_and_filter_pairing(self):
        text = '''E: manifest
  A: package="test"
  E: application
    E: activity
      A: android:name=".Main"
      E: intent-filter
        E: action
          A: android:name="android.intent.action.MAIN"
      E: intent-filter
        E: category
          A: android:name="android.intent.category.LAUNCHER"
    E: activity-alias
      A: android:name=".Icon"
      A: android:targetActivity=".Main"
      E: intent-filter
        E: action
          A: android:name="android.intent.action.MAIN"
        E: category
          A: android:name="android.intent.category.LAUNCHER"
'''
        parsed = rules.manifest(text)
        self.assertEqual(len(parsed["activities"]), 1)
        self.assertEqual(len(parsed["launchers"]), 1)
        self.assertEqual(parsed["launchers"][0]["target"], "test.Main")

    def test_opcode_parser(self):
        text = '''  Class descriptor  : 'Ltest/Main;'
  Superclass        : 'Landroid/app/Activity;'
  Virtual methods   -
    #0              : (in Ltest/Main;)
      name          : 'onResume'
      type          : '()V'
000000: 0000 |0000: invoke-virtual {v0, v1}, Ltest/Main;.startActivity:(Landroid/content/Intent;)V // method@0001
000002: 0000 |0002: const-string v0, "startActivity"
'''
        classes, methods = rules.parse_dex(text.splitlines(), "classes.dex", "a" * 64)
        result = rules.inspect_activity("test.Main", classes, methods)
        self.assertEqual(len(result["starts"]), 1)
        self.assertEqual(result["starts"][0]["instruction"]["offset"], "0000")

    def test_super_lifecycle_does_not_spend_helper_budget(self):
        classes, methods = {}, {}
        for number in range(6):
            owner, parent = f"Ltest/Base{number};", f"Ltest/Base{number + 1};"
            classes[owner] = parent if number < 5 else "Landroid/app/Activity;"
            calls = [call(parent, "onResume")] if number < 5 else [call(owner, "startActivity", "(Landroid/content/Intent;)V")]
            item = method(owner, "onResume", calls=calls)
            methods[item["id"]] = item
        result = rules.inspect_activity("test.Base0", classes, methods)
        self.assertEqual(len(result["starts"]), 1)
        self.assertFalse(result["limits"])

    def test_helper_depth_remains_unknown(self):
        owner = "Ltest/Main;"
        classes = {owner: "Landroid/app/Activity;"}
        items = [method(owner, "onResume", calls=[call(owner, "helper0")])]
        for number in range(5):
            items.append(method(owner, f"helper{number}", calls=[call(owner, f"helper{number + 1}")]))
        result = rules.inspect_activity("test.Main", classes, {item["id"]: item for item in items})
        self.assertEqual(result["status"], "unknown-bounded-analysis")
        self.assertTrue(any(item.startswith("helper-depth-limit") for item in result["limits"]))

    def test_permission_is_not_an_activity_trampoline(self):
        witness = dict(instruction=dict(line=30, instruction="invoke-virtual {v0, v1}, Launcher.launch"))
        lines = [dict(line=29, text='|0000: const-string v1, "android.permission.POST_NOTIFICATIONS"')]
        self.assertEqual(rules.modern_input(witness, lines)["kind"], "permission-string-input")
        lines.append(dict(line=29, text="|0001: new-instance v1, Landroid/content/Intent;"))
        self.assertEqual(rules.modern_input(witness, lines)["kind"], "intent-object-input")
        lines.append(dict(line=29, text="|0002: move-object v1, v2"))
        self.assertEqual(rules.modern_input(witness, lines)["kind"], "unknown")


class ReplayTests(unittest.TestCase):
    def test_report_and_controls(self):
        actual = report.build()
        self.assertEqual(actual, json.loads((report.HERE / "results.json").read_text()))
        self.assertEqual(len(actual["rows"]), 66)
        self.assertEqual(len(actual["controls"]), 2)
        self.assertFalse(any(item["false_positive"] for item in actual["controls"]))
        wiki = next(item for item in actual["rows"] if item["key"] == "wikipedia")
        self.assertGreater(wiki["activity_result_sites"], 0)
        self.assertEqual(wiki["literal_start_sites"], 0)
        for key in ["fd-reader", "fd-droidify", "fd-uhabits"]:
            row = next(item for item in actual["rows"] if item["key"] == key)
            self.assertFalse(row["starts"])
            self.assertTrue(row["permission_requests"])

    def test_tampering_rejected(self):
        row = report.read_evidence("wikipedia")
        changed = copy.deepcopy(row)
        changed["manifest_text"] += "\n"
        with self.assertRaises(ValueError):
            report.verify_row(changed)
        changed = copy.deepcopy(row)
        changed["launchers"][0]["analysis"]["starts"] = []
        with self.assertRaises(ValueError):
            report.verify_row(changed)


if __name__ == "__main__":
    unittest.main()
