from pathlib import Path

from common import HERE, REPO, load, save, sha
from validation import check_admission, check_atomic, check_pair_template, check_preview


def main():
    check_preview(load("registry-delta.preview.json"), load("old-partial-final-mapping.json"))
    check_atomic(load("evidence/atomic-files.json"))
    check_admission(load("flutter-admission-decision.json"))
    expected = load("expected-pair.json")
    check_pair_template(load("paired-receipt.template.json"), expected["inputs"], expected["images"])
    save("results.json", dict(status="PREPARED_PENDING_DONORS_AND_FINAL_BINDING", applied=False, execution_enabled=False,
        promotion_confirmed=False, registry_rows=204, gates=dict(N1=99, N2=105), new_findings=0,
        flutter_new_native_rows=0, flutter_admission_rule="existing target replacement; recheck signed effective transaction base",
        final_bundle_sha256=None, final_native_manifest_sha256=None, final_inputs_sha256=None,
        runtime_jar_candidate_sha256=None, candidate_image_hashes=None, paired_receipt_status="NOT_RUN",
        active_inputs_unchanged=load("active-inputs-unchanged.json"), builds=False, vm_access=False, board_access=False))
    save("documentation.json", dict(
        layout_row="| **`benchmark/2026-10-03-u15-admission-prep/`** | **204 exact old/partial/final binding previews, signed atomic strings condition, Flutter replacement admission decision and two-run unknown paired receipt while U15 donors are pending.** |",
        digest_append="- U15准入备料(2026-10-03,cx-bms):204旧项先保留U14→partial→final空列，JAR/镜像到件后fresh报告重算ID，不替换SHA伪造绑定；Flutter9b82在U14是既有target替换，new-native表仅deployed=None才需行，实际按板BASE仍须重查。strings20批准只绑b6b4与ANL b96a/host9e3a同进同退，不批准图像或JAR。见benchmark/2026-10-03-u15-admission-prep/。"))
    paths = [str(path.relative_to(REPO)) for path in HERE.rglob("*") if path.is_file()
        and ".artifacts" not in path.parts and "__pycache__" not in path.parts
        and path.name not in ["landing-paths.txt", "listing-receipt.json"]]
    paths.extend(str(path.relative_to(REPO)) for path in (REPO / "specs/u15-admission-prep").glob("*.spec.md"))
    paths.extend(["tools/spec-checks/tests/u15_admission_prep.rs", str((HERE / "listing-receipt.json").relative_to(REPO))])
    paths = sorted(set(paths))
    (HERE / "landing-paths.txt").write_text("\n".join(paths) + "\n")
    save("listing-receipt.json", dict(paths=len(paths), sha256=sha(HERE / "landing-paths.txt"),
        final_binding=False, execution_enabled=False, binaries=False))
    print("U15 ADMISSION PREP paths=" + str(len(paths)) + " listing=" + sha(HERE / "landing-paths.txt"))


if __name__ == "__main__":
    main()
