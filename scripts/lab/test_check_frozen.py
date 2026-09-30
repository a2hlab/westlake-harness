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
        "sources": list(sources)}]}))
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


if __name__ == "__main__":
    unittest.main()
