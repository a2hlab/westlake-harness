#!/usr/bin/env python3
"""Tests for the OPTIONAL v1 boot-permissive switch (cc-t3 #91, default OFF; needs user approval to use).

The switch lives in a NEW file westlake-u13-recover-v3.sh (= v2 recover.sh + the switch block); the v2
recover.sh is left byte-for-byte unchanged (it is cited by knowledge/gates/selinux-label-recipe.json, so
it must never be overwritten). Covers:
  A. the recover-v3.sh switch block run under sh with stubbed setenforce/getenforce:
     file missing / wrong-content / exactly "permissive" -> setenforce 0 ONLY for permissive; never implicit.
  B. v2 recover.sh SHA is unchanged, and v3 == v2 + ONLY the switch block (functional diff).
  C. demo_seal_61b plan-driven SELinux criterion: expected_enforce mapping + validate() fail-closed requirement.

Run:  python3 -m unittest -v scripts/lab/test_selinux_mode_switch.py
"""
import difflib
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
SCR = os.path.join(REPO, "benchmark/2026-10-10-u13-autostart/payload/scripts")
RECOVER_V2 = os.path.join(SCR, "westlake-u13-recover.sh")
RECOVER_V3 = os.path.join(SCR, "westlake-u13-recover-v3.sh")
# pinned pristine v2 recover.sh (a2hlab/master) — this file MUST NOT change (frozen-gate cited)
V2_SHA256 = "95eb4f6efd3c48853211ec63cab3da778a098152c545454a09fe6ec74c926b25"
sys.path.insert(0, HERE)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def code_lines(path):
    return [l for l in read(path).splitlines() if l.strip() and not l.lstrip().startswith("#")]


def extract_switch_block():
    m = re.search(r"# >>> selinux-mode-switch BEGIN.*?\n(.*?)# <<< selinux-mode-switch END", read(RECOVER_V3), re.S)
    assert m, "switch markers not found in recover-v3.sh"
    return m.group(1)


def run_switch(mode_file_content):
    """Run the REAL extracted v3 switch block under sh, stubbed log/setenforce/getenforce, temp ROOT."""
    block = extract_switch_block()
    with tempfile.TemporaryDirectory() as tmp:
        if mode_file_content is not None:
            with open(os.path.join(tmp, "selinux-mode"), "w") as fh:
                fh.write(mode_file_content)
        calls = os.path.join(tmp, "setenforce.calls")
        harness = f"""
set -u
ROOT={tmp}
RECEIPT={tmp}/receipt.env
LOG={tmp}/recover.log
: > "$RECEIPT"
log(){{ printf '%s\\n' "$*" >> "$LOG"; }}
setenforce(){{ printf 'setenforce %s\\n' "$*" >> {calls}; echo permissive > {tmp}/.enforced0; }}
getenforce(){{ if [ -f {tmp}/.enforced0 ]; then echo Permissive; else echo Enforcing; fi; }}
{block}
printf 'REQUESTED=%s\\n' "$selinux_requested"
printf 'ACTUAL=%s\\n' "$selinux_actual"
"""
        out = subprocess.run(["sh", "-c", harness], capture_output=True, text=True)
        assert out.returncode == 0, "switch block errored: " + out.stderr
        requested = re.search(r"REQUESTED=(\w+)", out.stdout).group(1)
        actual = re.search(r"ACTUAL=(\w+)", out.stdout).group(1)
        receipt = read(os.path.join(tmp, "receipt.env"))
        return requested, actual, os.path.exists(calls), receipt


class RecoverV3SwitchBehaviour(unittest.TestCase):
    def test_file_missing_stays_enforcing(self):
        requested, actual, called, receipt = run_switch(None)
        self.assertEqual(requested, "enforcing")
        self.assertFalse(called, "setenforce must NOT run when the file is absent")
        self.assertEqual(actual, "Enforcing")
        self.assertIn("selinux_mode=Enforcing", receipt)

    def test_wrong_content_stays_enforcing(self):
        for bad in ["enforcing", "Permissive", "permissive\nextra", "0", "", " permissive "]:
            requested, actual, called, _ = run_switch(bad)
            self.assertEqual(requested, "enforcing", "content %r must not switch" % bad)
            self.assertFalse(called, "setenforce must NOT run for content %r" % bad)
            self.assertEqual(actual, "Enforcing")

    def test_exactly_permissive_switches(self):
        for good in ["permissive", "permissive\n"]:  # trailing newline tolerated ($(cat) strips it)
            requested, actual, called, receipt = run_switch(good)
            self.assertEqual(requested, "permissive", "content %r must switch" % good)
            self.assertTrue(called, "setenforce 0 must run for content %r" % good)
            self.assertEqual(actual, "Permissive")
            self.assertIn("selinux_mode=Permissive", receipt)


