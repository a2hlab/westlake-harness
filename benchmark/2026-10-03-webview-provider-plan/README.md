# Real WebView provider: offline feasibility and staged plan

## Correction and decision

Neither `ASX_WEBVIEW_APK` alone nor a nonnull `WebViewFactoryProvider` renders a page. The effective J8/J10 startup caches an empty proxy **before** trying provider installation; J10e would even overwrite an existing nonproxy provider. CanIWebView's native controls are lit, but its browser region is blank. Restoring `Html.fromHtml` compat moves **0** browser-content walls.

There is a historical real-rendering method donor, not an immediately deployable route-A renderer. AOSP14's actual boot DEX uses **ForT/create** and an update-service multiprocess answer. The newer gap-map claim about a Flags-forced renderer process must not be imported as a fact about this boot JAR.

**Decision:** feasibility is conditional, not package-ready. Plan a fresh-process, opt-in real Chromium route with local software content first, then networking and hardware rendering. Proven first-fatal moves **0**; proven content moves **0**. Conditional local first-content targets **4**, additional remote target **1**, union **5**. No promised newly lit keys. No candidate, native/JAR compilation, VM, board or package edit occurred.

## 1. Copy validated methods, not unverifiable binaries

Primary-source snapshots, original file line numbers, SHA and path commits are in `evidence/source-lines.json`. `donors.json` separates methods, artifacts and validation strength.

| Source | What is actually established | Use / limitation |
|---|---|---|
| Master import `b355ed4ce3`, `benchmark/blockers-ledger.json:83–95` | BurgerKing WebView user policy fixed by `9b8b861`; renderer process remains `fixed_in:null` | Service/renderer gap is not a provider success record. The import-time ledger is retained separately from current source. |
| `harness/westlake_gap/gapmap.py:658–685,833–850` | Classifies WebView and proposes isolated renderer or single-process configuration; service presence is just a source-name hit | Taxonomy, not a running provider. Its conditional newer `Flags` test is not our deployed14 behavior. |
| First200 corpus: `benchmark/loop-outcomes.json`; batches11–15 README | Current loop ledger has201 app records; whole-app draw judgments | A drawn toolbar/splash is not proof of DOM pixels. |
| Framework68 batches16–20 README:5–8,34–42,73 | Uses framework68/opengl11/tz2/nw9; empty web-page region in `standard` is blocked | Framework68 did not universally solve WebView. Do not apply audio ledger gains to M2. |
| Westlake historical `OH-FIVE-GAP-REPAIR-2026-09-04.md:9–16,74–110` (`f82d1f1…`) | Reports candidate05 Toutiao search text/images/scroll, local hardware WebView/JS and HTTPS control; explicitly retains EGL/TLS limits | Validated historical **method** donor. The copied checkout has **0** manifest/results/image/raw-child-log files for this directory; no local binary/hash replay of its58 artifacts. |
| `framework/activity/jni/activity_task_manager_adapter.cpp:419–570`, `e2b0bf66…` | Selected package → provider context → shared assets → native library → provider class | Port the general sequence. Lines697+ are Toutiao wrapper/obfuscated-field stabilization, not needed for our five apps. |
| `framework/core/java/WebViewUpdateServiceAdapter.java:28–76` | Sideloaded package response, `isMultiProcessEnabled=false` | Applicable interface behavior, but adapt exact14 Stub/signatures/service publication and actual package identity. |
| `framework/window/java/OhWebViewBridge.java:10–17` | Opt-in software `View` layer | A real Chromium provider is still required. This is not an ArkWeb implementation. |
| `00.Workspace/src/adapter/aosp_patches/libs/hwui/patches/WebViewFunctorManager.cpp.patch`, `d7531474…` | Replaces a visibility enum with `1` | Neither provider implementation nor verified rendering solution. No local `real-work` checkout identified in bounded named-root inventory; no remote search performed. |

Historical functor helper build (`evidence/hwui-build-source.json`) explicitly links `baseline-libhwui.so` and OH Skia against its own accepted ABI. **Do not** transplant that helper into deployed `be59260f` HWUI without provenance/ABI matching, nor shadow `libandroid`/AssetManager2 as the upstream caller-redirection shim does. Existing source of a method is not proof of our sole runtime/graphics owner.

## 2. Exact route-A caches and required bypasses

Fresh `artifact_identity` output is `evidence/artifact-identity.txt`. Effective runtime **5ae3dd29d45c…** is `bundle/framework/oh-adapter-runtime.jar`, not stale native-payload `d5000c4e`. Boot `framework.jar` is **3e106350d882…**; runtime native owner **ac59dec07719…**. Full hashes are in the DEX/identity evidence.

Coordinates below are **per-DEX dexdump lines**, not Java source lines; evidence includes DEX filename, PC and class/method. Machine-readable changes: `cache-changes.json`.

