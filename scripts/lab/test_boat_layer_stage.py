#!/usr/bin/env python3
"""Known-answer / contract tests for scripts/lab/boat_layer_stage.sh (OFFLINE, zero board).

boat_layer_stage.sh is the installer-free Boat-layer path discovered during the 5ea #91
investigation: the Boat overlay is a separate init job that only reads $ROOT/sources-boat, so
the layer can be added/removed by staging (or removing) those 6 files + one reboot — WITHOUT the
installer that re-archives /system/android (the 5ea incident). These tests pin that safety contract
so it cannot silently drift before any board step.

Run:  python3 -m unittest -v scripts/lab/test_boat_layer_stage.py
   or just:  python3 scripts/lab/test_boat_layer_stage.py
"""
import os
import re
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "boat_layer_stage.sh")
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
OVERLAY = os.path.join(REPO, "benchmark", "2026-10-10-u13-autostart", "payload",
                       "scripts", "westlake-u13-boat-overlay.sh")

# The 6 signed Boat files and their canonical SHAs (source of truth = the payload overlay script).
EXPECT_SHA = {
    "liboh_adapter_bridge.so": "8ab85446f8b386c4a649576326d5f393669b3a22529874fb673eea7c3b1cd71e",
    "oh-adapter-runtime.jar": "6333bcab4ca2daad03965712deac6adf028a6ff0dfac04fc8ea91af177828852",
    "liboh_android_runtime.so": "adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130",
    "libunity.so": "1bea0fae1e6e76db15f17fca2bfa91b9c303ce278d6a4dcfba6af233b68b64ac",
    "libil2cpp.so": "f6b806b5c55e702b98caa2e85d2f9afb678bc47dcc4067017b33f5269afed746",
    "libwestlake_bionic_signal_box.so": "7a931c79c0be28468bdd02a626a637431f2447f5fd0aba87176e5acdb071f5da",
}


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class Syntax(unittest.TestCase):
    def test_script_exists_and_executable(self):
        self.assertTrue(os.path.isfile(SCRIPT), "boat_layer_stage.sh missing")
        self.assertTrue(os.access(SCRIPT, os.X_OK), "boat_layer_stage.sh not executable")

    def test_bash_syntax_ok(self):
        r = subprocess.run(["bash", "-n", SCRIPT], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, "bash -n failed: " + r.stderr)


class Files(unittest.TestCase):
    def setUp(self):
        self.text = read(SCRIPT)

    def test_all_six_files_and_shas_present(self):
        for name, sha in EXPECT_SHA.items():
            self.assertIn(name, self.text, "missing boat file: " + name)
            self.assertIn(sha, self.text, "missing/wrong SHA for " + name)

    def test_exactly_six_boat_shas(self):
        shas = set(re.findall(r"\b[0-9a-f]{64}\b", self.text))
        self.assertEqual(shas, set(EXPECT_SHA.values()),
                         "the script must pin exactly the 6 Boat SHAs, no more/less")

    @unittest.skipUnless(os.path.isfile(OVERLAY), "payload overlay not present in this tree")
    def test_shas_match_payload_overlay(self):
        overlay = read(OVERLAY)
        for name, sha in EXPECT_SHA.items():
            self.assertIn(sha, overlay,
                          "SHA for %s drifted from payload overlay (source of truth)" % name)


class SafetyNegativeInvariants(unittest.TestCase):
    """The whole point of this path: never do what the installer did to 5ea."""
    def setUp(self):
        self.text = read(SCRIPT)
        # executable lines only (strip comments) so documentation mentions don't trip the checks
        self.code = "\n".join(
            ln for ln in self.text.splitlines()
            if ln.strip() and not ln.lstrip().startswith("#"))

    def test_never_calls_installer(self):
        self.assertNotIn("install-westlake-u13-autostart", self.code,
                         "must never invoke the installer")

    def test_never_remounts_system(self):
        self.assertNotRegex(self.code, r"mount\s+-o\s+(remount|rw)",
                            "must never remount /system")
        self.assertNotRegex(self.code, r"\bremount\b", "no remount of any kind")

    def test_no_setenforce(self):
        self.assertNotIn("setenforce", self.code, "sealed enforcement: never setenforce")

    def test_never_mutates_seq1_or_base_archive(self):
        # reading seq1 (find -type f) is allowed; writing/moving/removing/sending to it is not.
        for pat in [r"rm\s+.*sources/seq1", r"mv\s+.*sources/seq1", r"cp\s+.*sources/seq1",
                    r"rm\s+-rf?\s+\$?\{?SEQ1", r"file\s+send\s+\S+\s+\S*sources/seq",
                    r">\s*\$?\{?SEQ1", r"mkdir\s+.*sources/seq1"]:
            self.assertNotRegex(self.code, pat, "must not mutate the U13 base archive: " + pat)
        # the ONLY sources/seq1 reference may be the read-only `find ... -type f`
        for ln in self.code.splitlines():
            if "sources/seq1" in ln or "$SEQ1" in ln or "{SEQ1" in ln:
                self.assertRegex(ln, r"find .*-type f|SEQ1=|# ",
                                 "seq1 referenced outside a read-only find: " + ln)

    def test_does_not_reboot_itself(self):
        # `target boot` may only appear inside printed guidance, never as an executed hdc command.
        for ln in self.code.splitlines():
            if "target boot" in ln:
                self.assertNotRegex(ln.strip(), r'^"\$HDC"\s+-t\s+"\$SERIAL"\s+target\s+boot',
                                    "script must print, not execute, target boot: " + ln)


