import copy
from pathlib import Path
import tempfile
import unittest

import score


def event(message, pid=123, tid=456, number=1):
    return score.classify.parse(f"10-01 04:30:00.000 {pid} {tid} I C00f00/AppSpawnXJava: {message}", number)


class NoiseSupportTests(unittest.TestCase):
    def test_live_html_and_historical_pin(self):
        registry = score.read(score.benign.REGISTRY)
        self.assertEqual(18, len(registry["signatures"]))
        html = next(row for row in registry["signatures"] if row["id"] == "U5-BENIGN-018")
        self.assertEqual(24, html["distinct_app_count"])
        self.assertEqual(28, html["occurrence_count"])
        pins = {row["key"]: row for row in registry["source_pins"]}
        for sample in html["examples"]:
            self.assertIn(sample["event"]["pid"], pins[sample["key"]]["pids"])
            self.assertEqual(html["signature"], score.benign.signature(sample["event"]))
        old = score.HERE / "evidence/benign-v1.json"
        cohort = score.read(score.HERE.parent / "2026-10-01-u5-investigate/evidence/cohort.json")
        self.assertEqual(cohort["benign_registry_sha256"], score.sha(old))
        self.assertEqual(17, len(score.read(old)["signatures"]))


class NoiseSafetyTests(unittest.TestCase):
    def test_exact_candidate_projection_and_fatal(self):
        registry = score.read(score.benign.REGISTRY)
        expected = score.read(score.FROZEN / "expected-run.json")
        applied, policy = score.noise_registry("u6", expected["runtime_files"], expected["boot_files"], registry, expected)
        self.assertEqual("U6", applied["context"]["generation"])
        self.assertIn("authorized", policy)
        html = copy.deepcopy(registry["signatures"][-1]["examples"][0]["event"])
        fatal = event("FATAL EXCEPTION: main", pid=html["pid"])
        foreign = event("Fatal signal 11", pid=999999)
        kept, noise = score.triage([html, fatal, foreign], {html["pid"]}, None, applied)
        self.assertEqual([fatal], kept)
        self.assertEqual([html], [row["event"] for row in noise])
        applied, _ = score.noise_registry("u6", {}, expected["boot_files"], registry, expected)
        self.assertIsNone(applied)
        self.assertEqual(([html], []), score.triage([html], {html["pid"]}, None, applied))
        self.assertEqual(([], []), score.triage([html], set(), None, registry))


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        expected = score.read(score.FROZEN / "expected-run.json")
        board = self.root / "runs/u6-synthetic/serial"
        board.mkdir(parents=True)
        for filename, field in [("runtime-fingerprint.txt", "runtime_files"), ("boot-image-fingerprint.txt", "boot_files")]:
            (board / filename).write_text("".join(digest + "  " + path + "\n" for path, digest in expected[field].items()))
        selected = []
        for key, identity in expected["apps"].items():
            folder = board / key
            folder.mkdir()
            lines = [f"10-01 04:30:00.000 123 456 I C00f00/AppSpawnXJava: nativeOnScheduleLaunchApplication ENTRY bundle={identity['package']} activity=test",
                     "10-01 04:30:01.000 123 456 I C00f00/AppSpawnXJava: positive business operation"]
            (folder / "hilog.txt").write_text("\n".join(lines) + "\n")
            (folder / "t20.jpeg").write_bytes(b"synthetic-test-capture-not-real-UI")
            record = dict(key=key, serial="serial", boot_id="boot", package=identity["package"], apk_sha256=identity["apk_sha256"],
                          native_sidecars=[dict(abi=path.split("/")[1], name=path.split("/")[-1], sha256=digest) for path, digest in identity["sidecars"].items()],
                          clicked_at=1790800200, install={"success_text": True}, native_assembly={"status": "verified"},
                          diagnostics={"sha256": score.sha(folder / "hilog.txt"), "complete": True},
                          screenshots=[dict(scheduled_seconds=20, captured=True, sha256=score.sha(folder / "t20.jpeg"),
                                            remote_stat="10 1790800220", elapsed_seconds=20)])
            record["native_assembly"]["files"] = [dict(item, verified=True) for item in record["native_sidecars"]]
            path = folder / "record.json"
            path.write_text(score.encoded(record))
            selected.append(dict(key=key, record=str(path.relative_to(self.root)), record_sha256=score.sha(path)))
        self.index_path = self.root / "index-test.json"
        self.index = dict(serial="serial", boot_id="boot", selected=selected)
        self.save_index()

    def save_index(self):
        self.index_path.write_text(score.encoded(self.index))

    def change_record(self, key, callback):
        entry = next(item for item in self.index["selected"] if item["key"] == key)
        path = self.root / entry["record"]
        record = score.read(path)
        callback(record)
        path.write_text(score.encoded(record))
        entry["record_sha256"] = score.sha(path)
        self.save_index()