class RecoverV3Contract(unittest.TestCase):
    def test_switch_default_off_one_guarded_setenforce(self):
        block = extract_switch_block()
        invocations = re.findall(r"(?m)^\s*setenforce 0\b", block)
        self.assertEqual(len(invocations), 1, "exactly one real setenforce in the block")
        self.assertRegex(block, r'\[ -f "\$SELINUX_MODE_FILE" \] && \[ "\$\(cat "\$SELINUX_MODE_FILE".*\)" = permissive \]')

    def test_v3_only_real_setenforce_is_guarded(self):
        invocations = re.findall(r"(?m)^\s*setenforce 0\b", read(RECOVER_V3))
        self.assertEqual(len(invocations), 1, "recover-v3.sh runs setenforce only in the guarded switch")

    def test_v3_receipt_records_mode(self):
        self.assertIn("selinux_mode=$", read(RECOVER_V3))
        self.assertIn("selinux_requested=$", read(RECOVER_V3))


class V2UnchangedV3IsV2PlusSwitch(unittest.TestCase):
    def test_v2_recover_sha_unchanged(self):
        import hashlib
        got = hashlib.sha256(read(RECOVER_V2).encode()).hexdigest()
        self.assertEqual(got, V2_SHA256, "v2 recover.sh must NOT change (frozen-gate cited)")

    def test_v2_has_no_real_setenforce(self):
        self.assertEqual(re.findall(r"(?m)^\s*setenforce 0\b", read(RECOVER_V2)), [],
                         "v2 recover.sh must never run setenforce")

    def test_v3_is_v2_plus_only_the_switch(self):
        v2, v3 = code_lines(RECOVER_V2), code_lines(RECOVER_V3)
        sm = difflib.SequenceMatcher(a=v2, b=v3)
        removed, added = [], []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag in ("replace", "delete"):
                removed += v2[i1:i2]
            if tag in ("replace", "insert"):
                added += v3[j1:j2]
        self.assertEqual(removed, [], "no v2 functional line may be removed/changed in v3")
        # every added functional line must belong to the switch block (markers region)
        block_lines = set(l.strip() for l in extract_switch_block().splitlines() if l.strip())
        for a in added:
            self.assertIn(a.strip(), block_lines, "v3 adds a line outside the switch block: " + a)
        self.assertEqual(len(added), 10, "the switch adds exactly its block's functional lines")


class SealCriterionPlanDriven(unittest.TestCase):
    def _wf(self, selinux_mode):
        import demo_seal_61b as ds
        plan = {"reference": {"kind": "5cd"}, "selinux_mode": selinux_mode}
        with tempfile.TemporaryDirectory() as tmp:
            return ds.Workflow(plan, tmp, preview=True, mode="v1", reference="5cd")

    def test_expected_enforce_mapping_enforcing(self):
        self.assertEqual(self._wf("enforcing").expected_enforce, "Enforcing")

    def test_expected_enforce_mapping_permissive(self):
        self.assertEqual(self._wf("permissive").expected_enforce, "Permissive")

    def test_validate_requires_explicit_selinux_mode(self):
        import demo_seal_61b as ds
        base = {"schema": "demo-seal-61b-orchestration/v1", "serial": ds.SERIAL, "execution_enabled": True, "mode": "v1"}
        with self.assertRaises(ValueError) as cm:
            ds.validate(dict(base), authorization="/nonexistent", plan_sha="x", mode="v1")
        self.assertIn("selinux_mode", str(cm.exception))
        with self.assertRaises(ValueError) as cm2:
            ds.validate(dict(base, selinux_mode="loose"), authorization="/nonexistent", plan_sha="x", mode="v1")
        self.assertIn("selinux_mode", str(cm2.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
