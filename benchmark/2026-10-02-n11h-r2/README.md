# N11h-r2 — FINAL VERDICT: SHELVED (prediction 0; double copy causes no observed first fatal)

> After the outer refuted the white-window prediction (double copy is on 115/115 lit keys too, so it is benign for
> rendering), the only bad-key-exclusive signal was the AAssetManager_fromJava->GetLongField->JniAbort cluster. Static
> + runtime check of the 4 keys that actually terminate there (glmark2, localsend, fd-fluffychat, fd-immich) shows it
> is **NOT a double-copy mechanism** (`evidence/assetmanager-jniabort-not-doublecopy.txt`):
> (b) the AssetManager.mObject fieldID cache IS filled ("OH_AssetOffsets: AssetManager.mObject cached in runtime and
> libandroid NDK owner"); (c) the GetLongField abort is on a NULL **object** (x0=0 at the abort frame, all four), not a
> null/stale fieldID; (a) path = the app's own native_getSceneInfo -> AAssetManager_fromJava -> GetLongField(null obj).
> The null is the Java AssetManager object (app/framework level); a single bridge/runtime owner would not change it.
>
> **Therefore, per the dispatch's gate ("若查下来不是双拷贝机制,N11h-r2 整件就搁置,预测 0 不开工"), N11h-r2 is SHELVED.**
> The double bridge/runtime copy causes NO observed first fatal: benign on all 115 lit + 17 white keys, and the 7-key
> GetLongField JniAbort is a null-object wall with the cache already filled. N11h single-owner predicted benefit = 0 keys.
> No host patch is produced. The CREATE_INHERIT_DEFAULT root cause (below) remains accurate for *where* the second copy
> comes from, but since the second copy harms nothing, the outer's call to NOT touch it (blast radius 166 keys, benefit
> 0) stands. The GetLongField-null-object wall is a separate, non-N11h investigation.
>
> The sections below are the prior-round design/root-cause (kept for the trail); they are superseded by this verdict.

---

# N11h-r2 — UPDATE (outer correction applied; root cause FOUND)

> The outer corrected precondition A: the source is NOT missing — my first pass read the OLD tree
> (`_cc-wiki-b1-src`, f754fa9a, where `CLF_createClassloaderNamespace` returns null). The current source is
> `bms/src/adapter/framework/` (android-runtime CLF -> libnativeloader `native_loader_registry.cpp` ANL_CreateDomain
> -> libapp_native_loader `app_native_loader.c`). With the right tree, the **root cause is now pinned**:
>
> **Copy B is created by `CREATE_INHERIT_DEFAULT` at the CL bridge-namespace creation** in the N11h host
> `candidate-stock-host.c:197` — the bridge ns inherits `default`, which supplies `liboh_adapter_bridge.so` /
> `liboh_android_runtime.so` fresh from `/system/android/lib64` BEFORE the sealed.child inherit (line 216). The
> sealed inherit the dispatch proposed is **already present** (marker 12494, rc=0) and cannot collapse the default edge.
> The app ns (line 224) correctly uses `LOCAL_NS_PREFERED` (no default); the bridge ns does not — that asymmetry is
> the bug. See `evidence/root-cause-create-inherit-default.txt` and the corrected `fix-spec.md`.
>
> **Corrected fix (single logical change, in candidate-stock-host.c — the host, NOT ANL):** stop `default` from
> supplying the two owner libs (bridge ns: `LOCAL_NS_PREFERED` + base-libs-only default inherit; app-ns flutter/native
> branch: drop runtime/bridge from its default-inherit list), so `westlake.sealed.child` is their only source. Plus the
> JNI_OnLoad guard (precondition B, unchanged — copy A's bridge already ran an incomplete JNI_OnLoad; the once-flag must
> set only on complete success). The host rebuild + window belongs to the cx-bms lineage; cc-wiki delivers the pinned
> root cause + exact edit. No build here (host-build + window to be coordinated with the corrected direction).
>
> The sections below are the first-pass report (kept for the trail); where they say "source missing", read this update.

---

# N11h-r2 — minimal fix for the second bridge/runtime copy: design done, build BLOCKED (2 preconditions)

Static-first, no board. Per the N11h double-copy forensics (`benchmark/2026-10-02-n11h-doublecopy`), the second copy
is the **B8 runtime-CL native namespace** (the Android per-ClassLoader namespace) which never links the sealed owner.
This round located the source, designed the one-variable `dlns_inherit` fix, and — per the dispatch's "answer the
fix-invalidating question first" — found **two preconditions that block a clean build**. Reported, not forced.

## 1. Source of the B8 runtime-CL namespace — located; the creating code is NOT in any reachable source
- The B8 strings live in **`framework/oh-adapter-runtime.jar` → `com.android.internal.os.AppSpawnXInit`**
  (`[B8-NATIVE] native namespace created for runtime CL`, `createClassloaderNamespace returned: <name>`).
- The native `createClassloaderNamespace` is `framework/android-runtime/src/com_android_internal_os_ClassLoaderFactory.cpp`
  → compiled into `liboh_android_runtime.so`. **In the current source (vm-copies/westlake-current @532633d) it is a
  NO-OP: `CLF_createClassloaderNamespace() { return nullptr; }`** ("OH manages namespaces differently … null = no
  error, default ns"). But the **deployed** one RETURNS A NAME (it creates a namespace — hilog
  `createClassloaderNamespace returned: <name>`).