class IntakeTests(Fixture):
    def test_complete_structure_and_mismatch(self):
        prepared = score.prepare(self.root, "u6")
        self.assertEqual(66, len(prepared["rows"]))
        self.assertTrue(all(row["identity_verified"] and row["first_attempt"] for row in prepared["rows"]))
        self.change_record("aegis", lambda record: record.update(apk_sha256="0" * 64))
        row = next(row for row in score.prepare(self.root, "u6")["rows"] if row["key"] == "aegis")
        self.assertFalse(row["identity_verified"])
        self.assertIn("input-mismatch", row["issues"])

    def test_hash_duplicate_missing_and_retry(self):
        entry = self.index["selected"][0]
        path = self.root / entry["record"]
        path.write_text(path.read_text() + " ")
        with self.assertRaisesRegex(ValueError, "record changed"):
            score.prepare(self.root, "u6")
        entry["record_sha256"] = score.sha(path)
        self.index["selected"].append(dict(entry))
        self.save_index()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            score.prepare(self.root, "u6")
        self.index["selected"].pop()
        self.save_index()
        retry = self.root / "runs/earlier/serial" / entry["key"] / "record.json"
        retry.parent.mkdir(parents=True)
        record = score.read(path)
        record["clicked_at"] -= 10
        retry.write_text(score.encoded(record))
        with self.assertRaisesRegex(ValueError, "selected retry"):
            score.prepare(self.root, "u6")
        self.index["selected"].pop()
        self.save_index()
        with self.assertRaisesRegex(ValueError, "cohort"):
            score.prepare(self.root, "u6")

    def test_log_and_image_tampering(self):
        folder = (self.root / self.index["selected"][0]["record"]).parent
        image = folder / "t20.jpeg"
        original = image.read_bytes()
        image.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "image changed"):
            score.prepare(self.root, "u6")
        image.write_bytes(original)
        (folder / "hilog.txt").write_text("changed")
        with self.assertRaisesRegex(ValueError, "log changed"):
            score.prepare(self.root, "u6")

    def test_candidate_mismatch_and_missing_log(self):
        (self.root / "runs/u6-synthetic/serial/runtime-fingerprint.txt").write_text("")
        key = self.index["selected"][0]["key"]
        (self.root / self.index["selected"][0]["record"]).with_name("hilog.txt").unlink()
        prepared = score.prepare(self.root, "u6")
        self.assertFalse(any(row["identity_verified"] for row in prepared["rows"]))
        row = next(row for row in prepared["rows"] if row["key"] == key)
        self.assertEqual([], row["target_pids"])
        self.assertEqual("disabled-candidate-mismatch", row["noise_policy"])

    def test_null_install_remains_unverified(self):
        self.change_record("aegis", lambda record: record.update(install=None, native_assembly=None))
        row = next(row for row in score.prepare(self.root, "u6")["rows"] if row["key"] == "aegis")
        self.assertFalse(row["identity_verified"])
        self.assertIn("installation-unverified", row["issues"])

    def test_no_sidecars_and_changed_installed_inventory(self):
        self.change_record("fd-noice", lambda record: record.update(native_assembly=dict(status="not_needed", files=[])))
        self.change_record("aegis", lambda record: record["native_assembly"]["files"][0].update(sha256="0" * 64))
        rows = {row["key"]: row for row in score.prepare(self.root, "u6")["rows"]}
        self.assertTrue(rows["fd-noice"]["identity_verified"])
        self.assertFalse(rows["aegis"]["identity_verified"])


