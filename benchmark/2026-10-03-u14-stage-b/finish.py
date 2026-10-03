import difflib
import json
from pathlib import Path

from prepare import HERE, REPO, sha, write

LAYOUT = "| **`benchmark/2026-10-03-u14-stage-b/`** | **Disabled U14 promotion port: exact 322/320 candidate and 321/319 armed-U13 rollback, future Stage A selftest output bindings, fresh-window retention and synthetic rejection/rollback known answers.** |"
DIGEST = "- U14 promotion prep (2026-10-03,cx-bms): Stage B cannot reuse U13 T8 recovery/318 names. Candidate322/320 restores retained U13 321/319, with future U14 Stage A report+explanations+summary SHA and exact runner-selection binding; malformed fresh signature/smoke must reach rollback. Copy-limit overrides keep ART/JVM1 and reviewed bridge/runtime/javacore1..2, ICU0..1. See benchmark/2026-10-03-u14-stage-b/."


def main():
    pairs = [("inputs/donor/promotion_dispatch_u13.py.txt", "promotion_dispatch_u14.py"),
        ("inputs/donor/promotion_hook_u13_runtime.py.txt", "promotion_hook_u14_runtime.py"),
        ("inputs/donor/review_wait_u13.py.txt", "review_wait_u14.py"),
        ("inputs/donor/test_promotion_u13.py.txt", "test_promotion_u14.py"),
        ("inputs/donor/u14-stage-a-backend-common.txt", "common/transaction_backend.py"),
        ("inputs/donor/u14-stage-a-backend-61b.txt", "61b/transaction_backend.py")]
    deltas = []
    for old, new in pairs:
        path = HERE / "port-deltas" / (new.replace("/", "-") + ".diff")
        path.parent.mkdir(exist_ok=True)
        path.write_text("".join(difflib.unified_diff((HERE / old).read_text().splitlines(keepends=True),
            (HERE / new).read_text().splitlines(keepends=True), fromfile=old, tofile=new)))
        deltas.append(dict(old=old, old_sha256=sha(HERE / old), new=new, new_sha256=sha(HERE / new), diff=str(path.relative_to(HERE)), diff_sha256=sha(path)))
    vm = json.loads((HERE / "vm-replay.json").read_text())
    records = json.loads((HERE / "validation-runs.json").read_text())["records"] if (HERE / "validation-runs.json").exists() else []
    if (HERE / "preflight.json").exists():
        records += json.loads((HERE / "preflight.json").read_text())["records"]
    write(HERE / "results.json", dict(variants={variant: {key: json.loads((HERE / variant / "composition.json").read_text())[key] for key in
        ["bundle_sha256", "base_bundle_sha256", "native_manifest_sha256", "native_inputs_sha256", "execution_enabled"]} for variant in ["common", "61b"]},
        candidate_identity_assertions=322, candidate_unique_paths=320, restored_identity_assertions=321, restored_unique_paths=319,
        ports=deltas, commands=records, vm=vm, production_pass=False, stage_a_signed=False,
        execution_enabled=False, board_access=False, lock_taken=False, gates_written=False, request_cx_t0_review=True))
    write(HERE / "documentation.json", {"README.md": [LAYOUT], ".octos/KNOWLEDGE-DIGEST.md": [DIGEST]})
    paths = [str(path.relative_to(REPO)) for path in HERE.rglob("*") if path.is_file() and ".artifacts" not in path.parts and "__pycache__" not in path.parts
        and not path.name.startswith(".") and path.name not in ["landing-paths.txt", "listing-receipt.json"]]
    paths += [str(path.relative_to(REPO)) for path in (REPO / "specs/u14-stage-b").glob("*.spec.md")]
    paths += ["tools/spec-checks/tests/u14_stage_b.rs", str((HERE / "listing-receipt.json").relative_to(REPO))]
    paths = sorted(set(paths))
    (HERE / "landing-paths.txt").write_text("\n".join(paths) + "\n")
    write(HERE / "listing-receipt.json", dict(paths=len(paths), sha256=sha(HERE / "landing-paths.txt"), execution_enabled=False))
    print("U14 Stage B disabled: paths=" + str(len(paths)) + "; VM replay exit=" + str(vm["exit_code"]))


if __name__ == "__main__":
    main()
