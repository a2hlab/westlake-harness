import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from source import BASE_SHA, HERE, R3_SHA, candidate, sha


class BaselineTests(unittest.TestCase):
    def test_frozen_sources(self):
        self.assertEqual(sha(HERE / "inputs/host-r3.c"), BASE_SHA)
        self.assertEqual(sha(HERE / "inputs/resident-compat.h"), "e4f7321547d6cafac5734a7ff3b9338cc0e8a93e94ff5932bafa3caa23cb35e0")
        self.assertEqual((HERE / "src/candidate-stock-host.c").read_text(), candidate())

    def test_callbacks_are_only_host_source_changes(self):
        baseline = (HERE / "inputs/host-r3.c").read_text()
        updated = candidate().replace('#include "n11h-owner.h"\n', '')
        before = "static WLASC_NOINLINE int StockCreateConfiguredNamespaces("
        after = "static uint8_t HexNibble("
        self.assertEqual(baseline.split(before)[0], updated.split(before)[0])
        self.assertEqual(baseline.split(after)[1], updated.split(after)[1])

    def test_archived_exact_build_receipt(self):
        receipt = json.loads((HERE / "evidence/build-receipt.json").read_text())
        self.assertEqual(receipt["repeated"][0], receipt["repeated"][1])
        self.assertEqual(receipt["repeated"][0]["baseline"], R3_SHA)
        for name, digest in receipt["source_snapshot"].items():
            self.assertEqual(sha(HERE / name), digest)
        self.assertGreater(len(receipt["inputs"]), 100)


class ReplayTests(unittest.TestCase):
    def replay(self, selector):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "dlfcn.h").write_text('''#pragma once
typedef struct { char name[256]; } Dl_namespace;
#define RTLD_NOW 2
#define RTLD_NOLOAD 4
#define RTLD_LOCAL 0
#define RTLD_GLOBAL 256
int dlns_get(const char*, Dl_namespace*);
void* dlopen_ns(Dl_namespace*, const char*, int);
void* dlsym(void*, const char*);
int dlclose(void*);
char* dlerror(void);
''')
            text = candidate()
            start = text.index("static int NamespaceNameOwnedByCurrentProcess(")
            end = text.index("static uint8_t HexNibble(", start)
            (folder / "namespace-body.h").write_text(text[start:end])
            command = ["/usr/bin/cc", "-std=c11", "-I" + str(folder), "-I" + str(HERE),
                       "-I" + str(HERE / "inputs"), str(HERE / "test_namespace.c"), "-o", str(folder / "replay")]
            subprocess.run(command, check=True)
            subprocess.run([str(folder / "replay"), selector], check=True)


class NamespaceTests(ReplayTests):
    def test_real_callbacks_with_replacement_inheritance(self):
        self.replay("namespace")


class OpenTests(ReplayTests):
    def test_exact_owner_and_failure_routes(self):
        self.replay("open")


class ArtifactTests(unittest.TestCase):
    def test_review_report_does_not_claim_runtime_or_exception_approval(self):
        report = json.loads((HERE / "results.json").read_text())
        self.assertEqual(report["baseline_sha256"], R3_SHA)
        self.assertTrue(report["two_identical_builds"])
        self.assertEqual(report["inherit_repeat"], 0)
        self.assertEqual(report["sealed_edges_before_fresh_open"], 2)
        self.assertEqual(len(report["r3_after_open_comparison"]), 4)
        self.assertEqual(report["abi_consumer_breaks"], 0)
        self.assertEqual(report["unrelated_call_diffs"], 0)
        self.assertTrue(report["n2_exact_details_and_findings_unchanged"])
        self.assertFalse(report["rollout_ready"])
        self.assertFalse(report["device_io"])
        self.assertFalse(report["dynamic_single_owner_proven"])
        self.assertGreater(report["native_predeploy"]["gates"]["N1"]["rejected"], 0)
        self.assertEqual(report["native_predeploy"]["gates"]["N1"]["excepted"], 0)
        listing = json.loads((HERE / "evidence/open-candidate.json").read_text())
        self.assertFalse([row for row in listing["findings"] if row["kind"] == "INHERIT-REPEAT"])
        self.assertFalse([row for row in listing["findings"] if row["kind"] == "INHERIT-AFTER-OPEN"])
        abi = json.loads((HERE / "evidence/abi.json").read_text())
        self.assertEqual(abi["consumer_breaks"], [])
        self.assertEqual(len(abi["consumers"]), report["distinct_payload_consumers"])


if __name__ == "__main__":
    unittest.main()
