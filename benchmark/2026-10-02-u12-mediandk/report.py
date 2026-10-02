import json
import re

from collect import HERE, REPO, portable, save, sha


def load(name):
    return json.loads((HERE / name).read_text())


def main():
    build = load("build-receipt.json")
    policy = load("policy-receipt.json")
    gate = load("namespace-gates.json")
    observations = load("observations.json")
    unity = next(row for row in observations["rows"] if row["key"] == "subwaysurfers")
    chess = next(row for row in observations["rows"] if row["key"] == "cv2-com-chessclock-android")
    predictions = [dict(key=unity["key"], current_first_fatal="libmain FatalError after libunity NEEDED libmediandk.so failure; SIGABRT",
                       evidence=unity["run"] + "/hilog.txt:44187", components=["new-root-mediandk", "trusted-manifest-row"],
                       conditional_first_wall_moved=True,
                       condition="final frozen loader build + both route/root aliases + app namespace resolves new root provider and all remaining Unity imports",
                       next_first_fatal="unknown: further relocation/JNI_OnLoad/media capability initialization or an unsupported result; no fallback proof",
                       t20="unknown", first_fatal_after="unknown"),
                   dict(key=chess["key"], current_first_fatal="media_jni absent from trusted adapter manifest; MediaPlayer.<clinit>",
                       evidence=chess["run"] + "/hilog.txt:43043", components=[], conditional_first_wall_moved=False,
                       condition="libmediandk patch is unrelated; reviewed media_jni owner alias is a separate task",
                       next_first_fatal="same MediaPlayer manifest ULE unless separate media_jni repair is admitted", t20="unknown",
                       first_fatal_after="same wall for this patch alone")]
    save("predictions.json", dict(conditional_first_wall_movement=1, proven_lights=0, rows=predictions))
    allow = []
    for name in ["strings-mediandk", "strings-policy-candidate", "strings-policy-rebuild"]:
        for line in (HERE / "evidence" / (name + ".txt")).read_text().splitlines():
            if not line.startswith(("DROPPED", "ADDED")):
                continue
            reason = "exact trusted root provider publication path; shared table unchanged" if name.startswith("strings-policy") else (
                "replace false presence-only label with truthful typed unsupported boundary label" if "westlake-mediandk" in line else
                "unsupported diagnostic function-name/context; does not imply a working codec")
            allow.append(dict(comparison=name, delta=line, reason=reason, outer_approved=False))
    save("strings-review.json", dict(rows=allow, deployment_authorized=False))
    save("offline_precheck.json", dict(execution_enabled=False, package_manifest_sha256=gate["package_manifest_sha256"],
         expect=dict(confirm="libunity no longer reports missing libmediandk.so or missing 50 listed media imports; provider diagnostic may report -10002; first fatal and UI scored separately",
                     refute="same PID reports libmediandk.so absent/missing media symbol; or wrong provider/namespace; candidate is not proven effective"),
         admission_blocks=["frozen Linux loader rebuild required", "new manifest N2 exception rebinding needs outer approval",
                           "live app provider resolution not yet verified", "full Unity relocation closure and runtime fallback unknown"],
         artifacts=[dict(target="/system/android/lib64/libmediandk.so", sha256=build["candidate_sha256"]),
                    dict(target="libnativeloader route+root aliases", comparison_sha256=policy["artifacts"]["candidate1"]["sha256"])],
         chessclock_beneficiary=False))
    save("results.json", dict(schema="u12-mediandk-typed-boundary-v1", device_io=False, execution_enabled=False,
         library=build["candidate_sha256"], policy_comparison=policy["artifacts"]["candidate1"]["sha256"],
         source_commit=load("sources.json")["commit"], source_files=65, imported_apis=50, exports=52,
         unsupported_error=-10002, conditional_wall_movement=1, predicted_lights="unknown", chessclock_mediandk_benefit=0,
         gates=gate, focused_provider_closure=load("provider-closure.json"), runtime_fallback_verified=False))
    save("documentation.json", {"README.md": ["| **`benchmark/2026-10-02-u12-mediandk/`** | **Unity 50 real imports, AOSP14 typed unsupported errors; Chessclock kept separate.** |"],
         ".octos/KNOWLEDGE-DIGEST.md": ["- U12 media names must be resolved from actual PID logs + deployed DEX: window5 Unity needs libmediandk (44187–44192), Chessclock loads media_jni (MediaPlayer clinit/43043–43055), not libmediandk. AOSP14 AMEDIA_ERROR_UNSUPPORTED=-10002, not old-plan -1002; 50-export loader coverage does not prove Unity fallback or lighting. See benchmark/2026-10-02-u12-mediandk/."]})
    for path in HERE.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".txt"} and not any(part in path.parts for part in [".artifacts", "__pycache__", "inputs"]):
            text = path.read_text()
            path.write_text(portable(text))
    print("media imports=50/50, exports=52; conditional wall movement=1, Chessclock=0, t20=unknown; generation admission disabled")


if __name__ == "__main__":
    main()
