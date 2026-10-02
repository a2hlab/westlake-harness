import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from validation import ABI_MEMBER, BASES, T8_BASES, INSTALLER, INSTALLER_PATHS, OLD_ABI, check_base, check_delta, check_disabled, check_local_plan, check_image_approval, map_pending


class BindingTests(unittest.TestCase):
    def test_explicit_variants(self):
        identity = dict(expected={target: INSTALLER for target in INSTALLER_PATHS})
        for variant, digest in BASES.items():
            check_base(variant, digest, digest, identity)
        with self.assertRaises(ValueError):
            check_base("61b", BASES["common"], BASES["common"], identity)

    def test_installer_rejected(self):
        identity = dict(expected={target: INSTALLER for target in INSTALLER_PATHS})
        identity["expected"][INSTALLER_PATHS[0]] = "wrong"
        with self.assertRaises(ValueError):
            check_base("61b", BASES["61b"], BASES["61b"], identity)

    def test_abi_only(self):
        before = {ABI_MEMBER: OLD_ABI, "boot.art": "image", "jar": "jar", "root-abi": "root"}
        self.assertEqual(check_delta(before, before, OLD_ABI), [])
        after = dict(before, **{ABI_MEMBER: "new"})
        self.assertEqual(check_delta(before, after, "new"), [ABI_MEMBER])
        for target in ["boot.art", "jar", "root-abi", "extra"]:
            changed = dict(after, **{target: "changed"})
            with self.assertRaises(ValueError):
                check_delta(before, changed, "new")

    def test_disabled(self):
        value = dict(promotion_confirmed=False, execution_enabled=False, rollout_ready=False)
        check_disabled(value)
        for key in value:
            changed = dict(value, **{key: True})
            with self.assertRaises(ValueError):
                check_disabled(changed)

    def test_installer_plan(self):
        identity = dict(expected={target: INSTALLER for target in INSTALLER_PATHS})
        plan = dict(baseline=identity["expected"].copy(), expected=identity["expected"].copy(), changes=[], additions=[])
        check_local_plan(plan, identity)
        plan["changes"].append(dict(target=INSTALLER_PATHS[0]))
        with self.assertRaises(ValueError):
            check_local_plan(plan, identity)

    def test_published_variants(self):
        root = Path(__file__).resolve().parent
        for variant in BASES:
            data = json.loads((root / variant / "composition.json").read_text())
            check_disabled(data)
            check_base(variant, data["transaction_base_sha256"], data["transaction_base_sha256"], data["baseline"])
            plan = json.loads((root / variant / "transaction-plan.json").read_text())
            check_local_plan(plan, data["baseline"])
            self.assertFalse(data["image_rebake"])
            self.assertEqual(data["identity_role"], "planned-post-promotion-base-not-live-signoff")
            for row in data["board_local_members"]:
                self.assertEqual(row["baseline_sha256"], row["expected_sha256"])
                self.assertFalse(row["changed"])

    def test_diagnostic_and_replay_disabled(self):
        root = Path(__file__).resolve().parent
        for variant, digest in T8_BASES.items():
            data = json.loads((root / (variant + "-diagnostic") / "composition.json").read_text())
            check_base(variant, data["transaction_base_sha256"], digest, data["baseline"], "diagnostic-t8")
            self.assertEqual(data["baseline_mode"], "diagnostic-t8")
            check_disabled(data)
        environment = dict(os.environ)
        environment.pop("U14_PRODUCTION_REPLAY", None)
        run = subprocess.run(["bash", root / "replay-production.sh"], env=environment, capture_output=True, text=True)
        self.assertEqual(run.returncode, 78)
        self.assertIn("DISABLED", run.stdout)


class PreviewTests(unittest.TestCase):
    def test_signed_transfer(self):
        root = Path(__file__).resolve().parent
        data = json.loads((root / "registry-delta-signed.json").read_text())
        self.assertFalse(data["applied"])
        self.assertEqual(len(data["exceptions"]), 204)
        self.assertEqual(len(data["old_to_new"]), 45)
        self.assertTrue(all(row["approved_by"] == "outer(claude)" for row in data["exceptions"]))
        identities = {(row["package_manifest_sha256"], row["inputs_sha256"]) for row in data["exceptions"]}
        self.assertEqual(len(identities), 1)

    def test_image_approval(self):
        draft = dict(input_jars={"stubs": "87cf"}, outputs={"boot.art": "run1"}, object=dict(file_offset_start="0x3e3b8", file_offset_end_exclusive="0x3e3c0"))
        approval = dict(decision="approve", signer="outer(claude)", object="draft-sha")
        check_image_approval(approval, "draft-sha", draft["input_jars"], draft["outputs"], draft)
        with self.assertRaises(ValueError):
            check_image_approval(approval, "another-draft", draft["input_jars"], draft["outputs"], draft)
        with self.assertRaises(ValueError):
            check_image_approval(approval, "draft-sha", {"stubs": "old"}, draft["outputs"], draft)
        with self.assertRaises(ValueError):
            check_image_approval(approval, "draft-sha", draft["input_jars"], {"boot.art": "other"}, draft)

    def test_semantic_mapping(self):
        old = dict(gate="N1", issue_id="old", profile="test", detail=dict(library="owner", evidence=dict(line=29, text="NOLOAD")), disposition="REJECT")
        new = dict(old, issue_id="new", disposition="EXCEPTED")
        row = map_pending([old], [new])[0]
        self.assertTrue(row["semantic_unchanged"])
        self.assertEqual(row["old_issue_id"], "old")
        self.assertIsNone(row["approved_by"])
        changed = copy.deepcopy(new)
        changed["detail"]["library"] = "another"
        self.assertFalse(map_pending([old], [changed])[0]["semantic_unchanged"])
        changed = copy.deepcopy(new)
        changed["detail"]["evidence"]["line"] = 30
        self.assertFalse(map_pending([old], [changed])[0]["semantic_unchanged"])

    def test_published_preview(self):
        root = Path(__file__).resolve().parent
        for variant in BASES:
            preview = json.loads((root / variant / "registry-delta.json").read_text())
            review = json.loads((root / variant / "needs-outer-review.json").read_text())
            self.assertFalse(preview["applied"])
            self.assertFalse(review["applied"])
            self.assertIsNone(review["approved_by"])
            self.assertEqual(len(preview["exceptions"]), 159)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    classes = [BindingTests] if mode == "binding" else [PreviewTests] if mode == "preview" else [BindingTests, PreviewTests]
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(group) for group in classes)
    sys.exit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