1. `B7BindFixes.apply`: J8 seed at line11319/offset0x3, J10e at11320/0x6. Package fallback at11516/0x1b5 and provider install at11520/0x1bf are too late. Choose admitted target route before the two seeders.
2. `WebViewProviderFix.install`: reflective `sProviderInstance` (34764), skip when nonnull (34772), otherwise cache zero proxy (34790). Skip seeding on real route; leave existing real provider untouched.
3. `J10eWebView.install`: current guard returns only for its own proxy handler (16514–16524); a nonproxy falls into replacement at16537. Add a real-route/nonproxy preserve guard, not merely the J8 change. It calls J10g at16554.
4. `J10gWebExtras.install`: null `sPackageInfo` becomes fake9999 (19288–19327). Do not seed it for target apps; bind actual selected APK PackageInfo. Separately audit its fallback CookieManager/ServiceWorker globals so they cannot replace real provider-backed services.
5. `WebViewPackageFallback.install/$1.invoke`: replaces ActivityThread IPackageManager (45689); delegates to sideloaded-package helper when available. Use the existing route, but make actual APK/sourceDir/nativeLibDir/version/metadata/signers coherent with update-service and context creation. Current helper hardcodes109 identity; do not copy upstream unsigned-null-signature equality as trust validation.
6. `WestlakeWebViewInstall.install`: availability46444 → native link46449 → prime46452; service/feature is held until publish-after-bind (46464). Reuse unique-owner prime/publication with genuine provider context; distinguish real readiness from synthetic PackageInfo or cached feature flags.
7. `WebViewFactory.getProvider` returns cached global instance at boot line204102; `WebView.ensureProviderCreated` caches each view's `mProvider` at1995470/1995478. Therefore use **fresh target child before any WebView**. Do not clear a live view's cache or hot-swap a real provider. Keep unchanged fallback outside target scope and restore the original opt-in route on rollback.

Boot line204793 selects **WebViewChromiumFactoryProviderForT**. The local provider already has static `create(WebViewDelegate)` (provider line1229069); no ForU rename or Toutiao-specific Compat subclass is necessary for these generic keys. Boot delegate lines203459–203462 calls `IWebViewUpdateService.isMultiProcessEnabled`, matching14r1 source207–213. Single-process exploratory rendering is possible through the real service answer; actual Chromium initialization must still confirm that choice. It is not a blanket production-isolation claim.

## 3. Available APK/native closure versus missing pieces

| Input/component | Exact state |
|---|---|
| Original Android13r80 APK | `westlake-inputs/webview/aosp-android-13.0.0_r80-arm64-webview.apk`, SHA `39655f84bcc079941725f44a0dd6b5e0354281964ad59f65352f4ec0f5540417` |
| Repacked provider APK | `webview-t.apk`, SHA `932c602192978650091b508c54ceb2ed41fa5efd5b8a33118a294c5b7db4dc0d`; Chromium109/compile33/min24. Local apksigner verifies v2/v3, Android Debug signer; verified signature is not an approved system-provider trust policy. |
| APK native/resources | Both APKs have95 `lib/`+`assets/` members including locales/paks and linker/crashpad/arcore helpers; arm64 Chromium member SHA `3279d0c701a0a3e620224bd39c2bf14b6eef74394b7b39103b4b53a367c7de1b`. 32-bit members are not board inputs. |
| External Chromium ELF | `webview-t-lib/libwebviewchromium.so`, SHA `27c34ff45b14fe68a397a6dbe78733731a8da5822ffcb334f8a8588f1546777b`, **not the APK member**. Retains LIBC version requirements. Its transformed imports need a frozen transformation recipe and matching bionic helper; absence of such provenance is a stop gate. |
| NEEDED | `libdl.so`, `libm.so`, `libandroid.so`, `liblog.so`, `libjnigraphics.so`, `libc.so` (readelf output retained). This excludes later `dlopen`/JNI/EGL/driver/service edges, not proof they are unnecessary. |
| Immediate UND coverage |423 strong UND compared with152 payload+retainedOH-system provider paths:13 absent from the union. `wl_getai_oh`, `wl_freeai_oh`, `wl_fillset`, `wl_pthread_mask`, `wl_emptyset`, `wl_sigact`, `wl_conn`, `wl_sjp`, `wl_ljmp`, `wl_addset`, `wl_ismember`, `__pwrite64_chk`, `__pread64_chk`. Other symbols being in the union proves neither version acceptance nor selected namespace resolution. |
| Bionic helper donor | `framework/webview-shim/webview_bionic_shim.c` has renamed boundary adapters/signals/network/FORTIFY source (`evidence/shim-source-lines.json`), history `532633d`/`f8ab5f8`/`fa7bbcf`; no deployed matching helper in T8. Port narrowly against OH ABI/unique owners, not global RTLD_NEXT/caller-based path redirection. |
| Graphics/window owners | T8 has only two private551d `libjnigraphics` copies, no root publication; the tool's maps are explicitly **U9**169 captures, not T8 proof. Our six T8 app maps separately show no browser DSO. Resolve unique compatible JNI/Canvas/Skia owner before any rendering claim; do not duplicate old runtime. |
| APK services | Manifest names sandboxed isolated/external renderer services. They are Java declarations, not route-A service launch/Binder/FD/IPC support. No verified GPU/renderer child host is supplied. No DT_NEEDED shortcut creates these services. |
| HTML branch | Requested but load fails/outside app domain; no HTML DSO in T8. Historical pause is `Html.fromHtml` ArtMethod rewrite, not a browser moratorium. Do not restore it. |

