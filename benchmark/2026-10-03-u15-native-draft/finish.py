import json

from common import BASE, HERE, LOCAL, MASTER, PARTIAL, REPO, capture, save, sha
from validation import BASES, CHANGES, check_partial, check_review

LAYOUT = "| **`benchmark/2026-10-03-u15-native-draft/`** | **U14-based disabled native staging: runtime94c3 + host9e3a + both ANL b96a aliases, fresh N1/N2 preview, 219 consumers and unsigned open/string/call review; NSD BCP pair pending.** |"
DIGEST = "- U15 native草稿(2026-10-03,cx-bms):三件四路径(runtime94c3/host9e3a/ANL b96a双别名)须同进同退，Meet两名单+needs_runtime一致；编译后host源是release63e2而非builder的未打补丁inputs。N1/N2有效报告204同项preview/0新但未落绑定仍REJECT；开点197/8/0与namespace delta全无不等于调用零差，runtime仅EGL函数新增直连转换+HiLog。framework9e55+待到NSD须一次全27新配对，旧framework-only计划不能先跑；无bundle描述符/事务基座未填，不借U14图像批文。见benchmark/2026-10-03-u15-native-draft/。"


def main():
    state = json.loads((HERE / "composition.json").read_text())
    old = json.loads((BASE / "native/package.json").read_text())
    new = json.loads((PARTIAL / "native/package.json").read_text())
    check_partial(old["files"], new["files"], state, (PARTIAL / "bundle.json").exists())
    for member, digest in new["files"].items():
        if sha(PARTIAL / "native" / member) != digest:
            raise ValueError("Composed payload changed after static checks")
    for variant, root in [("common", BASE), ("61b", LOCAL)]:
        if sha(root / "bundle.json") != BASES[variant]:
            raise ValueError("U14 content base changed")
    report = json.loads((HERE / "report-summary.json").read_text())
    check_review(report)
    capture("composition-check", ["python3", HERE / "test_draft.py"])
    save("rebake-hold.json", dict(execution_enabled=False, reason="NSD stubs donor pending; framework plus NSD must share one 27-image rebake",
        changed_bcp_expected=["framework.jar", "adapter-mainline-stubs.jar"], framework_candidate_sha256="9e55e28623c86cc553bb2449cb18948e383a05fb0283b045d969655813b7d1b7",
        nsd_stubs_candidate_sha256=None, prior_framework_only_plan="benchmark/2026-10-03-u15-plan/plan.json",
        prior_plan_is_executable_u15_pair=False, prior_images_selected=False, actual_outputs=None, approval=None))
    save("results.json", dict(status="NATIVE_STAGING_COMPLETE_FULL_U15_DISABLED", native_manifest_sha256=state["native_manifest_sha256"],
        native_inputs_sha256=state["native_inputs_sha256"], final_bundle_sha256=None, native_objects=3, changed_payload_paths=4,
        changes=CHANGES, content_bases=BASES, transaction_base=state["transaction_base"], execution_enabled=False, deploy_allowed=False,
        promotion_confirmed=False, native_gate_raw_status=report["native_candidate"], auto_identical_preview=204, new_findings=report["new_findings_by_gate"],
        consumers=219, abi=report["abi"], image_bake_run=False, production_run=False, vm_used=False, device_access=False,
        approvals_applied=False, active_registry_updated=False, bcp="U14 historical inventory only; framework+NSD pair pending",
        source_validation_correction="builder inputs are pre-patch; bind release u15jitsi-stock-host.c63e2 SHA for actual host",
        donor_predictions=dict(m3_first_wall_targets=3, mindustry_first_wall_targets=1, fd_meet_first_wall_targets=1, observed_moves=0, lit="not inferred"),
        checks="evidence/test and lifecycle outputs are computational proof, not production admission"))
    save("documentation.json", dict(layout_row=LAYOUT, digest_append=DIGEST, note="Apply snippets only, not accumulated root documents"))
    paths = sorted(str(path.relative_to(REPO)) for path in HERE.rglob("*") if path.is_file() and ".artifacts" not in path.parts
        and "__pycache__" not in path.parts and path.name not in ["landing-paths.txt", "listing-receipt.json"])
    paths.extend(str(path.relative_to(REPO)) for path in (REPO / "specs/u15-native-draft").glob("*.spec.md"))
    paths.extend(["tools/spec-checks/tests/u15_native_draft.rs", str((HERE / "listing-receipt.json").relative_to(REPO))])
    paths = sorted(set(paths))
    (HERE / "landing-paths.txt").write_text("\n".join(paths) + "\n")
    save("listing-receipt.json", dict(paths=len(paths), sha256=sha(HERE / "landing-paths.txt"), native_binaries=False, executable_bundle=False))
    print("LANDING paths=" + str(len(paths)) + " sha=" + sha(HERE / "landing-paths.txt") + "; no bundle descriptor; native bindings are preview only")


if __name__ == "__main__":
    main()
