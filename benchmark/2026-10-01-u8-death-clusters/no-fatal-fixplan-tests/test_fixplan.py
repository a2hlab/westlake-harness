import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "benchmark/2026-10-01-u8-death-clusters"
EVIDENCE = BASE / "no-fatal-fixplan-evidence"


def read_json(filename):
    return json.loads(filename.read_text())


def checksum(filename):
    return hashlib.sha256(filename.read_bytes()).hexdigest()


def selected_inputs(workspaces):
    override = os.environ.get("WESTLAKE_FIXPLAN_INPUTS")
    if override:
        return {row["key"]: row for row in read_json(Path(override))}
    legacy = read_json(ROOT / "benchmark/2026-10-01-u7-prospective/v1/inputs.json")["apps"]
    corpus = read_json(ROOT / "benchmark/2026-10-01-corpus-v2/results.json")["rows"]
    packages = {row["package"]: row for row in corpus}
    legacy_keys = {row["key"]: row for row in legacy}
    selected = {}
    for row in read_json(BASE / "no-fatal-fixplan.json")["rows"]:
        if row["key"] in legacy_keys:
            entry = legacy_keys[row["key"]]
            target = Path.home() / "a2hlab/app-inputs" / row["key"] / entry["selected_apk"]
        else:
            entry = packages[row["package"]]
            target = workspaces / "westlake-inputs/corpus-v2/apks" / Path(entry["apk_url"]).name
        selected[row["key"]] = {"path": str(target), "apk_sha256": row["apk_sha256"]}
    return selected


def validate_sources(sources):
    identities = set()
    for source in sources["sources"]:
        if source["id"] in identities:
            raise ValueError("duplicate source identity")
        identities.add(source["id"])
        if not re.fullmatch(r"[a-f0-9]{64}", source["sha256"]):
            raise ValueError("invalid source SHA")
        for snippet in source["snippets"]:
            if not snippet["lines"] or not (
                1 <= snippet["start_line"]
                <= snippet["start_line"] + len(snippet["lines"]) - 1
                <= source["line_count"]
            ):
                raise ValueError("invalid source coordinates")
        if source["tag"] is not None:
            if source["tag"] != "android-14.0.0_r1":
                raise ValueError("wrong AOSP tag")
            expected = source["sha256"] + "  " + source["path"].split("aosp-14.0.0_r1-src/", 1)[1]
            if source["manifest_entry"] != expected:
                raise ValueError("SHA manifest mismatch")
        elif not re.fullmatch(r"[a-f0-9]{40}", source["repository_head"]):
            raise ValueError("unidentified donor")
    return {source["id"]: source for source in sources["sources"]}


def validate_report(report, sources):
    source_map = validate_sources(sources)
    audit = read_json(BASE / "no-fatal-terminations.json")
    audited = {row["key"]: row for row in audit["rows"]}
    rows = report["rows"]
    if len(rows) != 11 or {row["key"] for row in rows} != set(audited):
        raise ValueError("wrong key cohort")
    if checksum(BASE / "no-fatal-terminations.json") != report["prior_audit"]["sha256"]:
        raise ValueError("frozen audit changed")
    for row in rows:
        if row["layer"] not in {"J", "native"}:
            raise ValueError("invalid repair layer")
        if row["apk_sha256"] != audited[row["key"]]["apk_sha256"]:
            raise ValueError("wrong APK identity")
        beneficiaries = set(row["beneficiary_keys"])
        if not beneficiaries <= set(audited) or row["expected_beneficiary_count"] != len(beneficiaries):
            raise ValueError("invalid beneficiary count")
        if row["predicted_new_lit"] is not None or not row["repair"] or not row["validation"]:
            raise ValueError("unsupported lit claim or missing proposal")
        if not row["source_files"]:
            raise ValueError("missing source coordinates")
        for reference in row["source_files"]:
            source = source_map[reference["source_id"]]
            if reference["file"] != source["path"] or not any(
                snippet["start_line"] <= reference["line"]
                < snippet["start_line"] + len(snippet["lines"])
                for snippet in source["snippets"]
            ):
                raise ValueError("source coordinate outside pinned snippet")


