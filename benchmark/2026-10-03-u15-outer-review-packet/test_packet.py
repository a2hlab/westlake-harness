import copy
import csv
import sys
import unittest

from class_contracts import contract, parse_blocks
from common import HERE, load, sha
from strict_findings import differences, field_proof, finding, issue_id


def local(value):
    marker = "/benchmark/" + HERE.name + "/"
    if marker not in str(value):
        raise ValueError("Cold test requires a landed packet file: " + str(value))
    return HERE / str(value).split(marker, 1)[1]


class ClassTests(unittest.TestCase):
    def test_all_thirteen_contracts_and_sources(self):
        report = load(HERE / "classes.json")
        self.assertEqual((report["count"], report["nsd"], report["trampoline"], report["source_matches"]), (13, 8, 5, 13))
        self.assertEqual(report["comparison"], dict(equal_to_u14=0, exact_add=13, unexpected_add=0, dropped=0, reshaped=0))
        descriptors = set()
        for row in report["classes"]:
            self.assertNotIn(row["descriptor"], descriptors)
            descriptors.add(row["descriptor"])
            text = local(row["raw_dexdump"]).read_text()
            self.assertEqual(sha(local(row["raw_dexdump"])), row["raw_dexdump_sha256"])
            parsed = contract(row["descriptor"], text)
            for field in ["descriptor", "superclass", "interfaces", "methods"]:
                self.assertEqual(parsed[field], row[field])
            source = row["source"]
            self.assertEqual(sha(local(source["snapshot"])), source["sha256"])
            self.assertTrue(source["git_blob_matches"])
            self.assertEqual(len(source["commit"]), 40)
            delta = local(row["per_class_diff"])
            self.assertEqual(sha(delta), row["per_class_diff_sha256"])
            self.assertIn("U14:absent:" + row["descriptor"], delta.read_text())
            self.assertTrue(row["exact_add"] and row["absent_in_u14"])
            prediction = row["prediction"]
            self.assertEqual(prediction["measured_new_moves"], 0)
            self.assertEqual(prediction["new_screenshot_status"], "not measured")
            self.assertTrue(prediction["shared_cluster_credit_not_per_class"])
            if "/nsd/" in row["descriptor"]:
                self.assertEqual(prediction["served_keys"], ["fd-immich"])
                self.assertIsNone(prediction["standalone_first_fatal_prediction"])
                self.assertEqual(prediction["cluster_first_fatal_prediction"], 1)
                self.assertIn("NSD alone leaves ATrace", prediction["after"])
            else:
                self.assertEqual(len(set(prediction["served_keys"])), 36)
                self.assertIn("x", prediction["served_keys"])
                self.assertEqual(prediction["standalone_first_fatal_prediction"], 0)
        self.assertEqual(sorted((row["old_class_count"], row["new_class_count"]) for row in report["jars"]), [(219, 224), (268, 276)])

    def test_invalid_extraction_refuses(self):
        with self.assertRaises(ValueError):
            parse_blocks("")
        text = "Class descriptor : 'LExample;'\nSuperclass : 'Ljava/lang/Object;'\nDirect methods -\nname : 'hello'\ntype : '()V'\naccess : PUBLIC\n"
        self.assertEqual(contract("LExample;", parse_blocks(text)["LExample;"])["methods"][0]["signature"], "LExample;->hello()V")
        with self.assertRaises(ValueError):
            parse_blocks(text + text)
        with self.assertRaises(ValueError):
            contract("LExample;", "Class descriptor : 'LExample;'")
        with self.assertRaises(ValueError):
            contract("LExample;", text.replace("type : '()V'\n", ""))

    def test_class_original_exits(self):
        report = load(HERE / "classes.json")
        self.assertEqual([row["exit_code"] for row in report["records"]], [1, 1])
        for record, added in zip(report["records"], [8, 5]):
            text = local(record["evidence"]).read_text()
            self.assertEqual(sha(local(record["evidence"])), record["evidence_sha256"])
            self.assertIn("0 dropped, 0 reshaped, " + str(added) + " added", text)
        self.assertFalse(report["approved"] or report["execution_enabled"])


