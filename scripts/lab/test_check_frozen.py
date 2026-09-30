import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_frozen

SHA_A, SHA_B = "a" * 64, "b" * 64


def registry(d, sources=()):
    r = pathlib.Path(d) / "frozen.json"
    r.write_text(json.dumps({"entries": [{
        "id": "FZ-T", "artifacts": [{"path": "/system/lib64/libx.so", "sha256": SHA_A}],
        "sources": list(sources), "verified_apps": [{"app": "a1"}, {"app": "a2"}]}]}))
    return str(r)


class CheckFrozenTests(unittest.TestCase):
    def test_fingerprint_with_frozen_hash_passes(self):
        with tempfile.TemporaryDirectory() as d:
            fp = pathlib.Path(d) / "fp.txt"
            fp.write_text(f"{SHA_A}  /system/lib64/libx.so\n{SHA_B}  /system/lib64/other.so\n")
            self.assertEqual(check_frozen.main(["--registry", registry(d), "--fingerprint", str(fp)]), 0)

    def test_changed_frozen_artifact_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            fp = pathlib.Path(d) / "fp.txt"
            fp.write_text(f"{SHA_B}  /system/lib64/libx.so\n")
            self.assertEqual(check_frozen.main(["--registry", registry(d), "--fingerprint", str(fp)]), 1)

    def test_package_live_hash_is_checked(self):
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / "package.json").write_text(json.dumps({"live_hashes": {"/system/lib64/libx.so": SHA_B}}))
            self.assertEqual(check_frozen.main(["--registry", registry(d), "--package", d]), 1)

    def test_input_not_touching_the_artifact_passes(self):
        with tempfile.TemporaryDirectory() as d:
            fp = pathlib.Path(d) / "fp.txt"
            fp.write_text(f"{SHA_B}  /system/lib64/other.so\n")
            self.assertEqual(check_frozen.main(["--registry", registry(d), "--fingerprint", str(fp)]), 0)

    def test_edited_or_missing_frozen_source_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            src = pathlib.Path(d) / "src" / "Fix.java"
            src.parent.mkdir()
            src.write_text("class Fix {}\n")
            blob = check_frozen.git_blob(src)
            reg = registry(d, [{"repo_path": "src/Fix.java", "blob": blob}])
            self.assertEqual(check_frozen.main(["--registry", reg, "--source-root", d]), 0)
            src.write_text("class Fix { int changed; }\n")
            self.assertEqual(check_frozen.main(["--registry", reg, "--source-root", d]), 1)
            src.unlink()
            self.assertEqual(check_frozen.main(["--registry", reg, "--source-root", d]), 1)


class RegistryTests(unittest.TestCase):
    V1 = {"id": "FZ-V", "version": 1, "status": "frozen", "history": [],
          "verified_apps": [{"app": "a1"}, {"app": "a2"}], "artifacts": [], "sources": []}

    def v2(self, **change):
        c = {"reason": "defect", "compare_runs": "cmp.txt", "full_sweep": "sweep/", "approved_by": "outer",
             "reverified": ["a1", "a2"]}
        c.update(change)
        return dict(self.V1, version=2, history=[dict(self.V1)], change=c)

    def test_well_formed_first_version_passes(self):
        self.assertEqual(check_frozen.validate([self.V1]), [])

    def test_single_app_evidence_is_not_enough(self):
        self.assertTrue(check_frozen.validate([dict(self.V1, verified_apps=[{"app": "a1"}])]))

    def test_outer_may_register_a_defect_fix_that_relights_every_app(self):
        self.assertEqual(check_frozen.validate([self.v2()]), [])

    def test_new_version_must_relight_all_previous_apps(self):
        self.assertTrue(any("not re-lit" in p for p in check_frozen.validate([self.v2(reverified=["a1"])])))

    def test_new_version_needs_an_allowed_reason(self):
        self.assertTrue(check_frozen.validate([self.v2(reason="cleanup")]))

    def test_removal_needs_the_user(self):
        self.assertTrue(check_frozen.validate([dict(self.V1, status="removed", removed={"approved_by": "outer"})]))
        self.assertEqual(check_frozen.validate([dict(self.V1, status="removed", removed={"approved_by": "user"})]), [])

    def test_removed_entry_is_not_enforced(self):
        self.assertEqual(check_frozen.active([dict(self.V1, status="removed")]), [])


if __name__ == "__main__":
    unittest.main()