class ReportTests(unittest.TestCase):
    def test_eleven_keys_and_source_coordinates(self):
        report = read_json(BASE / "no-fatal-fixplan.json")
        validate_report(report, read_json(EVIDENCE / "sources.json"))
        self.assertEqual(report["counts"]["primary_J"], 4)
        self.assertEqual(report["counts"]["primary_native"], 7)
        document = (BASE / "no-fatal-fixplan.md").read_text()
        for row in report["rows"]:
            self.assertIn(row["key"], document)

    def test_duplicate_key_and_false_beneficiaries_rejected(self):
        report = read_json(BASE / "no-fatal-fixplan.json")
        sources = read_json(EVIDENCE / "sources.json")
        mutated = copy.deepcopy(report)
        mutated["rows"][0] = mutated["rows"][1]
        with self.assertRaises(ValueError):
            validate_report(mutated, sources)
        mutated = copy.deepcopy(report)
        mutated["rows"][0]["expected_beneficiary_count"] = 99
        with self.assertRaises(ValueError):
            validate_report(mutated, sources)

    def test_raw_evidence_identity_matches_adopted_audit(self):
        raw = read_json(EVIDENCE / "raw-lines.json")
        audit = read_json(BASE / "no-fatal-terminations.json")
        for row in audit["rows"]:
            evidence = raw[row["key"]]
            self.assertEqual(evidence["sha256"], row["inputs"]["hilog.txt"])
            self.assertEqual(evidence["target_pids"], row["target_pids"])
            self.assertEqual(evidence["file"], row["source"] + "/hilog.txt")
            self.assertTrue(evidence["lines"])


class SourceTests(unittest.TestCase):
    def test_source_manifest_and_artifact_owner(self):
        sources = read_json(EVIDENCE / "sources.json")
        validate_sources(sources)
        native = read_json(EVIDENCE / "native.json")
        self.assertEqual(native["artifact_identity"]["exit_code"], 0)
        artifacts = {item["name"]: item for item in native["artifacts"]}
        self.assertIn("android_set_abort_message", artifacts["libbionic_compat.so"]["exports"])
        self.assertNotIn("android_dlopen_ext", artifacts["libbionic_compat.so"]["exports"])
        self.assertIn("libEGL.so", artifacts["libhwui.so"]["needed"])
        self.assertFalse(sources["predicate_absence"]["found"])
        report = read_json(BASE / "no-fatal-fixplan.json")
        for symbol in report["shared_native_symbols"]:
            consumers = {
                item["key"] for item in native["consumers"]
                if symbol["symbol"] in {name.split("@", 1)[0] for name in item["undefined"]}
            }
            self.assertEqual(set(symbol["importing_keys"]), consumers)
            self.assertEqual(symbol["count"], len(consumers))

    def test_bad_hash_tag_and_coordinates_rejected(self):
        original = read_json(EVIDENCE / "sources.json")
        for field, value in [("sha256", "0" * 64), ("tag", "android-16.0.0_r4")]:
            mutated = copy.deepcopy(original)
            mutated["sources"][0][field] = value
            with self.assertRaises(ValueError):
                validate_sources(mutated)
        report = read_json(BASE / "no-fatal-fixplan.json")
        report["rows"][0]["source_files"][0]["line"] = 0
        with self.assertRaises(ValueError):
            validate_report(report, original)

    def test_local_originals_when_requested(self):
        if os.environ.get("WESTLAKE_FIXPLAN_REPLAY") != "1":
            self.skipTest("external originals replay requested separately")
        workspaces = Path(os.environ["WORKSPACES"])
        sources = read_json(EVIDENCE / "sources.json")
        for source in sources["sources"]:
            target = workspaces / source["path"]
            self.assertEqual(checksum(target), source["sha256"])
            lines = target.read_text().splitlines()
            for snippet in source["snippets"]:
                begin = snippet["start_line"] - 1
                self.assertEqual(lines[begin:begin + len(snippet["lines"])], snippet["lines"])
        for evidence in read_json(EVIDENCE / "raw-lines.json").values():
            target = workspaces / evidence["file"]
            self.assertEqual(checksum(target), evidence["sha256"])
            lines = target.read_text(errors="replace").splitlines()
            for entry in evidence["lines"]:
                expected = lines[entry["line"] - 1].replace(str(workspaces), "$WORKSPACES")
                expected = expected.replace(str(Path.home()), "$HOME")
                self.assertEqual(expected, entry["text"])
        native = read_json(EVIDENCE / "native.json")
        for artifact in native["artifacts"]:
            self.assertEqual(checksum(workspaces / artifact["path"]), artifact["sha256"])
        inputs = selected_inputs(workspaces)
        dex = read_json(EVIDENCE / "dex.json")
        consumers = native["consumers"]
        for key in {item["key"] for item in dex + consumers}:
            self.assertEqual(checksum(Path(inputs[key]["path"])), inputs[key]["apk_sha256"])
            with zipfile.ZipFile(inputs[key]["path"]) as archive:
                for item in [entry for entry in dex if entry["key"] == key]:
                    self.assertEqual(hashlib.sha256(archive.read(item["dex"])).hexdigest(), item["dex_sha256"])
                for item in [entry for entry in consumers if entry["key"] == key]:
                    self.assertEqual(hashlib.sha256(archive.read(item["apk_member"])).hexdigest(), item["sha256"])


