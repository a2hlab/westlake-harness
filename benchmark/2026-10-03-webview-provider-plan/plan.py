import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(name):
    return json.loads((HERE / name).read_text())


def save(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def main():
    closure = read("evidence/closure.json")
    keys = read("evidence/six-keys.json")["rows"]
    phases = [
        dict(id="prerequisites", content_moves=0, first_fatal_moves=0, conditional=False,
             scope="Pinned provider identity, no fallback cache, singleton JNI/native closure; not visible content",
             modules=["APK/repacked ELF provenance and certificates", "before-first-WebView opt-in cache route",
                      "unique provider context and resident owners"], base_rounds=[6, 9], risk=1.3,
             rounds_including_integration_and_verification=[11, 15],
             acceptance="Reject cached proxy, fake9999, missing imports or unbound artifact provenance; do not count provider construction as rendered UI"),
        dict(id="local-software-content", content_moves=4, first_fatal_moves=0, conditional=True,
             scope="Real Chromium DOM/CSS/JS, software View layer, local assets and app JS/asset interception",
             modules=["WebView bionic/native ABI adapters", "software Canvas/Skia handoff and frame submission",
                      "Capacitor local origin and JavaScript bridge", "local content and CanI regression controls"],
             base_rounds=[18, 30], risk=1.5, rounds_including_integration_and_verification=[32, 51],
             acceptance="Main-thread JS confirms expected DOM and mutated pixels; external signed screenshot shows nonblank WebView region; local assets and app callbacks actually execute"),
        dict(id="network-hardware-rendering", content_moves=1, first_fatal_moves=0, conditional=True,
             scope="Additional Jiten HTTPS navigation plus real HWUI functor/GL surface rendering for all six controls",
             modules=["TLS/entropy/certificate chain and network boundary", "matching HWUI/Skia functor and EGL lifecycle",
                      "navigation/resize/scroll regression and owner checks"], base_rounds=[16, 28], risk=1.5,
             rounds_including_integration_and_verification=[30, 49],
             acceptance="Jiten real remote body plus JS and signed pixels; GPU-enabled runs have matching owner/ABI and scroll/resize; TLS failures remain explicit, never bypass trust"),
        dict(id="isolated-renderer-production-followup", content_moves=0, first_fatal_moves=0, conditional=True,
             scope="Optional isolated Chromium renderer/IPC and recovery; not a prerequisite to the AOSP14 single-process feasibility probe",
             modules=["isolated service process launch/bind", "Binder/FD/shared memory/IPC and lifecycle",
                      "GPU policy and owner-safe process recovery"], base_rounds=[20, 40], risk=1.5,
             rounds_including_integration_and_verification=[36, 68],
             acceptance="An actual service/renderer process binds and submits frames; manifest declaration or grep hit is not hosting proof"),
    ]
    rows = []
    for row in keys:
        control = row["key"] == "cv2-com-caniwebview-android"
        remote = row["key"] == "cv2-dev-obfusk-jiten-webview"
        local = not control and not remote
        if "webrtc" in row["key"]:
            content = "file:///android_asset/index.html; static WebRTC-Check body, Android.webviewVersion bridge; camera test only after Run link"
            next_wall = "JavaScript Android bridge; later camera/microphone permissions or real WebRTC media, not needed for initial text"
        elif control:
            content = "https://caniwebview.local/assets/html/index.html via WebViewAssetLoader; native toolbar already lit"
            next_wall = "shouldInterceptRequest/virtual origin and DOM; no newly-lit key"
        elif remote:
            content = "setupWebView assembles https:// server URL and calls loadUrl; zero local HTML/JS/CSS assets"
            next_wall = "network/TLS/server response and navigation; exact next terminal unknown"
        else:
            content = "Capacitor local assets/public/index.html + SPA JS/CSS; virtual local origin, Yatoo androidScheme=https"
            next_wall = "Capacitor shouldInterceptRequest, local origin, addJavascriptInterface, modern JS APIs and plugin callbacks"
        rows.append(dict(key=row["key"], signed_verdict=row["signed"]["verdict"], pids=row["app_pids"],
                         run=row["run"], apk_sha256=row["apk"]["apk_sha256"], content=content,
                         first_fatal_moves=0, proven_content_moves=0,
                         phase1_conditional_content_move=int(local), phase2_additional_conditional_content_move=int(remote),
                         already_lit_control=control, next_wall=next_wall,
                         evidence="evidence/six-keys.json; accepted M2 calls/lines and signed screenshot hashes"))
    save("results.json", dict(schema=1, execution_enabled=False, candidates_created=0,
         board_operations=0, builds=0, signed_basis="U10.1T8 window5 accepted M2; not current U12 signoff",
         rows=rows, phases=phases, proven_first_fatal_moves=0, proven_content_moves=0,
         phase1_conditional_content_moves=4, phase2_additional_conditional_content_moves=1,
         conditional_union_content_moves=5, guaranteed_new_lit_keys=0,
         html_compat_restore_content_moves=0,
         effort=dict(unit="agent round", nominal_minutes_per_round=3,
                     calculation="base * risk + approximately10% integration +2-4 verification rounds, rounded ranges",
                     excludes=["build/download queue", "blocked provenance recovery", "external review", "device window and screenshot signoff"],
                     stop_rule="Do the first provider/native/Canvas ABI gate before committing the exploratory range; no estimate overrides a failed owner/provenance gate")))
    runtime = read("evidence/runtime-dex.json")
    boot = read("evidence/boot-dex.json")
    changes = [
        dict(id="before-bind-route", location="B7BindFixes.apply", evidence_lines=[11319, 11320, 11516, 11520],
             change="Select an opt-in target route before offset0x3 J8 and offset0x6 J10e, not after offset0x1bf provider install; preserve fallback outside targets"),
        dict(id="j8-global-cache", location="WebViewProviderFix.install", evidence_lines=[34764, 34772, 34790],
             change="Skip proxy seeding for admitted real-provider target; never reset a real provider or live WebView"),
        dict(id="j10-enrichment", location="J10eWebView.install", evidence_lines=[16514, 16519, 16524, 16537, 16554],
             change="Skip on real route and preserve nonproxy existing provider; current code replaces any nonproxy provider, not only J8"),
        dict(id="fake-package-cache", location="J10gWebExtras.install", evidence_lines=[19288, 19296, 19300, 19327],
             change="Do not seed fake9999 for targets; publish verified selected APK PackageInfo and metadata before use, retain concrete fallback extras only outside real route"),
        dict(id="package-query", location="WebViewPackageFallback.install/invoke + WestlakeWebViewInstall.getSideloadedWebViewPackageInfo",
             evidence_lines=[11516, 45689, 46248, 46350],
             change="Return consistent actual provider identity through IPackageManager/context creation; bind signer, APK, lib/data path and metadata rather than hardcoded unsigned PackageInfo"),
        dict(id="service-publication", location="WestlakeWebViewInstall.install + unique runtime prime/publish after bind",
             evidence_lines=[46444, 46449, 46452, 46464],
             change="Publish real update-service and context only after coherent provider readiness; no feature true or success from a fake provider"),
        dict(id="per-view-cache", location="WebView.ensureProviderCreated + WebViewFactory.getProvider",
             evidence_kind="boot dexdump", evidence_lines=[204102, 204149, 1995470, 1995478],
             change="Fresh child before first WebView; global sProviderInstance and each view mProvider prevent late env-only switching; no hot cache clearing"),
    ]
    save("cache-changes.json", dict(runtime_sha256=runtime["sha256"], boot_sha256=boot["sha256"],
         evidence_coordinate="Original per-DEX dexdump line, with dex name/PC in the full evidence JSON, not Java source line", changes=changes))
    inputs = read("evidence/provider-inputs.json")
    sources = read("evidence/source-lines.json")["files"]
    save("donors.json", dict(upstream_import="b355ed4ce3", source_files=[
         dict(path=item["path"], sha256=item["sha256"]) for item in sources],
         verified_historical_method=dict(commit="f82d1f1a9d0a8760de6bb215f8d130cbb81b21a4",
             report="evidence/source-lines.json: OH-FIVE-GAP lines9-16,74-110",
             report_claim="Candidate05: real Toutiao search text/images/scroll, local hardware HTML/JS, HTTPS control",
             raw_results_available_locally=False, exact_route_a_artifact_reproduction=False,
             missing=["candidate05 manifest/58 frozen binaries", "screenshots and raw control logs", "accepted historical HWUI ABI inputs"],
             use="source method donor, not current route-A PASS"),
         framework68_loader=dict(commit="e2b0bf669ca33459c74618883614f4c603fbccbb",
             path="$WORKSPACES/vm-copies/westlake-current/framework/activity/jni/activity_task_manager_adapter.cpp:419",
             portable_sequence=["wait selected provider", "create provider context", "publish actual package", "assets shared path", "native load", "ForT factory"],
             do_not_copy=["Toutiao TTWebProviderWrapper/obfuscated fields", "RTLD_NEXT helper architecture", "shadow libandroid or private AssetManager/JNI owner", "unsigned hardcoded PackageInfo"]),
         workspace_patch=dict(commit="d7531474a77ad5e26e4418508d318eb8be3ae3aa",
             path="$WORKSPACES/00.Workspace/src/adapter/aosp_patches/libs/hwui/patches/WebViewFunctorManager.cpp.patch",
             verdict="visibility enum replacement only; not a provider or a verified software renderer"),
         real_work_lookup=dict(searched_roots=["$WORKSPACES", "$WORKSPACES/00.Workspace/code", "$HOME/a2hlab"],
             lookup_scope="bounded local directory inventory, no remote searches",
             verdict="No local real-work checkout identified; no evidence of a verified donor there, not proof of global absence"),
         provider_apks=inputs, extracted_chromium_sha256=closure["consumer_sha256"],
         extracted_chromium_matches_apk_member=False,
         strong_undefined_count=len(closure["strong_undefined"]),
         missing_from_inventory=[item["symbol"] for item in closure["strong_undefined"] if not item["inventory_export_paths"]],
         provider_namespace_visibility="unproved", gpu_renderer_host="not supplied; APK service declarations do not implement it",
         upstream_framework68_current_ledger="wv:renderer-process fixed_in=null; blind batch standard web page region empty; no universal renderer unlock"))
    manifest = [dict(path=str(path.relative_to(HERE)), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                for path in sorted((HERE / "evidence").glob("*")) if path.is_file()]
    save("evidence-index.json", manifest)
    print("PLAN: proven0; local conditional4 + remote conditional1 =5; CanI new-lit0; no candidates")


if __name__ == "__main__":
    main()
