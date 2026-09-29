import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import compare_runs

A5 = "5ea34a4500000000000000001123012c"
B6 = "61b0657200000000000000000324012c"


def make(root, serial, shas, facts):
    d = pathlib.Path(root) / serial
    d.mkdir(parents=True)
    (d / "runtime-fingerprint.txt").write_text("".join(f"{s * 64}  {p}\n" for p, s in shas.items()))
    (d / "facts.txt").write_text("".join(
        f"{k:<20} shots 2/2  alive t5={a} t20={b}  child_hilog=1  foreground_unconfirmed\n"
        for k, (a, b) in facts.items()))
    return str(d.parent)


class CompareRunsTests(unittest.TestCase):
    def test_installer_only_across_boards_is_two_variables(self):
        with tempfile.TemporaryDirectory() as t:
            a = make(f"{t}/a", A5, {"/lib/art.so": "1", "/lib/bms.so": "2"}, {"tusky": ("yes", "yes")})
            b = make(f"{t}/b", B6, {"/lib/art.so": "1", "/lib/bms.so": "3"}, {"tusky": ("yes", "no")})
            out = compare_runs.compare(a, b)
        self.assertEqual(out[0], "variables: 2")
        self.assertIn("key tusky", out)
        self.assertTrue(out[-1].startswith("verdict: 2 variables differ"))

    def test_installer_pair_on_one_board_is_one_variable(self):
        with tempfile.TemporaryDirectory() as t:
            pair = ("/system/lib64/libbms.z.so", "/system/lib64/libapk_installer.so")
            a = make(f"{t}/a", B6, {pair[0]: "1", pair[1]: "2"}, {})
            b = make(f"{t}/b", B6, {pair[0]: "3", pair[1]: "4"}, {})
            out = compare_runs.compare(a, b)
        self.assertEqual(out[0], "variables: 1")
        self.assertTrue(out[1].startswith("  installer: "))

    def test_reboot_between_runs_is_a_variable(self):
        with tempfile.TemporaryDirectory() as t:
            a = make(f"{t}/a", B6, {"/lib/art.so": "1"}, {})
            b = make(f"{t}/b", B6, {"/lib/art.so": "1"}, {})
            for run, boot in ((a, "aaaaaaaa-1"), (b, "bbbbbbbb-2")):
                (pathlib.Path(run) / B6 / "baseline.json").write_text(f'{{"boot_id": "{boot}"}}')
            out = compare_runs.compare(a, b)
        self.assertEqual(out[:2], ["variables: 1", "  reboot aaaaaaaa -> bbbbbbbb"])

    def test_same_board_one_file_is_single_variable(self):
        with tempfile.TemporaryDirectory() as t:
            a = make(f"{t}/a", A5, {"/fw/runtime.jar": "4"}, {"x": ("no", "no")})
            b = make(f"{t}/b", A5, {"/fw/runtime.jar": "5"}, {"x": ("yes", "yes")})
            out = compare_runs.compare(a, b)
        self.assertEqual(out[0], "variables: 1")
        self.assertTrue(out[-1].startswith("verdict: single-variable"))

    def test_nothing_differs_but_key_flips_is_nondeterminism(self):
        with tempfile.TemporaryDirectory() as t:
            a = make(f"{t}/a", A5, {"/lib/art.so": "1"}, {"zigzag": ("yes", "yes")})
            b = make(f"{t}/b", A5, {"/lib/art.so": "1"}, {"zigzag": ("no", "no")})
            out = compare_runs.compare(a, b)
        self.assertEqual(out[0], "variables: 0")
        self.assertIn("key zigzag", out)
        self.assertTrue(out[-1].startswith("verdict: no variable differs"))

    def test_file_present_in_one_run_only_counts(self):
        with tempfile.TemporaryDirectory() as t:
            a = make(f"{t}/a", A5, {"/lib/art.so": "1"}, {})
            b = make(f"{t}/b", A5, {"/lib/art.so": "1", "/lib/new.so": "6"}, {})
            out = compare_runs.compare(a, b)
        self.assertIn("  /lib/new.so absent -> 66666666", out)


if __name__ == "__main__":
    unittest.main()