class UncertaintyTests(unittest.TestCase):
    def test_native_surface_and_toutiao_bootstrap_not_j_defaults(self):
        rows = {row["key"]: row for row in read_json(BASE / "no-fatal-fixplan.json")["rows"]}
        self.assertEqual(rows["fd-plus"]["layer"], "native")
        self.assertEqual(rows["toutiao"]["layer"], "native")
        native = read_json(EVIDENCE / "native.json")
        self.assertIn("mov\tx0, xzr", native["runtime_lock_disassembly"])
        flipped = next(item for item in native["consumers"] if item["key"] == "toutiao")
        self.assertIn("libstdc++.so", flipped["needed"])
        self.assertFalse(flipped["stdcxx_symbols_imported"])
        dex = read_json(EVIDENCE / "dex.json")
        main = next(item for item in dex if item["key"] == "toutiao" and item["method"] == "<init>" and "MainActivity" in item["class"])
        call = next(item for item in main["instructions"] if item["offset"] == 0x46)
        self.assertIn("Boolean;->booleanValue", call["output"])

    def test_unknown_sigkill_not_promoted_to_death_cure(self):
        report = read_json(BASE / "no-fatal-fixplan.json")
        self.assertEqual(report["counts"]["proven_SIGKILL_death_unlocks"], 0)
        self.assertIsNone(report["counts"]["predicted_new_lit"])
        for row in report["rows"]:
            if row["key"] in {"fd-fennec_fdroid", "firefox"}:
                self.assertIn("unknown", row["confidence"])
                self.assertIn("unknown", row["limits"])
                self.assertEqual(row["expected_beneficiary_count"], 2)
                self.assertIsNone(row["predicted_new_lit"])
            if row["key"] == "ppsspp":
                self.assertIn("not proven", row["limits"])

    def test_no_fake_egl_or_gnu_return_abi(self):
        report = read_json(BASE / "no-fatal-fixplan.json")
        flowit = next(row for row in report["rows"] if row["key"] == "cv2-com-bytehamster-flowitgame")
        self.assertIn("full-frame", flowit["repair"])
        self.assertIn("no false extension", " ".join(flowit["validation"]))
        native = read_json(EVIDENCE / "native.json")
        self.assertEqual(native["flowitgame_arm64_native_members"], 0)
        for row in report["rows"]:
            if row["key"] in {"firefox", "fd-fennec_fdroid"}:
                self.assertIn("char*", row["repair"])
                self.assertIn("never alias int-return", " ".join(row["validation"]))


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0], *sys.argv[1:]])
