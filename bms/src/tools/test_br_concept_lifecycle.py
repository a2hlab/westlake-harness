#!/usr/bin/env python3
"""Host regression tests for the Bridge Concept lifecycle compatibility CLI."""

from __future__ import annotations

import json
import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "src/tools/br-concept-lifecycle"


class ConceptLifecycleCliTest(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(CLI), *args],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
        )

    def assert_passes(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def load_current_checkpoint(self) -> dict:
        """Return an ephemeral checkpoint rebound to the current test tree.

        The repository checkpoint is a production fail-closed receipt.  Concept or
        Action edits must therefore make that file stale until a real reacceptance.
        Unit tests which exercise local drift need an independent current baseline
        so an unrelated production drift does not invalidate every test branch.
        """
        data = json.loads(
            (ROOT / "docs/workflows/FN01_RESUME_CHECKPOINT.json").read_text(
                encoding="utf-8"
            )
        )

        def current_sha(path_value: object) -> str | None:
            if not isinstance(path_value, str):
                return None
            candidate = ROOT / path_value
            if not candidate.is_file():
                return None
            return hashlib.sha256(candidate.read_bytes()).hexdigest()

        def rebind(node: object) -> None:
            if isinstance(node, dict):
                digest = current_sha(node.get("path"))
                if digest is not None and "sha256" in node:
                    node["sha256"] = digest
                for path_key in (
                    "evidence",
                    "implementation",
                    "manifest",
                    "results",
                    "supersession_receipt",
                ):
                    digest = current_sha(node.get(path_key))
                    digest_key = f"{path_key}_sha256"
                    if digest is not None and digest_key in node:
                        node[digest_key] = digest
                for value in node.values():
                    rebind(value)
            elif isinstance(node, list):
                for value in node:
                    rebind(value)

        rebind(data)
        return data

    def write_checkpoint(self, mutate) -> Path:
        data = self.load_current_checkpoint()
        mutate(data)
        directory = Path(tempfile.mkdtemp(prefix="fn01-resume-test-"))
        checkpoint = directory / "checkpoint.json"
        checkpoint.write_text(json.dumps(data), encoding="utf-8")
        self.addCleanup(lambda: directory.rmdir() if directory.exists() else None)
        self.addCleanup(lambda: checkpoint.unlink(missing_ok=True))
        return checkpoint

    def write_pre_device_manifest(self, mutate=lambda data: None) -> Path:
        evidence_path = "src/tools/test_br_concept_lifecycle.py"
        evidence_sha = hashlib.sha256((ROOT / evidence_path).read_bytes()).hexdigest()

        def artifact() -> dict:
            return {"path": evidence_path, "sha256": evidence_sha}

        data = {
            "schema_version": 1,
            "action_id": "Fn07.A01",
            "device_verdict": "NOT_RUN",
            "gates": {
                "spec": {"status": "PASS", "evidence": [artifact()]},
                "wiring": {"status": "PASS", "evidence": [artifact()]},
                "build": {"status": "PASS", "evidence": [artifact()]},
                "host_pnf": {
                    "status": "PASS",
                    "cases": {
                        "positive": "PASS",
                        "negative": "PASS",
                        "failure": "PASS",
                    },
                    "evidence": [artifact()],
                },
                "artifact_provenance": {
                    "status": "PASS",
                    "evidence": [artifact()],
                    "bindings": {
                        "source_inputs": [artifact()],
                        "build_receipts": [artifact()],
                        "deployable_artifacts": [artifact()],
                    },
                },
            },
            "blockers": [],
        }
        mutate(data)
        directory = Path(tempfile.mkdtemp(prefix="pre-device-test-"))
        manifest = directory / "manifest.json"
        manifest.write_text(json.dumps(data), encoding="utf-8")
        self.addCleanup(lambda: directory.rmdir() if directory.exists() else None)
        self.addCleanup(lambda: manifest.unlink(missing_ok=True))
        return manifest

    def test_pre_device_ready_is_not_a_device_verdict(self) -> None:
        result = self.run_cli(
            "pre-device", "--manifest", str(self.write_pre_device_manifest())
        )
        self.assert_passes(result)
        self.assertIn("readiness: READY_FOR_DEVICE_ALLOCATION", result.stdout)
        self.assertIn("device_verdict: NOT_RUN", result.stdout)
        self.assertIn("formal_effect: NONE", result.stdout)

    def test_pre_device_fails_closed_with_mechanical_blocker_taxonomy(self) -> None:
        def mutate(data: dict) -> None:
            data["gates"]["host_pnf"]["cases"]["failure"] = "FAIL"
            data["gates"]["artifact_provenance"]["bindings"][
                "deployable_artifacts"
            ] = []

        result = self.run_cli(
            "pre-device", "--manifest", str(self.write_pre_device_manifest(mutate))
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("readiness: BLOCKED", result.stdout)
        self.assertIn("BLOCKER HOST_PNF_INCOMPLETE", result.stdout)
        self.assertIn("BLOCKER ARTIFACT_PROVENANCE_INCOMPLETE", result.stdout)
        self.assertIn("device_verdict: NOT_RUN", result.stdout)

    def test_pre_device_rejects_stale_bound_evidence(self) -> None:
        def mutate(data: dict) -> None:
            data["gates"]["wiring"]["evidence"][0]["sha256"] = "0" * 64

        result = self.run_cli(
            "pre-device", "--manifest", str(self.write_pre_device_manifest(mutate))
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("BLOCKER WIRING_INCOMPLETE", result.stdout)

    def test_default_check_remains_multi_apk_compatible(self) -> None:
        result = self.run_cli("check")
        self.assert_passes(result)
        self.assertIn("FN01_MULTI_APK_LIFECYCLE.json", result.stdout)

    def test_route_status_selects_independent_state(self) -> None:
        for route, state_name in (
            ("r2", "FN01_OWN_R2_LIFECYCLE.json"),
            ("r3", "FN01_OWN_R3_LIFECYCLE.json"),
        ):
            with self.subTest(route=route):
                result = self.run_cli("status", "--route", route)
                self.assert_passes(result)
                self.assertIn(state_name, result.stdout)
                self.assertRegex(result.stdout, r"current_step: [1-9]|current_step: 10")

    def test_parallel_check_validates_routes_and_fails_closed_on_concept_drift(
        self,
    ) -> None:
        result = self.run_cli("parallel-check")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FN01_OWN_R2_LIFECYCLE.json", result.stdout)
        self.assertIn("FN01_OWN_R3_LIFECYCLE.json", result.stdout)
        self.assertIn("FN01_OWN_R2_LIFECYCLE.json", result.stdout)
        self.assertIn("FN01_OWN_R3_LIFECYCLE.json", result.stdout)
        self.assertEqual(result.stdout.count("PASS mandatory lifecycle:"), 2)
        self.assertIn(
            "FAIL parallel decision gate: Concept graph changed",
            result.stdout + result.stderr,
        )

    def test_route_lifecycle_uses_concept_route_ids(self) -> None:
        for state_name, expected in (
            ("FN01_OWN_R2_LIFECYCLE.json", "R2"),
            ("FN01_OWN_R3_LIFECYCLE.json", "R3"),
        ):
            with self.subTest(state=state_name):
                data = json.loads(
                    (ROOT / "docs" / "workflows" / state_name).read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(data["technology_route"], expected)

    def test_parallel_commands_reject_route_override(self) -> None:
        result = self.run_cli("parallel-check", "--route", "r2")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "parallel commands do not accept --state or --route", result.stderr
        )

    def test_default_resume_reuses_history_without_restart(self) -> None:
        checkpoint = self.write_checkpoint(lambda data: None)
        result = self.run_cli("resume", "--checkpoint", str(checkpoint))
        self.assert_passes(result)
        self.assertIn("default_entry: resume", result.stdout)
        self.assertIn("HISTORICAL_PASS_EVIDENCE_RECOVERY Fn01.A01", result.stdout)
        self.assertIn("WAITING_EVIDENCE Fn01.A04", result.stdout)
        self.assertIn("WAITING_EVIDENCE Fn01.A05", result.stdout)
        self.assertIn("WAITING_EVIDENCE Fn01.A06", result.stdout)
        self.assertIn("PASS_REUSABLE Fn01.A07", result.stdout)
        self.assertIn(
            "resume_result: checkpoint valid; 2 historical evidence-recovery action(s); no hash invalidation",
            result.stdout,
        )

    def test_default_resume_check_is_strict_and_clean(self) -> None:
        checkpoint = self.write_checkpoint(lambda data: None)
        self.assert_passes(
            self.run_cli("resume-check", "--checkpoint", str(checkpoint))
        )

    def test_action_local_drift_invalidates_only_that_dependency_branch(self) -> None:
        def mutate(data: dict) -> None:
            action = data["actions"][5]
            self.assertEqual(action["action_id"], "Fn01.A06")
            action["frozen_inputs"][1]["sha256"] = "0" * 64

        checkpoint = self.write_checkpoint(mutate)
        report = self.run_cli("resume", "--checkpoint", str(checkpoint))
        self.assert_passes(report)
        self.assertIn("INVALIDATED Fn01.A06", report.stdout)
        self.assertIn("PASS_REUSABLE Fn01.A07", report.stdout)
        self.assertNotIn("INVALIDATED Fn01.A07", report.stdout)

        strict = self.run_cli("resume-check", "--checkpoint", str(checkpoint))
        self.assertEqual(strict.returncode, 1, strict.stdout + strict.stderr)

    def test_concept_drift_invalidates_every_action(self) -> None:
        def mutate(data: dict) -> None:
            data["concept_baseline"][0]["sha256"] = "0" * 64

        checkpoint = self.write_checkpoint(mutate)
        result = self.run_cli("resume-check", "--checkpoint", str(checkpoint))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("INVALIDATED Fn01.A01", result.stdout)
        self.assertIn("INVALIDATED Fn01.A19", result.stdout)

    def test_reusable_verdict_drift_propagates_to_explicit_consumers(self) -> None:
        def mutate(data: dict) -> None:
            action = data["actions"][6]
            self.assertEqual(action["action_id"], "Fn01.A07")
            action["reuse"]["evidence_sha256"] = "0" * 64

        checkpoint = self.write_checkpoint(mutate)
        result = self.run_cli("resume-check", "--checkpoint", str(checkpoint))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        for action_id in (
            "Fn01.A07",
            "Fn01.A08",
            "Fn01.A09",
            "Fn01.A10",
            "Fn01.A18",
            "Fn01.A19",
        ):
            self.assertIn(f"INVALIDATED {action_id}", result.stdout)
        self.assertNotIn("INVALIDATED Fn01.A06", result.stdout)

    def test_reusable_runtime_helper_drift_propagates_to_consumers(self) -> None:
        def mutate(data: dict) -> None:
            action = data["actions"][6]
            self.assertEqual(action["action_id"], "Fn01.A07")
            helper = action["reuse"]["exact_bindings"][-1]
            self.assertTrue(helper["path"].endswith("sha256.c"))
            helper["sha256"] = "0" * 64

        checkpoint = self.write_checkpoint(mutate)
        result = self.run_cli("resume-check", "--checkpoint", str(checkpoint))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        for action_id in (
            "Fn01.A07",
            "Fn01.A08",
            "Fn01.A09",
            "Fn01.A10",
            "Fn01.A18",
            "Fn01.A19",
        ):
            self.assertIn(f"INVALIDATED {action_id}", result.stdout)
        self.assertNotIn("INVALIDATED Fn01.A06", result.stdout)

    def test_dependency_copy_must_match_atom_truth(self) -> None:
        def mutate(data: dict) -> None:
            action = data["actions"][18]
            self.assertEqual(action["action_id"], "Fn01.A19")
            action["depends_on"].remove("Fn01.A18")

        checkpoint = self.write_checkpoint(mutate)
        result = self.run_cli("resume-check", "--checkpoint", str(checkpoint))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("do not match atom.yaml", result.stderr)

    def test_evidence_hash_cannot_hide_wrong_action_or_verdict(self) -> None:
        def mutate(data: dict) -> None:
            a06 = data["actions"][5]
            a07 = data["actions"][6]
            a07["reuse"]["evidence"] = a06["last_verdict"]["evidence"]
            a07["reuse"]["evidence_sha256"] = a06["last_verdict"][
                "evidence_sha256"
            ]

        checkpoint = self.write_checkpoint(mutate)
        result = self.run_cli("resume-check", "--checkpoint", str(checkpoint))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("evidence action identity mismatch", result.stderr)

    def test_awaiting_verification_handoff_drift_invalidates_action(self) -> None:
        def mutate(data: dict) -> None:
            action = data["actions"][5]
            self.assertEqual(action["action_id"], "Fn01.A06")
            action["state"] = "awaiting_verification"
            action["implementation_handoff"]["implementation_sha256"] = "0" * 64

        checkpoint = self.write_checkpoint(mutate)
        result = self.run_cli("resume-check", "--checkpoint", str(checkpoint))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("INVALIDATED Fn01.A06", result.stdout)
        self.assertNotIn("INVALIDATED Fn01.A07", result.stdout)

    def test_block_verdict_evidence_drift_invalidates_waiting_action(self) -> None:
        def mutate(data: dict) -> None:
            action = data["actions"][5]
            self.assertEqual(action["action_id"], "Fn01.A06")
            self.assertEqual(action["state"], "waiting_evidence")
            action["last_verdict"]["evidence_sha256"] = "0" * 64

        checkpoint = self.write_checkpoint(mutate)
        result = self.run_cli("resume-check", "--checkpoint", str(checkpoint))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("INVALIDATED Fn01.A06", result.stdout)
        self.assertNotIn("INVALIDATED Fn01.A07", result.stdout)

    def test_bound_artifact_cannot_escape_repository(self) -> None:
        def mutate(data: dict) -> None:
            data["concept_baseline"][0]["path"] = "/etc/passwd"

        checkpoint = self.write_checkpoint(mutate)
        result = self.run_cli("resume-check", "--checkpoint", str(checkpoint))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn(
            "artifact path must be repository-relative", result.stderr
        )

    def test_resume_commands_reject_lifecycle_route_or_state_override(self) -> None:
        route = self.run_cli("resume", "--route", "r2")
        self.assertNotEqual(route.returncode, 0)
        self.assertIn(
            "resume commands do not accept --state or --route", route.stderr
        )
        state = self.run_cli(
            "resume",
            "--state",
            str(ROOT / "docs/workflows/FN01_MULTI_APK_LIFECYCLE.json"),
        )
        self.assertNotEqual(state.returncode, 0)
        self.assertIn(
            "resume commands do not accept --state or --route", state.stderr
        )

    def test_resume_next_persists_same_run_across_interruption(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fn01-run-state-test-") as directory:
            run_state = Path(directory) / "run-state.json"
            checkpoint = self.write_checkpoint(lambda data: None)
            created = self.run_cli(
                "resume-next",
                "--checkpoint",
                str(checkpoint),
                "--action",
                "Fn01.A02",
                "--run-state",
                str(run_state),
            )
            self.assert_passes(created)
            self.assertIn("CREATED_RUN:", created.stdout)
            state = json.loads(run_state.read_text(encoding="utf-8"))
            run_id = state["runs"][0]["run_id"]

            started = self.run_cli(
                "run-next",
                "--checkpoint",
                str(checkpoint),
                "--run-id",
                run_id,
                "--run-state",
                str(run_state),
            )
            self.assert_passes(started)
            self.assertIn("STARTED_RUN:", started.stdout)

            resumed = self.run_cli(
                "resume-next",
                "--checkpoint",
                str(checkpoint),
                "--run-state",
                str(run_state),
            )
            self.assert_passes(resumed)
            self.assertIn("RESUMED_RUN:", resumed.stdout)
            self.assertIn(run_id, resumed.stdout)
            self.assertIn("action_id: Fn01.A02", resumed.stdout)
            self.assertNotIn("Fn01.A01", resumed.stdout)
            final_state = json.loads(run_state.read_text(encoding="utf-8"))
            self.assertEqual(len(final_state["runs"]), 1)
            self.assertEqual(final_state["runs"][0]["attempt_count"], 1)

    def test_close_next_binds_outputs_without_granting_maturity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fn01-close-state-test-") as directory:
            temporary = Path(directory)
            run_state = temporary / "run-state.json"
            checkpoint = self.write_checkpoint(lambda data: None)
            self.assert_passes(
                self.run_cli(
                    "resume-next",
                    "--checkpoint",
                    str(checkpoint),
                    "--action",
                    "Fn01.A02",
                    "--run-state",
                    str(run_state),
                )
            )
            state = json.loads(run_state.read_text(encoding="utf-8"))
            run = state["runs"][0]
            self.assert_passes(
                self.run_cli(
                    "run-next",
                    "--checkpoint",
                    str(checkpoint),
                    "--run-id",
                    run["run_id"],
                    "--run-state",
                    str(run_state),
                )
            )
            output_path = (
                ROOT
                / "var/evidence/atoms/Fn01/A02/runs/"
                "20260728T-fn01-a02-evidence-recovery/AUDIT.md"
            )
            output_sha = hashlib.sha256(output_path.read_bytes()).hexdigest()
            result = {
                "schema_version": 1,
                "run_id": run["run_id"],
                "work_digest": run["work_digest"],
                "action_id": "Fn01.A02",
                "outcome": "completed",
                "outputs": [
                    {
                        "path": str(output_path.relative_to(ROOT)),
                        "sha256": output_sha,
                    }
                ],
            }
            result_path = temporary / "result.json"
            result_path.write_text(json.dumps(result), encoding="utf-8")
            closed = self.run_cli(
                "close-next",
                "--checkpoint",
                str(checkpoint),
                "--run-id",
                run["run_id"],
                "--result",
                str(result_path),
                "--run-state",
                str(run_state),
            )
            self.assert_passes(closed)
            self.assertIn("CLOSED_RUN:", closed.stdout)
            self.assertIn("formal_effect: NONE", closed.stdout)
            final_state = json.loads(run_state.read_text(encoding="utf-8"))
            self.assertEqual(final_state["runs"][0]["status"], "completed")

            repeated = self.run_cli(
                "resume-next",
                "--checkpoint",
                str(checkpoint),
                "--action",
                "Fn01.A02",
                "--run-state",
                str(run_state),
            )
            self.assert_passes(repeated)
            self.assertIn("ALREADY_COMPLETED:", repeated.stdout)
            self.assertEqual(
                json.loads(run_state.read_text(encoding="utf-8"))["runs"][0][
                    "run_id"
                ],
                run["run_id"],
            )

    def test_resume_next_supersedes_open_run_after_valid_state_advance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fn01-state-advance-test-") as directory:
            temporary = Path(directory)
            run_state = temporary / "run-state.json"
            checkpoint_data = self.load_current_checkpoint()
            a02 = checkpoint_data["actions"][1]
            original_state = a02["state"]
            a02["state"] = "historical_pass_evidence_recovery"
            a02["reuse"][
                "binding_status"
            ] = "historical_hash_bound_current_source_lineage_requires_evidence_recovery"
            old_checkpoint = temporary / "old-checkpoint.json"
            old_checkpoint.write_text(json.dumps(checkpoint_data), encoding="utf-8")
            self.assert_passes(
                self.run_cli(
                    "resume-next",
                    "--checkpoint",
                    str(old_checkpoint),
                    "--action",
                    "Fn01.A02",
                    "--run-state",
                    str(run_state),
                )
            )
            old_run = json.loads(run_state.read_text(encoding="utf-8"))["runs"][0]

            a02["state"] = original_state
            a02["reuse"][
                "binding_status"
            ] = "current_source_hash_bound_host_contract_production_receipt_pending"
            new_checkpoint = temporary / "new-checkpoint.json"
            new_checkpoint.write_text(json.dumps(checkpoint_data), encoding="utf-8")
            advanced = self.run_cli(
                "resume-next",
                "--checkpoint",
                str(new_checkpoint),
                "--action",
                "Fn01.A02",
                "--run-state",
                str(run_state),
            )
            self.assert_passes(advanced)
            self.assertIn("CREATED_RUN:", advanced.stdout)
            state = json.loads(run_state.read_text(encoding="utf-8"))
            self.assertEqual(len(state["runs"]), 2)
            self.assertEqual(state["runs"][0]["run_id"], old_run["run_id"])
            self.assertEqual(state["runs"][0]["status"], "superseded")
            self.assertEqual(state["runs"][1]["status"], "pending")
            self.assertNotEqual(
                state["runs"][0]["work_digest"], state["runs"][1]["work_digest"]
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