class AxesTests(Fixture):
    def reviewed(self):
        prepared = score.prepare(self.root, "u6")
        reviewed = score.review_template(prepared)
        reviewed.update(complete=True, outer_signoff="synthetic unit-test signoff; not board evidence")
        return prepared, reviewed

    def test_three_axes_not_inferred_from_each_other(self):
        prepared, reviewed = self.reviewed()
        source = next(row for row in prepared["rows"] if row["key"] == "aegis")
        row = next(row for row in reviewed["rows"] if row["key"] == "aegis")
        row["t20"] = dict(sha256=source["t20_sha256"], visual="own-ui", description="synthetic own UI")
        result = score.score(prepared, reviewed)
        result_row = next(row for row in result["rows"] if row["key"] == "aegis")
        self.assertEqual(dict(first_wall="unknown", checkpoints="not-applicable", t20="hit"), result_row["scores"])
        row["first_wall"] = dict(id="none", lines=[2], rationale="reviewed positive execution; synthetic")
        result = score.score(prepared, reviewed)
        self.assertEqual("hit", next(row for row in result["rows"] if row["key"] == "aegis")["scores"]["first_wall"])

    def test_rehearsal_unsigned_stale_and_noise_refs_reject(self):
        prepared, reviewed = self.reviewed()
        reviewed["complete"] = False
        with self.assertRaisesRegex(ValueError, "signoff"):
            score.score(prepared, reviewed)
        reviewed["complete"] = True
        reviewed["prepared_sha256"] = "wrong"
        with self.assertRaisesRegex(ValueError, "signoff"):
            score.score(prepared, reviewed)
        reviewed["prepared_sha256"] = score.seal(prepared)
        reviewed["rows"][0]["first_wall"] = dict(id="wall", lines=[999999], rationale="unbound")
        with self.assertRaisesRegex(ValueError, "log lines"):
            score.score(prepared, reviewed)
        prepared["mode"] = "rehearsal"
        with self.assertRaisesRegex(ValueError, "rehearsal"):
            score.score(prepared, reviewed)

    def test_frozen_conflict_flaky_and_identity(self):
        prediction = dict(wall_id="wall", fix_ids=["fix"], flaky=False, t20_prediction="own-ui")
        observed = dict(identity_verified=True, first_attempt=True, first_wall_confirmed=True,
                        first_wall_id="different", positive_crossings=["fix"], old_wall_reproduced=["fix"],
                        t20_reviewed=True, own_ui=True)
        self.assertEqual(dict(first_wall="false_positive", checkpoints="unknown", t20="hit"), score.forecast.score_reviewed(prediction, observed))
        self.assertEqual("unknown", score.forecast.score_reviewed(dict(prediction, flaky=True), observed)["t20"])
        self.assertEqual({"unknown"}, set(score.forecast.score_reviewed(prediction, dict(observed, identity_verified=False)).values()))
        self.assertEqual("hit", score.forecast.score_reviewed(prediction, dict(observed, old_wall_reproduced=[]))["checkpoints"])
        self.assertEqual("false_positive", score.forecast.score_reviewed(prediction, dict(observed, positive_crossings=[]))["checkpoints"])

    def test_review_cites_termination_not_earlier_warning(self):
        prepared, reviewed = self.reviewed()
        source = prepared["rows"][0]
        terminal = event("System.exit called, status: 1", number=3)
        source["termination"]["terminal"] = dict(kind="system-exit", event=terminal)
        source["fatal"] = [terminal]
        source["allowed_evidence_lines"].append(3)
        reviewed["prepared_sha256"] = score.seal(prepared)
        row = reviewed["rows"][0]
        row["first_wall"] = dict(id="SDK-warning", lines=[2], rationale="earlier is not causal")
        with self.assertRaisesRegex(ValueError, "selected termination"):
            score.score(prepared, reviewed)
        row["first_wall"] = dict(id="none", lines=[2], rationale="contradiction")
        with self.assertRaisesRegex(ValueError, "terminal target"):
            score.score(prepared, reviewed)


if __name__ == "__main__":
    unittest.main()