- **`B8-NATIVE` / `native namespace created for runtime CL` is absent from every reachable source** (vm-copies all
  commits of AppSpawnXInit.java + appspawn-x/src/*.cpp; a2hlab `~/a2hlab/ws/westlake`; hw248 `/opt/wl-src` + lab-state;
  westlake-inputs). So the deployed jar + the namespace-creating `createClassloaderNamespace` are from a **source
  iteration not in any repo here** — the same provenance gap as the ICU-72 deployed binary. Evidence:
  `evidence/source-search.txt`. **Precondition A: the deployed B8/createClassloaderNamespace source must be sourced
  before the fix can be built against the lineage that actually runs the double copy.**

## 2. The fix (design) — `fix-spec.md`
After the CL namespace is created, one new-file native helper links it to the sealed owner, mirroring the host's
`StockCreateConfiguredNamespaces@0xccf0`: `dlns_get(cl_ns) + dlns_get(westlake.sealed.child) + dlns_inherit(cl, sealed,
"liboh_adapter_bridge.so:liboh_android_runtime.so")`, called once right after the CL-ns name is obtained and before any
`[B8-NATIVE] loaded …`. Full spec + call site in `fix-spec.md`. Single new file, one call.

## 3. The fix-invalidating question — ANSWERED: the bare inherit is NOT a clean single variable
`evidence/jni-onload-state.txt`. ART `JavaVMExt::LoadNativeLibrary` keys `libraries_` by path; copy A was dlopen'd
**natively** by host/child (`RealOpenLocalNow`), so it is not in `libraries_`. If the inherit routes the CL-side
`System.loadLibrary` to copy A, ART would call `JNI_OnLoad` on copy A. But:
- **copy A's bridge ALREADY ran `JNI_OnLoad` once** — hilog 12254 `JNI_OnLoad: oh_adapter_bridge entered` (early native
  load, before B8), though incomplete (`FindClass(AppSpawnXInit) returned null`). So the inherit alone makes ART
  **re-enter `JNI_OnLoad` on copy A's bridge = a second init / re-RegisterNatives on the same copy.**
- runtime JNI registration is entirely on copy B (OH_RegHook 1386→copy B `7eebded`, 0→copy A `7ed6a2d`); consolidating
  to A also moves the registration surface.
- a consumer already hit namespace-view fragmentation (`OH_GfxShim: … liboh_android_runtime.so is not already loaded`).

**So the fix is a TWO-variable change:** the `dlns_inherit` PLUS one of {bridge/runtime `JNI_OnLoad` made idempotent;
register copy A with ART `libraries_` at the native load so ART won't re-run `JNI_OnLoad`; or route the host/child
native load through ART's registration}. No "already opened by ClassLoader" ULE was observed (no prior CL loaded the
owner by path), so that specific hazard is clear — but the double-`JNI_OnLoad` on copy A is real.
**Precondition B: pick the JNI_OnLoad-idempotency approach before the window.**

## 4. Prediction (CONDITIONAL — only if a correct single-owner fix lands)
Per `benchmark/2026-10-02-candidate-first-fatal-clusters/clusters.json`:
- **white-window double-copy cluster = cluster[0]** (`signature kind=no-observed-termination`, **20 keys**: fd-noice,
  fd-uhabits, noice, toutiao, fd-shatteredpixeldungeon, termux, yahtzeedicer, and the cv2 consistent-white keys
  cv2-{ca-vaults-randomlydie, com-bytehamster-flowitgame, com-degeder-yam, com-emmanuelmess-itsdicey,
  com-frequent-habits, com-paultirk-yatoo, dev-obfusk-jiten-webview, org-andresoviedo-dddmodel2, timur-webrtc-check},
  fd-{AppManager, app, mobile, tutanota}). These run without a termination = the double-copy white-window symptom; a
  true single owner is the candidate to move their first "fatal" (the non-render). **Judge the white-lottery members by
  k/n, not a single launch.**
- **AssetManager GetLongField cluster (≈7: cv2-org-linaro-glmark2 + the Flutter/localsend keys localsend, fd-fluffychat,
  fd-immich, fd-im-vector-app, mindustry, fd-meet)**: these JniAbort at `AAssetManager_fromJava → GetLongField(mObject
  null)` because copy B's `AssetManager.mObject` cache is unfilled (DIGEST 2026-10-01 fid==null = the two-copy disease).
  A single owner **may** fix them — BUT only if copy A's `AssetManager.mObject` cache is the one ART fills; the inherit
  alone does not guarantee that (it is the same open question as precondition B). **Not asserted** until the registration
  path is settled.

Because both preconditions are open, this round does **not** claim a firm "keys whose first fatal moves" set; the two
clusters above are the candidate scope, conditional on a correct two-variable fix.

## 5. Build + window — BLOCKED (precondition A)
No byte-reproducible product and no 61b window input are produced: the deployed B8/createClassloaderNamespace source is
not reachable (precondition A), and the fix is two-variable not one (precondition B). Producing a window now would ship
an unverifiable or hazardous candidate. Per AGENTS "静态先证" + the dispatch's "先回答会让修法失效的问题再动手", I stop
at the design + the two preconditions.

**Ask the outer:** (A) source the deployed `oh-adapter-runtime.jar` / `liboh_android_runtime.so`
`createClassloaderNamespace`-that-creates-a-ns (not in any repo here); (B) decide the JNI_OnLoad-idempotency approach
for copy A's bridge. With both, N11h-r2 is the one-file `dlns_inherit` + the chosen idempotency guard, then
`open_site_scan` static proof (owners no longer reach a second namespace) + a ≤30-min default-disabled 61b window
(base U10.1T8), as in `benchmark/2026-10-02-n11h-window`.

## Files
- `fix-spec.md` — the dlns_inherit design + call site + the idempotency requirement.
- `evidence/source-search.txt` — source located + missing-source proof.
- `evidence/jni-onload-state.txt` — the step-3 gating evidence (copy A bridge JNI_OnLoad ran; RegHook on copy B).