class DryRunDefault(unittest.TestCase):
    def setUp(self):
        self.text = read(SCRIPT)

    def test_execute_defaults_off(self):
        self.assertRegex(self.text, r"EXECUTE=0", "EXECUTE must default to 0 (dry-run)")

    def test_board_mutations_are_execute_guarded(self):
        # every board-mutating primitive must sit under an `if [ "$EXECUTE" -eq 1 ]` branch.
        # Heuristic: the file-send and the reverse mv must be guarded.
        self.assertRegex(self.text, r'EXECUTE"?\s*-eq\s*1',
                         "must gate mutations on EXECUTE")
        send_lines = [ln for ln in self.text.splitlines()
                      if "file send" in ln and not ln.lstrip().startswith("#")]
        self.assertTrue(send_lines, "expected a file-send line")
        # the reverse mv of sources-boat must exist and be an EXEC (not dry) action
        self.assertRegex(self.text, r"mv \$BARCH \$held", "reverse must move sources-boat aside")


class ForwardReverseSeparation(unittest.TestCase):
    def setUp(self):
        self.text = read(SCRIPT)

    def test_forward_stages_reverse_removes(self):
        # forward uses `file send` (adds); reverse uses `mv $BARCH` (removes); not vice-versa.
        stage_fn = re.search(r"stage\(\)\{.*?\n\}", self.text, re.S)
        reverse_fn = re.search(r"reverse\(\)\{.*?\n\}", self.text, re.S)
        self.assertTrue(stage_fn and reverse_fn, "stage() and reverse() must exist")
        self.assertIn("file send", stage_fn.group(0), "stage must send files")
        self.assertNotIn("file send", reverse_fn.group(0), "reverse must not send files")
        self.assertIn("mv $BARCH", reverse_fn.group(0), "reverse must move sources-boat aside")
        self.assertNotIn("mv $BARCH", stage_fn.group(0), "stage must not move sources-boat")


class CfgAndLabelContract(unittest.TestCase):
    def setUp(self):
        self.text = read(SCRIPT)

    def test_confirms_boat_job_never_edits_cfg(self):
        self.assertIn("westlake-u13-boat-overlay", self.text, "must know the boat job name")
        self.assertRegex(self.text, r"grep -q .*BOAT_JOB", "must confirm the boat job in cfg")
        # refuses (exit) when the boat job is absent, and says it won't edit the cfg
        self.assertIn("never edits the cfg", self.text)
        # it reads the cfg (cat) but never writes it (no redirection into $CFG, no cfg edit tool)
        self.assertNotRegex(self.text, r">\s*\$?\{?CFG", "must not write the cfg")

    def test_labels_via_single_recipe(self):
        self.assertIn("selinux_label_recipe.sh", self.text, "must use the single label recipe")
        self.assertRegex(self.text, r'recipe_label\(\)\{ sh "\$RECIPE" context',
                         "label must come from the recipe's context mode")

    def test_sha_verified_after_send(self):
        self.assertIn("STAGED_SHA", self.text, "must verify staged SHA on the board after send")


class NoUserPaths(unittest.TestCase):
    def test_no_hardcoded_user_home(self):
        text = read(SCRIPT)
        self.assertNotRegex(text, r"/Users/[A-Za-z0-9._-]+", "no hardcoded /Users/<name>")
        self.assertNotRegex(text, r"/home/[A-Za-z0-9._-]+", "no hardcoded /home/<name>")


if __name__ == "__main__":
    unittest.main(verbosity=2)