`evidence/provider-inputs.json`, `original-chromium-elf.json`, readelf/signature/manifest outputs, `closure.json` and WHOIS files preserve the exact inventory. Original ELF and full command outputs stay privately at `$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-webview-provider-plan/.artifacts/`; no binary is proposed for admission.

## 4. Phases, real acceptance and integer predictions

| Stage | Minimal scope / exit gate | Conditional first-content movement | First-fatal movement |
|---|---|---:|---:|
| Prerequisite | Frozen APK/ELF/helper provenance; target cache route; actual provider context, update service, single JNI/native owner; all UND/version/namespace gates |0|0|
|1: nonempty local software content | Real Chromium DOM/CSS/JS with software View layer; local virtual origins/interception and app JavaScript interfaces. Not a title label, colored placeholder or no-op provider. |4|0|
|2: network + hardware real rendering | Jiten HTTPS; correct TLS/random/certificates; matching HWUI functor/Canvas/GL/EGL ownership and frame submission, scroll/resize controls. Software stage already performs true rendering, this stage expands fidelity/performance. |+1; union5|0|
| Optional production isolation | Actual sandboxed renderer service/IPC/FD/lifecycle and GPU policy if enabled; separate from this14 single-process feasibility path |0 extra in this six-key cohort|0|

| Key | Stage1 | Stage2 additional | First content / next risk |
|---|---:|---:|---|
|RandomlyDie|1|0| Local Capacitor SPA, JS bridge/plugins/modern APIs may fail next |
|YAM|1|0| Local Capacitor SPA and SafeArea/plugin callbacks |
|Yatoo|1|0| Local SPA on virtualHTTPS origin (`androidScheme=https`), intercept correctly |
|WebRTC-Check|1|0| Local index has visible explanatory text and Run link; camera is a later page. `Android.webviewVersion()` must work; no camera/media-success claim |
|Jiten|0|1| No local HTML/JS/CSS assets; DEX `setupWebView` builds HTTPS URL. DNS/TLS/response/navigation remain explicit |
|CanIWebView|control|control| Already-lit toolbar, blank local virtual-origin browser. Must render the body too; **0 newly lit gain** |

All `1` entries are conditional **content-wall** predictions, not observed/frozen first-fatal changes or guaranteed signed new lit screens. First-fatal0 because the five target reference windows are alive with no established process terminal. Existing screenshots/signoff are not rewritten. Machine tables: `results.json`, `donors.json`, `cache-changes.json`.

First authorized future critical experiment should be just a fresh target child + existing pinned provider + local HTML containing Chinese text and a JS-mutated colored block. Require actual factory class (not Proxy), selected native owners, main-thread JS/body text, local resource callback and externally signed pixels. Failure classes must identify cache, loader/ABI, JNI/Canvas or frame submission; return to unchanged fallback, never swallow a loader failure into synthetic success. No such experiment is executed here.

## 5. Conditional effort, not a scheduling promise

Using module rounds, exploratory risk1.3–1.5, about10% integration and2–4 verification rounds:

| Stage | Base rounds | Risk | Inclusive range | Nominal active-agent time at3min/round |
|---|---:|---:|---:|---:|
| Prerequisite identity/cache/owner gate |6–9|1.3|11–15|33–45min|
| Stage1 native ABI, software Canvas, local JS/interception |18–30|1.5|32–51|96–153min|
| Stage2 TLS/network and matched hardware functor/EGL |16–28|1.5|30–49|90–147min|
| Optional isolated renderer/IPC production |20–40|1.5|36–68|108–204min|

These are planning assumptions, **not a tested implementation estimate**. Exclude download/build queues, source-provenance recovery, human review and device windows. HWUI source/ABI uncertainty, modified Chromium provenance and sole `libjnigraphics` publication can block work before the range starts. Stop after the first decisive identity/native/Canvas gate; do not spend an estimate to paper over failure. Camera/microphone/WebRTC completion is outside these counts.

## Replay and landing

Local collection: `python3 benchmark/2026-10-03-webview-provider-plan/collect.py`, then `plan.py`. Collection requires the retained local inputs; admitted tests do not require APKs, other worktrees, `.artifacts` or VM access.

```
python3 benchmark/2026-10-03-webview-provider-plan/test_plan.py
cargo test --manifest-path tools/spec-checks/Cargo.toml --test webview_provider_plan
```

`landing-paths.txt` lists reports, small hashed evidence, collector/tests and contracts only. Root Layout/DIGEST insertions are supplied separately in `documentation.json`. `validation/` retains fresh lint, test, lifecycle and preflight output. Execution remains disabled; outer review/代land only.
