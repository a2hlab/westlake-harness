import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import compare_runs

A5 = "5ea34a4500000000000000001123012c"
B6 = "61b0657200000000000000000324012c"


def make(root, serial, shas, facts, boot=None):
    d = pathlib.Path(root) / serial
    d.mkdir(parents=True)
    (d / "runtime-fingerprint.txt").write_text("".join(f"{s * 64}  {p}\n" for p, s in shas.items()))
    if boot is not None:
        (d / "boot-image-fingerprint.txt").write_text("".join(f"{s * 64}  {p}\n" for p, s in boot.items()))
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

    def test_launch_only_run_counts_app_data_as_a_variable(self):
        with tempfile.TemporaryDirectory() as t:
            a = make(f"{t}/a", A5, {"/fw/runtime.jar": "4"}, {})
            b = make(f"{t}/b", A5, {"/fw/runtime.jar": "5"}, {})
            (pathlib.Path(b) / A5 / "plan.json").write_text('{"options": {"reinstall": false, "launch_only": true}}')
            out = compare_runs.compare(a, b)
        self.assertEqual(out[0], "variables: 2")
        self.assertIn("  app data carried over from earlier runs in B (no --reinstall)", out)

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

    def test_boot_image_swap_with_same_runtime_is_one_variable(self):
        # T6 (2026-09-30): 27 boot-image files bind-swapped while runtime-fingerprint.txt stayed the same
        img_a = {f"/fw/arm64/boot-{i}.oat": "1" for i in range(27)}
        img_b = {f"/fw/arm64/boot-{i}.oat": "2" for i in range(27)}
        with tempfile.TemporaryDirectory() as t:
            a = make(f"{t}/a", A5, {"/lib/art.so": "1"}, {"hw": ("yes", "yes")}, img_a)
            b = make(f"{t}/b", A5, {"/lib/art.so": "1"}, {"hw": ("no", "no")}, img_b)
            out = compare_runs.compare(a, b)
        self.assertEqual(out[0], "variables: 1")
        self.assertTrue(out[1].startswith("  boot image: 27 file(s) differ"), out[1])

    def test_same_boot_image_adds_no_variable(self):
        img = {"/fw/arm64/boot.oat": "1"}
        with tempfile.TemporaryDirectory() as t:
            a = make(f"{t}/a", A5, {"/fw/runtime.jar": "4"}, {}, img)
            b = make(f"{t}/b", A5, {"/fw/runtime.jar": "5"}, {}, img)
            out = compare_runs.compare(a, b)
        self.assertEqual(out[0], "variables: 1")
        self.assertFalse(any("boot image" in l for l in out))

    def test_missing_boot_image_record_is_a_note_not_a_variable(self):
        with tempfile.TemporaryDirectory() as t:
            a = make(f"{t}/a", A5, {"/lib/art.so": "1"}, {})
            b = make(f"{t}/b", A5, {"/lib/art.so": "1"}, {}, {"/fw/arm64/boot.oat": "1"})
            out = compare_runs.compare(a, b)
        self.assertEqual(out[0], "variables: 0")
        self.assertTrue(any(l.startswith("note: boot-image-fingerprint.txt missing in A") for l in out))

    def test_same_library_under_two_alias_paths_is_one_variable(self):
        # 5ea bisect step 2: libapp_native_loader.so in lib64/ and route-a/<hash>/ changed together
        paths = ("/system/android/lib64/libapp_native_loader.so",
                 "/system/lib64/westlake/route-a/74d1/libapp_native_loader.so")
        with tempfile.TemporaryDirectory() as t:
            a = make(f"{t}/a", A5, {p: "7" for p in paths}, {})
            b = make(f"{t}/b", A5, {p: "e" for p in paths}, {})
            out = compare_runs.compare(a, b)
        self.assertEqual(out[0], "variables: 1")
        self.assertIn("(+1 alias path(s) with the same change)", out[1])

    def test_alias_paths_changing_differently_stay_separate(self):
        paths = ("/a/libx.so", "/b/libx.so")
        with tempfile.TemporaryDirectory() as t:
            a = make(f"{t}/a", A5, {paths[0]: "1", paths[1]: "1"}, {})
            b = make(f"{t}/b", A5, {paths[0]: "2", paths[1]: "3"}, {})
            out = compare_runs.compare(a, b)
        self.assertEqual(out[0], "variables: 2")

    def test_flaky_key_single_variable_needs_repeats(self):
        with tempfile.TemporaryDirectory() as t:
            a = make(f"{t}/a", A5, {"/lib/anl.so": "7"}, {"fd-noice": ("yes", "yes")})
            b = make(f"{t}/b", A5, {"/lib/anl.so": "e"}, {"fd-noice": ("yes", "yes")})
            out = compare_runs.compare(a, b)
        self.assertEqual(out[0], "variables: 1")
        self.assertTrue(out[-1].startswith("verdict: flaky key(s) fd-noice"), out[-1])

    def test_non_flaky_key_single_variable_unchanged(self):
        with tempfile.TemporaryDirectory() as t:
            a = make(f"{t}/a", A5, {"/lib/anl.so": "7"}, {"aegis": ("yes", "no")})
            b = make(f"{t}/b", A5, {"/lib/anl.so": "e"}, {"aegis": ("yes", "yes")})
            out = compare_runs.compare(a, b)
        self.assertTrue(out[-1].startswith("verdict: single-variable"), out[-1])

    def test_flaky_key_among_others_adds_caution(self):
        with tempfile.TemporaryDirectory() as t:
            a = make(f"{t}/a", A5, {"/lib/anl.so": "7"}, {"aegis": ("yes", "yes"), "fd-noice": ("yes", "yes")})
            b = make(f"{t}/b", A5, {"/lib/anl.so": "e"}, {"aegis": ("yes", "yes"), "fd-noice": ("yes", "yes")})
            out = compare_runs.compare(a, b)
        self.assertTrue(out[-1].startswith("verdict: single-variable"), out[-1])
        self.assertTrue(any(l.startswith("caution: flaky key(s) fd-noice") for l in out))


if __name__ == "__main__":
    unittest.main()
