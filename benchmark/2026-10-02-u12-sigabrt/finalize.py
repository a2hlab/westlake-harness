import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def main():
    observations = json.loads((HERE / "observations.json").read_text())
    providers = json.loads((HERE / "providers.json").read_text())
    asset_rows = [row for row in observations["rows"] if row["key"] != "subwaysurfers"]
    for row in asset_rows:
        text = (HERE / row["disassembly"]["evidence"]).read_text()
        if "AAssetManager_fromJava@plt" not in text:
            raise ValueError("unproved converter path")
    media_symbols = sorted(set(re.findall(r"UND\s+((?:AMedia|AImage)\w+)", (HERE / "evidence/subwaysurfers-unity-symbols.txt").read_text())))
    clusters = [dict(id="asset-converter-JNI-abort", keys=[row["key"] for row in asset_rows], affected_keys=7,
        observable_root="AAssetManager_fromJava tail-call into ART GetLongField -> JniAbort -> SIGABRT",
        field_source="android/content/res/AssetManager.mObject:J", cache_owner="unknown until resolved-owner evidence",
        null_field_id_in_this_attempt="not directly captured; supported by matching converter and prior U8 operand evidence, not asserted from SIGABRT alone",
        donor_commit="b24a118b0aa2fd9e4815cc5a09aabb5a0234bc17", donor_file="framework/webview-shim/android_asset_manager_bridge.cpp:33",
        donor_validation="upstream commit records FediSuite/Sift/CastLab lit; not the current seven inputs",
        transplant="Reuse wl_AAsset* bodies/AssetManager2 helper against initialized sole runtime; adapt namespace publication, C++14/15 ABI and builder inputs; do not copy lazy/default dlopen or build another runtime",
        expected_movement="conditional: converter abort -> asset open/Flutter engine or glmark scene initialization; exact next fatal unknown",
        expected_new_lit_keys="unknown"),
        dict(id="unity-required-media-provider", keys=["subwaysurfers"], affected_keys=1,
        observable_root="libmain native loader FatalError after two libunity dlopen failures; same PID/TID libmediandk missing",
        abort_text="not captured; assembly error branch formats Unable to load library: %s [%s] at rodata0x800 and reaches FatalError0x4dc0",
        alternative_FatalError_branches=["Unable to retrieve Java VM", "Unsupported VM version"],
        source="evidence/subwaysurfers-load-path.txt; hilog44187-44192; evidence/subwaysurfers-unity-needed.txt",
        donor_commit=None, donor_file=None, upstream_verified_media_fix="none found in requested tree or all-branch history",
        required_media_imports=media_symbols, required_media_import_count=len(media_symbols),
        rejected_donor="zigzag presence-only libmediandk has no AMedia implementation; old LIBMEDIANDK-PLAN-v2 failure stubs do not prove fallback",
        repair="Supply real matching AMedia/AImage provider and its namespace closure; then verify library owner and all50 imported APIs. Presence-only publication alone is not a repair",
        expected_movement="unchanged until a real provider exists; with complete provider, libunity relocation/JNI_OnLoad/Unity init is next checkpoint, exact next fatal unknown",
        expected_new_lit_keys="unknown")]
    predictions = []
    for row in observations["rows"]:
        cluster = clusters[1] if row["key"] == "subwaysurfers" else clusters[0]
        predictions.append(dict(key=row["key"], cluster=cluster["id"], current_first_fatal=row["observable_abort_site"],
            signal_evidence=row["run"] + "/hilog.txt:" + str(row["signal_line"]), caller_pc=row["caller_pc"],
            proposed_fix=cluster.get("transplant") or cluster["repair"], donor_commit=cluster["donor_commit"],
            first_fatal_prediction=cluster["expected_movement"], next_exact_fatal="unknown", t20_prediction="unknown",
            no_repair_prediction="same recorded first fatal", hardware_validated=False))
    result = dict(status="READ_ONLY_ROOT_CAUSE_AND_CONDITIONAL_REPAIR_PLAN", source_commit="2aa6c49df0", execution_enabled=False,
        device_io=False, keys=8, clusters=clusters, predictions=predictions,
        abort_messages_captured=0, standalone_cppcrash_files=0, in_hilog_pid_tid_bound_stacks=8,
        observed_libsurface_preload_failure_keys=[], newly_lit_prediction_supported=[], providers=providers["rows"])
    (HERE / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    documentation = {
        "README.md": ["| **`benchmark/2026-10-02-u12-sigabrt/`** | **Candidate window5 eight SIGABRT roots: seven AAssetManager/GetLongField converter aborts and one Unity missing-media loader failure; PID/TID-bound stacks, hashed caller disassembly, donor and conditional repair predictions.** |"],
        ".octos/KNOWLEDGE-DIGEST.md": ["- U12 SIGABRT window5 (2026-10-02,cx-bms): six Flutter keys including LocalSend plus glmark2 call AAssetManager_fromJava at each captured caller PC then ART GetLongField/JniAbort; no app-PID libsurface preloading error precedes these eight terminals. Root9cc and runtimeac59 still have separate converter/cache definitions, selected GOT owner unobserved. Unity libmain4dc0 FatalError follows same-TID libunity NEEDED libmediandk failures44187–44192; its load-failure branch4df4 formats rodata800, not proof of a VM-version error. No standalone crash/abort text captured; b24a118 asset companion is a conditional sole-owner donor, no validated AMedia donor or exact next fatal. See benchmark/2026-10-02-u12-sigabrt/."]}
    (HERE / "documentation.json").write_text(json.dumps(documentation, indent=2) + "\n")
    paths = [path for path in HERE.rglob("*") if path.is_file() and not any(part in {".artifacts", "__pycache__"} for part in path.relative_to(HERE).parts)]
    paths += [HERE / "landing-paths.txt", HERE / "evidence/preflight.txt", REPO / "tools/spec-checks/tests/u12_sigabrt.rs"]
    paths += list((REPO / "specs/u12-sigabrt").glob("*.spec.md"))
    (HERE / "landing-paths.txt").write_text("\n".join(sorted({str(path.relative_to(REPO)) for path in paths})) + "\n")
    print("8 keys -> asset converter7 + Unity media loader1; abort text unavailable; donor b24a118 conditional, next exact fatal unknown")


if __name__ == "__main__":
    main()
