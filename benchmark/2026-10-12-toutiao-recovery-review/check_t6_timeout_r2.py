import ast
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch


REVIEW = Path(__file__).resolve().parent
ROOT = REVIEW.parents[1].parent / "westlake-harness-t4/benchmark/2026-10-12-exact-realization"
REVISION = ROOT / "r2-timeout"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    pins = json.loads((REVISION / "source-exact.json").read_text())
    for row in pins["sources"]:
        assert sha(REVISION / row["path"]) == row["sha256"]
        assert sha(REVISION / row["derived_path"]) == row["derived_sha256"]
    parent = ast.parse((ROOT / "restore.py").read_text())
    revised = ast.parse((REVISION / "restore.py").read_text())
    normalize = lambda tree: {node.name: ast.dump(node, include_attributes=False)
                              for node in tree.body if isinstance(node, ast.FunctionDef)}
    old, new = normalize(parent), normalize(revised)
    assert set(old) == set(new)
    assert [key for key in old if old[key] != new[key]] == ["execute"]
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("review_timeout_r2", REVISION / "restore.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    results = []
    with tempfile.TemporaryDirectory(prefix="timeout-r2-offline-") as temporary:
        base = Path(temporary)
        lock = base / "lock-tool.sh"
        lock.write_text("fixture only; never invoked\n")
        lock_ref = {"path": str(lock), "sha256": sha(lock)}
        proof = {"proof_sha256": "1" * 64, "source_identity": {"kind": "candidate-fingerprint"}, "source_seal": None}
        plan = {"serial": "5cd1e3dd00000000000000000923012c"}
        auth = {"holder": "outer-fixture"}
        ad = {"lock_tool": lock_ref}
        receipt = {"plan_sha256": "2" * 64}
        guarded = (plan, ad, auth, base / "authorization.json", receipt)
        for label, executor_rc, action in (("success", 0, "apply"), ("executor_reject", 2, "apply"),
                                            ("executor_interrupted", -15, "apply"), ("rollback_budget", 0, "rollback"),
                                            ("timeout_unknown", None, "apply")):
            calls = []
            def runner(argv, **kwargs):
                calls.append({"argv": argv, "kwargs": kwargs})
                if len(calls) == 1:
                    return subprocess.CompletedProcess(argv, 0, "outer-fixture\n", "")
                if executor_rc is None:
                    raise subprocess.TimeoutExpired(argv, 2700, output=b"partial-out", stderr=b"partial-error")
                return subprocess.CompletedProcess(argv, executor_rc, "executor-out", "executor-error")
            with patch.object(module, "guard", return_value=guarded), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                result, returned = module.execute(proof, base, {}, {"sha256": "3" * 64}, lock_ref, base, base / "transaction", runner=runner, action=action)
            assert calls[0]["kwargs"]["timeout"] == 15
            assert calls[1]["kwargs"]["timeout"] == 2700
            assert calls[1]["argv"][-1] == action
            assert returned == (124 if executor_rc is None else executor_rc)
            assert result["seal_signed"] is False and result["ui_accepted"] is False
            if executor_rc is None:
                assert result["executor_rc"] is None
                assert result["status"] == result["process_state"] == result["rollback_state"] == "UNKNOWN"
                assert result["partial_stdout"] == "partial-out" and result["partial_stderr"] == "partial-error"
            results.append({"case": label, "passed": True, "returned_rc": returned, "runner_calls": calls})
        for label, fail_guard in (("admission_failure_zero_runner", True), ("wrong_holder_no_executor", False)):
            calls = []
            def runner(argv, **kwargs):
                calls.append(argv)
                return subprocess.CompletedProcess(argv, 0, "wrong-holder\n", "")
            with patch.object(module, "guard", side_effect=ValueError("fixture admission rejection") if fail_guard else None,
                              return_value=guarded):
                try:
                    module.execute(proof, base, {}, {}, lock_ref, base, base / "transaction", runner=runner)
                except ValueError:
                    pass
                else:
                    raise AssertionError("failed guard accepted")
            assert len(calls) == (0 if fail_guard else 1)
            results.append({"case": label, "passed": True, "runner_calls": len(calls)})
    report = {"verdict": "EXACT_SOURCE_DELTA_ACCEPT_PENDING_RELEASE_LISTING", "source_pins": pins,
              "only_changed_function": "execute", "lock_timeout_unchanged": 15, "executor_transport_timeout": 2700,
              "cases_passed": len(results), "cases": results, "device_access": False,
              "scope": "Mock runner exercises only adapter transport; admission validation is unchanged AST, not bypassed for real execution."}
    (REVIEW / "evidence/base-placement/t6-timeout-r2-review.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
