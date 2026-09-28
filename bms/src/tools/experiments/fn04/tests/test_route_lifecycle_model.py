#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "route_lifecycle_model.py"
SPEC = importlib.util.spec_from_file_location("route_lifecycle_model", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
RouteError = MODULE.RouteError
RouteLifecycle = MODULE.RouteLifecycle
State = MODULE.State
WindowIdentity = MODULE.WindowIdentity


GEN = "build7-boot42-window3"


def model():
    return RouteLifecycle(WindowIdentity(GEN, "binder:42", 28, 34))


def ready_model():
    lifecycle = model()
    lifecycle.add(GEN, "binder:42")
    lifecycle.relayout(GEN, 1280, 720)
    lifecycle.attach_surface(GEN, 9001)
    return lifecycle


class RouteLifecycleModelTest(unittest.TestCase):
    def test_positive_add_relayout_frame_remove(self):
        lifecycle = ready_model()
        lifecycle.dequeue(GEN, 1)
        lifecycle.queue(GEN, 1)
        lifecycle.commit(GEN, 1)
        lifecycle.remove(GEN)
        lifecycle.destroy(GEN)
        self.assertEqual(State.DESTROYED, lifecycle.state)
        self.assertTrue(lifecycle.frames[1].released)

    def test_a03_rejects_wrong_token(self):
        with self.assertRaisesRegex(RouteError, "WRONG_TOKEN"):
            model().add(GEN, "binder:wrong")

    def test_a03_rejects_parent_child_collapse(self):
        lifecycle = RouteLifecycle(WindowIdentity(GEN, "binder:42", 28, 28))
        with self.assertRaisesRegex(RouteError, "PARENT_CHILD_COLLAPSE"):
            lifecycle.add(GEN, "binder:42")

    def test_a03_propagates_oh_create_failure(self):
        lifecycle = model()
        with self.assertRaisesRegex(RouteError, "OH_CHILD_CREATE_FAILED"):
            lifecycle.add(GEN, "binder:42", oh_create_ok=False)
        self.assertEqual(State.FAILED, lifecycle.state)

    def test_a04_rejects_relayout_before_add(self):
        with self.assertRaisesRegex(RouteError, "INVALID_STATE"):
            model().relayout(GEN, 1280, 720)

    def test_a04_rejects_invalid_geometry(self):
        lifecycle = model()
        lifecycle.add(GEN, "binder:42")
        with self.assertRaisesRegex(RouteError, "INVALID_LAYOUT"):
            lifecycle.relayout(GEN, 0, 720)

    def test_a04_preserves_previous_geometry_on_oh_failure(self):
        lifecycle = model()
        lifecycle.add(GEN, "binder:42")
        lifecycle.relayout(GEN, 1280, 720)
        with self.assertRaisesRegex(RouteError, "OH_RELAYOUT_FAILED"):
            lifecycle.relayout(GEN, 1920, 1080, oh_apply_ok=False)
        self.assertEqual((1280, 720), (lifecycle.width, lifecycle.height))

    def test_rejects_cross_generation_surface(self):
        lifecycle = model()
        lifecycle.add(GEN, "binder:42")
        lifecycle.relayout(GEN, 1280, 720)
        with self.assertRaisesRegex(RouteError, "STALE_GENERATION"):
            lifecycle.attach_surface("old-generation", 9001)

    def test_a10_rejects_frame_replay(self):
        lifecycle = ready_model()
        lifecycle.dequeue(GEN, 1)
        with self.assertRaisesRegex(RouteError, "FRAME_ID_REPLAY"):
            lifecycle.dequeue(GEN, 1)

    def test_a10_rejects_failed_fence_without_consuming_ownership(self):
        lifecycle = ready_model()
        frame = lifecycle.dequeue(GEN, 1)
        with self.assertRaisesRegex(RouteError, "ACQUIRE_FENCE_FAILED"):
            lifecycle.queue(GEN, 1, fence_ok=False)
        self.assertTrue(frame.acquire_fence_owned)
        self.assertFalse(frame.queued)

    def test_a14_rejects_commit_before_queue(self):
        lifecycle = ready_model()
        lifecycle.dequeue(GEN, 1)
        with self.assertRaisesRegex(RouteError, "COMMIT_BEFORE_QUEUE"):
            lifecycle.commit(GEN, 1)

    def test_a14_propagates_rs_failure_without_false_commit(self):
        lifecycle = ready_model()
        lifecycle.dequeue(GEN, 1)
        lifecycle.queue(GEN, 1)
        with self.assertRaisesRegex(RouteError, "RS_COMMIT_FAILED"):
            lifecycle.commit(GEN, 1, rs_ok=False)
        self.assertFalse(lifecycle.frames[1].committed)

    def test_a08_rejects_remove_before_add(self):
        with self.assertRaisesRegex(RouteError, "INVALID_STATE"):
            model().remove(GEN)

    def test_a08_preserves_live_state_on_oh_remove_failure(self):
        lifecycle = ready_model()
        with self.assertRaisesRegex(RouteError, "OH_REMOVE_FAILED"):
            lifecycle.remove(GEN, oh_remove_ok=False)
        self.assertEqual(State.SURFACE_READY, lifecycle.state)

    def test_a08_rejects_stale_and_duplicate_teardown(self):
        lifecycle = ready_model()
        with self.assertRaisesRegex(RouteError, "STALE_GENERATION"):
            lifecycle.remove("old-generation")
        lifecycle.remove(GEN)
        lifecycle.destroy(GEN)
        with self.assertRaisesRegex(RouteError, "INVALID_STATE"):
            lifecycle.destroy(GEN)


if __name__ == "__main__":
    unittest.main()
