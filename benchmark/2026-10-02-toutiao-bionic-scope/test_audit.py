import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import audit


def load(name):
    return json.loads((audit.HERE / name).read_text())


class IdentityTests(unittest.TestCase):
    def test_real_dynamic_bindings(self):
        identity = load("identity.json")
        self.assertEqual(identity["pins"], audit.PINS)
        exports = identity["compat"]["all_exports"]
        self.assertEqual(len(exports), 50)
        self.assertNotIn("__errno", exports)
        self.assertNotIn("__cmsg_nxthdr", exports)
        self.assertIn("__system_property_read", exports)
        self.assertIn("__gnu_strerror_r", exports)
        self.assertEqual(identity["compat"]["version_definitions"], [])
        self.assertRegex((audit.HERE / "evidence/compat-full-nm.txt").read_text(), r"330c t __errno")

    def test_pinned_binary_version_behavior(self):
        text = (audit.HERE / "evidence/oh-libc-check-version.txt").read_text()
        self.assertIn("8b220:", text)
        self.assertIn("8b294:", text)
        self.assertIn("strlen", text)
        self.assertIn("cset\tw0, eq", text)
        identity = load("identity.json")
        for symbol in identity["compat"]["symbols"]:
            if symbol["defined"]:
                self.assertEqual(symbol["version_index"], 1)
                self.assertIsNone(symbol["version"])


class ConsumerTests(unittest.TestCase):
    def test_166_inventory_is_exposure_only(self):
        inventory = load("consumers.json")
        self.assertEqual(inventory["key_count"], 166)
        self.assertEqual(len({app["key"] for app in inventory["apps"]}), 166)
        self.assertEqual(inventory["native_members"], 888)
        self.assertFalse(inventory["execution_proved"])
        self.assertEqual({row["symbol"]: row["affected_keys"] for row in inventory["groups"]},
                         {"__errno": 50, "__cmsg_nxthdr": 19, "__system_property_read": 4, "__gnu_strerror_r": 14})
        for app in inventory["apps"]:
            for member in app["members"]:
                if member["status"] == "ELF64-AArch64":
                    for symbol in member["imports"]:
                        self.assertEqual(symbol["version"]["version"], "LIBC")
                        self.assertEqual(symbol["version"]["file"], "libc.so")
        self.assertEqual(audit.elf(b"not an ELF")["status"], "unsupported-ABI-or-non-ELF-not-clean")

    def test_observation_not_import_count_is_prediction(self):
        report = load("observations.json")
        self.assertEqual(report["scanned_logs"], 166)
        self.assertEqual(report["run_shards"], 9)
        self.assertEqual(report["actual_error_keys"]["__errno"], ["ooniprobe", "x"])
        self.assertEqual(report["actual_error_keys"]["__gnu_strerror_r"], ["fd-fennec_fdroid", "firefox"])
        self.assertEqual(report["actual_error_keys"]["__cmsg_nxthdr"], [])
        self.assertEqual(report["predicted_first_fatal_moved_keys_exports_only"], [])
        rows = {row["key"]: row for row in report["rows"]}
        self.assertIn("TelephonyManager", rows["x"]["first_fatal"]["root"]["event"]["message"])
        self.assertEqual(rows["x"]["first_fatal"]["terminal"]["event"]["line"], 32788)
        self.assertEqual(rows["ooniprobe"]["signed_status"], "lit")
        for key in ["fd-fennec_fdroid", "firefox"]:
            self.assertEqual(rows[key]["exports_only_prediction"], "gnu-wall-unchanged")


class CandidateTests(unittest.TestCase):
    def test_exact_repeats_and_no_removed_consumed_symbols(self):
        compat = load("build-receipt.json")
        host = load("host-build-receipt.json")
        for receipt in [compat, host]:
            self.assertTrue(receipt["baseline_reproduced"])
            self.assertEqual(receipt["repeated"][0], receipt["repeated"][1])
        for name in ["exports-only", "scope-global-reference", "host-proposal"]:
            delta = load("evidence/abi-" + name + ".json")
            self.assertEqual(delta["removed"], [])
            self.assertEqual(delta["drift"], [])
            self.assertEqual(delta["call_diffs"], [])
            self.assertEqual(delta["consumer_breaks"], [])
            self.assertTrue(delta["consumers"])
            self.assertEqual(delta["added"], [] if name == "host-proposal" else ["__cmsg_nxthdr", "__errno"])

    def test_android_cmsg_alignment_boundary_full_width(self):
        fixture = '\n'.join([
            '#include "' + str(audit.HERE / "cmsg_android.c") + '"',
            'int main(void) {',
            '    _Alignas(8) char control[64] = {0};',
            '    struct AndroidMsghdr message = {.msg_control = control, .msg_controllen = 40};',
            '    struct AndroidCmsghdr* first = (struct AndroidCmsghdr*)control;',
            '    first->cmsg_len = 17;',
            '    if (__cmsg_nxthdr(&message, first) != (struct AndroidCmsghdr*)(control + 24)) return 1;',
            '    message.msg_controllen = 39;',
            '    if (__cmsg_nxthdr(&message, first) != NULL) return 2;',
            '    message.msg_controllen = ((size_t)1 << 32) + 39;',
            '    if (__cmsg_nxthdr(&message, first) != (struct AndroidCmsghdr*)(control + 24)) return 3;',
            '    return 0;',
            '}',
        ])
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            source, executable = folder / "test.c", folder / "test"
            source.write_text(fixture)
            subprocess.run([shutil.which("clang") or "cc", "-std=c11", "-O2", source, "-o", executable], check=True)
            subprocess.run([executable], check=True)


class NamespaceTests(unittest.TestCase):
    def test_only_resident_query_flag_delta(self):
        delta = load("evidence/namespace-delta.json")
        self.assertEqual(delta["old_edges"], delta["new_edges"])
        self.assertEqual(delta["old_sites"], delta["new_sites"])
        self.assertEqual(len(delta["changed"]), 1)
        site = delta["changed"][0]
        self.assertEqual(site["old"]["pc"], "0xd6c8")
        self.assertEqual(site["old"]["flags"], ["0x6=NOW|NOLOAD"])
        self.assertEqual(site["new"]["flags"], ["0x106=NOW|NOLOAD|GLOBAL"])
        self.assertEqual(delta["findings_old"], delta["findings_new"])
        self.assertNotIn("INHERIT-REPEAT", json.dumps(delta["findings_new"]))
        self.assertEqual(json.dumps(delta["findings_new"]).count('"INHERIT-AFTER-OPEN"'), 4)

    def test_no_claimed_new_owner_or_scope_proof(self):
        candidate = load("candidate-evidence.json")
        self.assertFalse(candidate["device_io"])
        self.assertIn("PENDING", candidate["publication_status"])
        self.assertFalse(candidate["version_node_change"])
        policy = load("evidence/current-policy.json")
        self.assertEqual(len(policy["baked"]["system_libraries"]), 5)
        self.assertIn("libsoundpool.so", [row["soname"] for row in policy["baked"]["system_libraries"]])
        self.assertIn("libstdc++.so", policy["baked"]["shared_sonames"])
        self.assertIn("80f58:", (audit.HERE / "evidence/oh-libc-saved-scope.txt").read_text())


if __name__ == "__main__":
    unittest.main()
