import copy
from pathlib import Path
import unittest

import intake
import scoring


HERE = Path(__file__).resolve().parent


def evidence():
    return intake.u6.read(HERE / "evidence/5ea-prepared.json"), intake.u6.read(HERE / "evidence/5ea-review.json")


class IdentityTests(unittest.TestCase):
    def test_exact_candidate_and_mutations(self):
        expected = intake.u6.read(intake.FROZEN / "expected-run.json")
        prepared, _ = evidence()
        row = next(row for row in prepared["rows"] if row["key"] == "burgerking")
        identity = row["observed_input"]
        record = dict(key=row["key"], package=identity["package"], apk_sha256=identity["apk_sha256"],
                      native_sidecars=[], input_sha256=row["metadata_sha256"],
                      install=dict(success_text=True), native_assembly=dict(status="not_needed", files=[]))
        arguments = [record, expected["runtime_files"], expected["boot_files"], expected, row["prediction"], row["tool"]]
        self.assertEqual(intake.identity_issues(*arguments), [])
        for index, field, value in [(0, "apk_sha256", "0" * 64), (0, "input_sha256", "0" * 64),
                                    (0, "package", "wrong"), (1, "extra", "0" * 64), (2, "extra", "0" * 64),
                                    (5, "bms_batch_sha256", "0" * 64), (5, "manifest_sha256", "0" * 64),
                                    (0, "native_sidecars", [dict(abi="arm64-v8a", name="extra.so", sha256="0" * 64)])]:
            changed = [copy.deepcopy(argument) for argument in arguments]
            changed[index][field] = value
            self.assertTrue(intake.identity_issues(*changed), (index, field))

    def test_freeze_and_all_shard_identities(self):
        prepared, _ = evidence()
        self.assertEqual(len(intake.verify_freeze()["files"]), 149)
        self.assertEqual(len(prepared["rows"]), 22)
        self.assertTrue(all(row["identity_verified"] and row["first_attempt"] and not row["issues"] for row in prepared["rows"]))


class AttemptTests(unittest.TestCase):
    def test_prelaunch_failure_is_not_retry_but_later_click_is(self):
        attempts = [dict(record="failed", clicked_at=None), dict(record="first", clicked_at=10), dict(record="retry", clicked_at=20)]
        self.assertTrue(intake.first_attempt("first", attempts))
        with self.assertRaisesRegex(ValueError, "later timed retry"):
            intake.first_attempt("retry", attempts)
        self.assertFalse(intake.first_attempt("failed", attempts[:1]))


class AxisTests(unittest.TestCase):
    def test_unsigned_checkpoint_missing_and_flaky(self):
        prepared, reviews = evidence()
        report = scoring.build(prepared, reviews)
        rows = {row["key"]: row for row in report["rows"]}
        self.assertEqual(rows["burgerking"]["scores"], dict(first_wall="hit", checkpoints="unknown", t20="unknown"))
        self.assertEqual(rows["antennapod"]["analyst_t20_preview"], "unknown")
        self.assertEqual(rows["fd-AppManager"]["scores"]["first_wall"], "unknown")
        row = next(row for row in prepared["rows"] if row["key"] == "burgerking")
        review = copy.deepcopy(reviews["rows"]["burgerking"])
        review["outer_signoff"] = dict(reviewer="outer", source="synthetic-test-only", visual="desktop", t20_sha256=row["t20_sha256"])
        self.assertEqual(scoring.score_row(row, review)["scores"], dict(first_wall="hit", checkpoints="unknown", t20="hit"))

    def test_identity_downgrade_and_warning_substitution(self):
        prepared, reviews = evidence()
        row = copy.deepcopy(next(row for row in prepared["rows"] if row["key"] == "burgerking"))
        review = copy.deepcopy(reviews["rows"]["burgerking"])
        review["root_line"] -= 1
        with self.assertRaisesRegex(ValueError, "substituted"):
            scoring.score_row(row, review)
        review = copy.deepcopy(reviews["rows"]["burgerking"])
        row["identity_verified"] = False
        review["observation_sha256"] = intake.u6.seal(row)
        self.assertEqual(set(scoring.score_row(row, review)["scores"].values()), {"unknown"})


class ReplayTests(unittest.TestCase):
    def test_artifacts_and_known_terminal_answers(self):
        prepared, reviews = evidence()
        report = scoring.build(prepared, reviews)
        self.assertEqual(report, intake.u6.read(HERE / "results.json"))
        self.assertEqual(scoring.markdown(report), (HERE / "PRELIMINARY.md").read_text())
        self.assertEqual(report["axes"], dict(first_wall=dict(hit=18, unknown=4), checkpoints={"not-applicable": 21, "unknown": 1}, t20=dict(unknown=22)))
        self.assertEqual(report["visual_counts"], {"own-ui": 15, "white": 2, "desktop": 5})
        expected = {"burgerking": (45572, 45398), "fd-api": (37113, 37171), "fd-breezyweather": (73120, 73135), "fd-client": (55892, 55907)}
        for row in report["rows"]:
            if row["key"] in expected:
                self.assertEqual((row["terminal_line"], row["root_line"]), expected[row["key"]])

    def test_changed_evidence_review_and_premature_formal_rejected(self):
        prepared, reviews = evidence()
        with self.assertRaisesRegex(ValueError, "all 66"):
            scoring.build(prepared, reviews, formal=True)
        changed = copy.deepcopy(prepared)
        changed["rows"][0]["t20_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "evidence or freeze"):
            scoring.build(changed, reviews)
        changed = copy.deepcopy(reviews)
        changed["rows"]["aegis"]["outer_signoff"] = dict(reviewer="outer", source="synthetic-test-only", visual="own-ui", t20_sha256="0" * 64)
        with self.assertRaisesRegex(ValueError, "signoff"):
            scoring.build(prepared, changed)
        changed = copy.deepcopy(reviews)
        changed["rows"]["fd-app"]["wall_id"] = "none"
        with self.assertRaisesRegex(ValueError, "no-wall"):
            scoring.build(prepared, changed)


if __name__ == "__main__":
    unittest.main()