class RegistryTests(unittest.TestCase):
    def test_exact_204_and_recomputed_ids(self):
        report = load(HERE / "registry-comparison.json")
        self.assertEqual((report["count"], report["strictly_equal"], report["different"]), (204, 198, 6))
        self.assertEqual(report["new_findings"], [])
        self.assertEqual(report["missing_mappings"], [])
        self.assertEqual(report["active_registry_sha256_before"], report["active_registry_sha256_after"])
        self.assertFalse(report["applied"] or report["approved"])
        for gate, equal, changed in [("N1", 93, 6), ("N2", 105, 0)]:
            rows = [row for row in report["rows"] if row["gate"] == gate]
            self.assertEqual(sum(row["strict_equal"] for row in rows), equal)
            self.assertEqual(sum(not row["strict_equal"] for row in rows), changed)
        for row in report["rows"]:
            self.assertEqual(row["differences"], differences(row["old_finding"], row["new_finding"]))
            self.assertEqual(row["strict_equal"], not row["differences"])
            for version in ["old", "new"]:
                self.assertEqual(issue_id(row["gate"], row[version + "_finding"], row[version + "_manifest_sha256"], row[version + "_inputs_sha256"]), row[version + "_issue_id"])
            for name, proof in row["field_proof"].items():
                self.assertEqual(proof, field_proof(row["old_finding"], row["new_finding"], name))
            self.assertTrue(row["sequence_and_full_trace_compared"])
            if not row["strict_equal"]:
                self.assertTrue(all(item["path"].endswith("/line") for item in row["differences"]))
                for proof in row["evidence_source_proofs"]:
                    path = local(proof["snapshot"])
                    self.assertEqual(sha(path), proof["sha256"])
                    self.assertEqual(path.read_text().splitlines()[proof["line"] - proof["first_line"]].strip(), proof["text"])
                    self.assertTrue(proof["exact"])
        mapping = list(csv.DictReader((HERE / "registry-mapping.csv").open()))
        self.assertEqual(len(mapping), 204)
        self.assertEqual(len({row["new_issue_id"] for row in mapping}), 204)
        self.assertEqual(len({row["old_issue_id"] for row in mapping}), 204)

    def test_line_sequence_and_binding_regression(self):
        old = dict(profile="runtime", detail=dict(evidence=dict(source="example.cpp", line=4, text="same"), sequence=1))
        for field in ["line", "sequence"]:
            new = copy.deepcopy(old)
            if field == "line":
                new["detail"]["evidence"]["line"] += 1
            else:
                new["detail"]["sequence"] += 1
            self.assertEqual(len(differences(old, new)), 1)
            self.assertNotEqual(issue_id("N1", old, "manifest", "inputs"), issue_id("N1", new, "manifest", "inputs"))
        self.assertEqual(finding(dict(**old, issue_id="id", disposition="EXCEPTED", exception={})), old)
        self.assertNotEqual(issue_id("N1", old, "manifest", "inputs"), issue_id("N1", old, "other", "inputs"))
        self.assertEqual(differences(dict(field=0), dict(field=False))[0]["path"], "/field")

    def test_outer_commands_and_guard(self):
        report = load(HERE / "g2-replay-commands.json")
        self.assertEqual(len(report["commands"]), 4)
        for row in report["commands"]:
            self.assertFalse(row["executed"])
            self.assertIn("U15_PRODUCTION_REPLAY=outer-approved", row["argv"])
            expected = report["variants"][row["variant"]]
            for field in ["transaction_base", "transaction_base_sha256", "package"]:
                self.assertIn(expected[field], row["argv"])
            self.assertEqual(len(expected["transaction_base_sha256"]), 64)
            if row["surface"] == "vm":
                self.assertEqual(row["argv"][:3], ["orb", "-m", "a2hlab"])
        self.assertFalse(report["executed"] or report["execution_enabled"])
        self.assertIn("outer only", report["authority"])

    def test_anl_fix_and_observation_boundary(self):
        report = load(HERE / "anl-review.json")
        self.assertFalse(report["mechanical_relink"])
        self.assertEqual(len(report["aliases"]), 2)
        self.assertEqual(len({row["new_sha256"] for row in report["aliases"]}), 1)
        self.assertTrue(all(row["old_sha256"] != row["new_sha256"] for row in report["aliases"]))
        self.assertIn("ship/rollback together", report["required_pair"])
        for source in report["sources"]:
            self.assertEqual(source["commit"], report["source_commit"])
            self.assertEqual(sha(local(source["snapshot"])), source["sha256"])
            self.assertTrue(source["git_blob_matches"])
        host = report["final_host_source"]
        self.assertEqual(sha(local(host["snapshot"])), host["sha256"])
        host_lines = local(host["snapshot"]).read_text().splitlines()
        for marker in report["markers"]:
            self.assertFalse(marker["exact_anl_load_proof"])
            for line in marker["lines"]:
                self.assertEqual(host_lines[line["line"] - 1], line["text"])
        self.assertIsNone(report["anl_new_route_marker"])
        self.assertEqual(report["u16"]["matrix_covered_first_fatal_moves"], 0)
        self.assertTrue(report["u16"]["absence_is_not_lit"])
        self.assertEqual(sha(local(report["u16"]["snapshot"])), report["u16"]["sha256"])
        self.assertFalse(any(set(row["keys"].split()) & {"fd-meet", "meet"} for row in csv.DictReader(local(report["u16"]["snapshot"]).open())))
        self.assertTrue(all(not row["fd_meet_present"] and not row["meet_present"] for row in report["signoff_coverage"]))
        prediction = report["prediction"]
        self.assertEqual((prediction["current_confirmed_moves"], prediction["conditional_historical_moves"]), (0, 1))
        self.assertIn("unknown", prediction["current_u16_first_fatal"])
        self.assertIn("android_set_abort_message", prediction["historical_terminal"])
        self.assertEqual(prediction["lit"], "unknown")
        strings = (HERE / "evidence/anl-strings.txt").read_text()
        self.assertIn("ADDED   'org.jitsi.meet'", strings)
        self.assertIn("0 dropped, 1 added", strings)
        before = (HERE / "evidence/anl-disassembly-u14.txt").read_text()
        after = (HERE / "evidence/anl-disassembly-u15.txt").read_text()
        for register in ["x28", "x24"]:
            self.assertIn(register + ", #0xc", before)
            self.assertIn(register + ", #0xd", after)
        for version in ["u14", "u15"]:
            self.assertIn("(0 open sites)", (HERE / "evidence" / ("anl-open-" + version + ".txt")).read_text())
        self.assertFalse(report["device_access"] or report["vm_used"] or report["approved"] or report["execution_enabled"])

    def test_original_evidence_hashes_and_no_authority(self):
        records = load(HERE / "collection-runs.json")["records"] + load(HERE / "anl-review.json")["records"]
        self.assertEqual([row["exit_code"] for row in records], [1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0])
        for record in records:
            self.assertEqual(sha(local(record["evidence"])), record["evidence_sha256"])
            self.assertEqual(len(record["raw_sha256"]), 64)
        result = load(HERE / "results.json")
        for field in ["production_gates_passed", "execution_enabled", "window_authorized", "active_tables_written", "device_access", "vm_used"]:
            self.assertFalse(result[field])


if __name__ == "__main__":
    selected = unittest.defaultTestLoader.loadTestsFromTestCase(ClassTests if "--classes" in sys.argv else RegistryTests) if any(arg in sys.argv for arg in ["--classes", "--registry"]) else unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(selected)
    raise SystemExit(not result.wasSuccessful())
