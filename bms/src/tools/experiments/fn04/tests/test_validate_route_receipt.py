#!/usr/bin/env python3

import copy
import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "validate_route_receipt.py"
SPEC = importlib.util.spec_from_file_location("validate_route_receipt", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
ReceiptError = MODULE.ReceiptError
validate_receipt = MODULE.validate_receipt


def base_receipt():
    return {
        "schema_version": "1.0",
        "concept_id": "Fn04",
        "route": "R1b",
        "verdict": "PASS",
        "generation_id": "d200-boot42-build7",
        "build_manifest_sha256": "a" * 64,
        "window": {
            "android_token": "binder:42",
            "oh_parent_id": 28,
            "oh_child_id": 34,
            "generation_id": "d200-boot42-build7",
        },
        "surface": {
            "unique_id": 9001,
            "generation_id": "d200-boot42-build7",
        },
        "lifecycle_events": [
            {
                "seq": index,
                "event": event,
                "generation_id": "d200-boot42-build7",
            }
            for index, event in enumerate(
                (
                    "ADD_ACCEPTED",
                    "RELAYOUT_READY",
                    "SURFACE_READY",
                    "REMOVE_REQUESTED",
                    "CHILD_DESTROYED",
                ),
                start=1,
            )
        ],
        "frames": [
            {
                "frame_id": 1,
                "generation_id": "d200-boot42-build7",
                "buffer_queued": True,
                "transaction_committed": True,
                "present_outcome": "PRESENTED",
                "content_origin": "APP_CONTENT",
            }
        ],
        "positive_cases": [{"id": "P01", "result": "PASS"}],
        "negative_cases": [{"id": "N01", "result": "PASS"}],
        "failure_cases": [{"id": "F01", "result": "PASS"}],
        "blocked_by": [],
    }


class ReceiptValidatorTest(unittest.TestCase):
    def test_positive_same_generation_app_content(self):
        validate_receipt(base_receipt())

    def test_rejects_parent_child_identity_collapse(self):
        receipt = base_receipt()
        receipt["window"]["oh_child_id"] = receipt["window"]["oh_parent_id"]
        with self.assertRaisesRegex(ReceiptError, "must differ"):
            validate_receipt(receipt)

    def test_rejects_cross_generation_surface(self):
        receipt = base_receipt()
        receipt["surface"]["generation_id"] = "stale-generation"
        with self.assertRaisesRegex(ReceiptError, "surface generation"):
            validate_receipt(receipt)

    def test_rejects_duplicate_frame_id(self):
        receipt = base_receipt()
        receipt["frames"].append(copy.deepcopy(receipt["frames"][0]))
        with self.assertRaisesRegex(ReceiptError, "duplicate frame_id"):
            validate_receipt(receipt)

    def test_rejects_relayout_before_add(self):
        receipt = base_receipt()
        receipt["lifecycle_events"][0]["event"] = "RELAYOUT_READY"
        with self.assertRaisesRegex(ReceiptError, "must follow"):
            validate_receipt(receipt)

    def test_rejects_cross_generation_teardown(self):
        receipt = base_receipt()
        receipt["lifecycle_events"][-1]["generation_id"] = "stale-generation"
        with self.assertRaisesRegex(ReceiptError, "generation mismatch"):
            validate_receipt(receipt)

    def test_rejects_duplicate_teardown_sequence(self):
        receipt = base_receipt()
        receipt["lifecycle_events"][-1]["seq"] = receipt["lifecycle_events"][-2]["seq"]
        with self.assertRaisesRegex(ReceiptError, "strictly increasing"):
            validate_receipt(receipt)

    def test_rejects_present_without_queue_and_commit(self):
        receipt = base_receipt()
        receipt["frames"][0]["buffer_queued"] = False
        with self.assertRaisesRegex(ReceiptError, "PRESENTED requires"):
            validate_receipt(receipt)

    def test_rejects_placeholder_only_pass(self):
        receipt = base_receipt()
        receipt["frames"][0]["content_origin"] = "PLACEHOLDER"
        with self.assertRaisesRegex(ReceiptError, "APP_CONTENT PRESENTED"):
            validate_receipt(receipt)

    def test_block_requires_explicit_external_gate(self):
        receipt = base_receipt()
        receipt["verdict"] = "BLOCK"
        receipt["lifecycle_events"] = []
        receipt["frames"] = []
        receipt["positive_cases"] = []
        receipt["negative_cases"] = []
        receipt["failure_cases"] = []
        with self.assertRaisesRegex(ReceiptError, "BLOCK requires"):
            validate_receipt(receipt)
        receipt["blocked_by"] = ["EXTERNAL:DEVICE_EXCLUSIVE_WINDOW_UNAVAILABLE"]
        validate_receipt(receipt)

    def test_fail_may_preserve_nonpresented_frame(self):
        receipt = base_receipt()
        receipt["verdict"] = "FAIL"
        receipt["lifecycle_events"] = receipt["lifecycle_events"][:3]
        receipt["frames"][0].update(
            {
                "buffer_queued": True,
                "transaction_committed": False,
                "present_outcome": "FAILED",
                "content_origin": "UNKNOWN",
            }
        )
        receipt["positive_cases"][0]["result"] = "FAIL"
        validate_receipt(receipt)


if __name__ == "__main__":
    unittest.main()
