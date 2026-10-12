import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch


REVIEW = Path(__file__).resolve().parent
ROOT = REVIEW.parents[1].parent / "westlake-harness-t4/benchmark/2026-10-12-exact-realization/r3-activation-selfcheck"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    pins = {name: sha(ROOT / name) for name in ("selfcheck.py", "build_binding.py")}
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("independent_r3_checker", ROOT / "selfcheck.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cases = []
    argv = ["python3", "/fixed/executor.py", "--plan", "/fixed/plan.json", "--execute",
            "--authorization", "/fixed/auth.json", "--authorization-sha256", "1" * 64,
            "--out", "/fixed/transaction", "--action", "apply"]
    assert module.command_fields(argv)["out"] == "/fixed/transaction"
    cases.append({"case": "exact_apply_argv", "passed": True})
    for name, mutate in (("rollback_not_activation", lambda value: value.__setitem__(12, "rollback")),
                         ("wrong_authorization_flag", lambda value: value.__setitem__(5, "--out")),
                         ("duplicate_tail_flag", lambda value: value.extend(["--execute"]))):
        value = list(argv)
        mutate(value)
        try:
            module.command_fields(value)
        except ValueError:
            pass
        else:
            raise AssertionError(name)
        cases.append({"case": name, "passed": True})
    with tempfile.TemporaryDirectory(prefix="r3-early-history-local-") as temporary:
        base = Path(temporary)
        for name, status in (("interrupted", -15), ("timeout", None), ("bool_not_zero", False), ("reject", 2)):
            parent = base / "execution.json"
            parent.write_text(json.dumps({"executor_rc": status}))
            binding = {"schema": "exact-activation-selfcheck-binding/v1", "checker_sha256": pins["selfcheck.py"],
                       "synthetic": False, "execution_receipt": {"path": str(parent), "sha256": sha(parent)}}
            path = base / "binding.json"
            path.write_text(json.dumps(binding))
            with patch.object(module.r, "verify", side_effect=AssertionError("expensive proof replay reached")):
                try:
                    module.admit(path, sha(path), offline=True)
                except ValueError as error:
                    assert "executor did not succeed" in str(error)
                else:
                    raise AssertionError(name)
            cases.append({"case": "early_parent_" + name, "passed": True})
    assert all(sha(ROOT / name) == expected for name, expected in pins.items()), "editing snapshot changed"
    result = {"status": "EDITING_SNAPSHOT_PREVIEW_NOT_RELEASE", "source_sha256": pins,
              "cases_passed": len(cases), "cases": cases, "device_access": False,
              "full_487_matrix_repeated": False,
              "scope": "Exact CLI command shape and early historical executor-rc refusal only; no successful fake transaction asserted."}
    (REVIEW / "evidence/base-placement/t6-r3-preview.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
