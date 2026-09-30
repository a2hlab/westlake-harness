#!/usr/bin/env python3
"""Fake Cargo coverage; never invokes Cargo recursively or operates a device."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import spec_checks


REGISTRY = spec_checks.REPO / "knowledge/gates/spec-check-exceptions.json"


def cargo_output(statuses):
    failed = [name for name, status in statuses.items() if status == "FAILED"]
    passed = sum(status == "ok" for status in statuses.values())
    ignored = sum(status == "ignored" for status in statuses.values())
    lines = [f"running {len(statuses)} tests"]
    for name, status in statuses.items():
        lines.extend([f"test {name} ... evidence subprocess stdout", status])
    if failed:
        lines.extend(["", "failures:", "", f"---- {failed[0]} stdout ----", "panic: evidence failed",
                      "", "failures:", *[f"    {name}" for name in failed], ""])
    verdict = "FAILED" if failed else "ok"
    lines.append(f"test result: {verdict}. {passed} passed; {len(failed)} failed; "
                 f"{ignored} ignored; 0 measured; 0 filtered out; finished in 0.01s")
    stderr = "error: test failed, to rerun pass `--lib`\nerror: 1 target failed:\n    `--lib`\n" if failed else ""
    return subprocess.CompletedProcess(["cargo"], 101 if failed else 0, "\n".join(lines) + "\n", stderr)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.registry = Path(self.temporary.name) / "exceptions.json"
        self.registry.write_text(json.dumps({
            "schema_version": 1,
            "exceptions": [
                {"selector": selector, "category": "open-acceptance", "reason": "retained failure",
                 "evidence": ["evidence/results.json"], "removal_condition": "reviewed acceptance"}
                for selector in ("known_failure", "stale_candidate")
            ],
        }))
        self.exceptions = spec_checks.load_exceptions(self.registry)

    def run_gate(self, completed, registry=None):
        registry = registry or self.registry
        before = registry.read_bytes()
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(spec_checks.subprocess, "run", return_value=completed) as fake_cargo:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = spec_checks.main(["--repo", str(spec_checks.REPO), "--exceptions", str(registry)])
        self.assertEqual(registry.read_bytes(), before)
        if fake_cargo.called:
            fake_cargo.assert_called_once_with(
                ["cargo", "test", "--color", "never", "--no-fail-fast", "--",
                 "--format=pretty", "--test-threads=1"],
                cwd=spec_checks.REPO / "tools/spec-checks", capture_output=True, text=True,
            )
            self.assertTrue(stdout.getvalue().startswith(completed.stdout))
            self.assertTrue(stderr.getvalue().startswith(completed.stderr))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_approved_failures(self):
        spec_checks.load_exceptions(REGISTRY)
        statuses = dict.fromkeys(self.exceptions, "FAILED")
        statuses["passing_control"] = "ok"
        completed = cargo_output(statuses)
        completed.stdout += "\nrunning 0 tests\n\ntest result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n"
        code, stdout, stderr = self.run_gate(completed)
        self.assertEqual(code, 0)
        self.assertEqual(stdout.count("EXCEPTED "), 2)
        self.assertIn("GATE PASS: cargo_exit=101 passed=1 failed=2 excepted=2 unexpected=0", stdout)
        self.assertNotIn("STALE", stdout)
        self.assertNotIn("GATE ERROR", stderr)

    def test_new_failure(self):
        statuses = dict.fromkeys(self.exceptions, "FAILED")
        statuses["new_regression"] = "FAILED"
        code, stdout, stderr = self.run_gate(cargo_output(statuses))
        self.assertEqual(code, 1)
        self.assertIn("FAIL new_regression: not in exception registry", stdout)
        self.assertIn("GATE FAIL", stdout)
        self.assertNotIn("GATE ERROR", stderr)
        for category in ("compile", "truncated", "missing", "ignored", "filtered", "wrong-list", "late-error", "partial-suite", "signal"):
            with self.subTest(category=category):
                completed = cargo_output(dict.fromkeys(self.exceptions, "FAILED"))
                if category == "compile":
                    completed.stdout = ""
                    completed.stderr = "error: could not compile westlake-spec-checks\n"
                elif category == "truncated":
                    completed.stdout = completed.stdout.split("test result:")[0]
                elif category == "missing":
                    completed = cargo_output({"passing_control": "ok"})
                elif category == "ignored":
                    completed = cargo_output(dict.fromkeys(self.exceptions, "ignored"))
                elif category == "filtered":
                    completed.stdout = completed.stdout.replace("0 filtered out", "1 filtered out")
                elif category == "wrong-list":
                    completed.stdout = completed.stdout.replace("    known_failure\n", "    different_failure\n")
                elif category == "late-error":
                    completed.stderr += "error: doctest failed: unable to run test binary\n"
                elif category == "partial-suite":
                    completed.stdout += "\nrunning 3 tests\n"
                elif category == "signal":
                    completed.returncode = -9
                code, stdout, stderr = self.run_gate(completed)
                self.assertEqual(code, 1)
                self.assertNotIn("GATE PASS", stdout)
                self.assertNotIn("STALE", stdout)
        with tempfile.TemporaryDirectory() as temporary:
            registry = Path(temporary) / "exceptions.json"
            payload = json.loads(self.registry.read_text())
            payload["exceptions"].append(payload["exceptions"][0])
            registry.write_text(json.dumps(payload))
            code, stdout, stderr = self.run_gate(cargo_output(statuses), registry)
            self.assertEqual(code, 1)
            self.assertIn("duplicate exception", stderr)
            self.assertNotIn("GATE PASS", stdout)
        with patch.object(spec_checks.subprocess, "run", side_effect=FileNotFoundError("cargo unavailable")):
            with redirect_stderr(io.StringIO()) as stderr:
                self.assertEqual(spec_checks.main(["--exceptions", str(REGISTRY)]), 1)
            self.assertIn("cargo unavailable", stderr.getvalue())

    def test_stale_exception(self):
        statuses = dict.fromkeys(self.exceptions, "FAILED")
        selector = "stale_candidate"
        statuses[selector] = "ok"
        code, stdout, stderr = self.run_gate(cargo_output(statuses))
        self.assertEqual(code, 0)
        self.assertIn(f"STALE {selector}: passed; review and remove the exception", stdout)
        self.assertEqual(stdout.count("EXCEPTED "), 1)
        self.assertNotIn("GATE ERROR", stderr)
        code, stdout, stderr = self.run_gate(cargo_output(dict.fromkeys(self.exceptions, "ok")))
        self.assertEqual(code, 0)
        self.assertEqual(stdout.count("STALE "), 2)
        self.assertIn("GATE PASS: cargo_exit=0", stdout)
        empty = Path(self.temporary.name) / "empty.json"
        empty.write_text(json.dumps({"schema_version": 1, "exceptions": []}))
        code, stdout, stderr = self.run_gate(cargo_output({"passing_control": "ok"}), empty)
        self.assertEqual(code, 0)
        self.assertNotIn("STALE", stdout)


if __name__ == "__main__":
    unittest.main()
