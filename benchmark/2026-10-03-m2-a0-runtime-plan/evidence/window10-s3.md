# Window 10 S3 analysis: the `nweb_ns` name cleared the permission wall; the engine load failed only because the probe pre-created `nweb_ns` with the wrong `lib_path`

Window 10 (5cd, 2026-10-03 11:31:28, U13 `821de739cf81/124`, clean rollback + UNLOCK). The window-10 entry created
`nweb_ns` with `lib_path=/data/local/tmp` only; it cleared the permission wall and reached deep into OH's NWeb stack,
failing only at the engine load. The window-11 fix (entry a352a36f, both dirs in `nweb_ns` `lib_path`) is below.

## ① Full S3 log (probe pid 12103, hilog `C04500/webview` + `WL-A0`)

```
[A0] entry ns nweb_ns (lib_paths=/data/local/tmp): dlns_get(nweb_ns)=126 create=0 dlns_get(default)=0 inherit=0
[A0] entry: worker a0_probe_start rc=0
[A0] S0 … mainEventRunner=0x… existingAppContext=0
[A0] S1 NWebHelper::Instance at 0x… in /system/lib64/platformsdk/libarkweb_core_loader.z.so
[A0] S2 attached ApplicationContext … baseDir=/data/storage/el2/base bundleName=org.westlake.a0probe
C04500/webview Init: [webview]: init load resources bundle path /data/storage/el1/bundle/arkwebcore
C04500/webview GetArkwebLibPath: get arkweb lib path: /data/storage/el1/bundle/arkwebcore/libs/arm64
C04500/webview GetArkwebNameSpace: get arkweb name space: nweb_ns
C04500/webview ArkWebBridgeHelperLoadLibFile: dlns_create failed for '/data/storage/el1/bundle/arkwebcore/libs/arm64': errno=17   <-- EEXIST
MUSL-LDSO load libarkweb_engine.so failed, namespace=default no inherits, errno=2
MUSL-LDSO load libarkweb_engine.so failed, namespace=ndk no inherits, errno=2
MUSL-LDSO load libarkweb_engine.so failed, namespace=nweb_ns, errno=2
C04500/webview ArkWebBridgeHelperLoadLibFile: failed to load lib file …/arkwebcore/libs/arm64/libarkweb_engine.so
C04500/webview GetWebEngine: failed to init arkweb nweb bridge helper
[A0] S3 … Init(1) -> 0
[A0] RESULT FAIL stage=S3
```

**Return codes:** permission gate passed (`dlns_get(nweb_ns)=126` ENOKEY → `dlns_create=0`, `inherit=0`). S0/S1/S2 all
OK. The only error is at the engine load: OH's `ArkWebBridgeHelperLoadLibFile` got **errno 17 (EEXIST)** on
`dlns_create(nweb_ns, /data/storage/el1/bundle/arkwebcore/libs/arm64)`, then its `dlopen_ns(nweb_ns, libarkweb_engine.so)`
searched the **already-existing** `nweb_ns` — the one the probe created with `lib_path=/data/local/tmp` — so
`libarkweb_engine.so` (which is in `…/arkwebcore/libs/arm64`) was `errno 2 (ENOENT)`.

## ② Static checks (outer's request)

- **The arkwebcore mount is unconditional.** `appdata-sandbox.json` (deployed `…/payload/runtime/appdata-sandbox.json`;
  OH source `base/startup/appspawn/appdata-sandbox.json`) mounts `src /data/app/el1/bundle/public/<arkWebPackageName>` →
  `sandbox /data/storage/el1/bundle/arkwebcore` with `["bind","rec"]`, `check-action-status:false`, in the **common**
  (every-app) section — not gated by the app declaring web. So our test bundle's sandbox has it, and window 10 confirms
  it live: OH's `GetArkwebLibPath` returned that path and tried to load from it. The engine (`libarkweb_engine.so`,
  185 MB) is present there (roadmap evidence; same mount serves every bundle).
- **SetBundlePath / Init / LoadWebEngine, vs OH's own sequence** (`base/web/webview/ohos_nweb/src/nweb_helper.cpp`,
  `arkweb_utils/arkweb_utils.cpp`):
  - `NWebHelper::SetBundlePath("/data/storage/el1/bundle/arkwebcore")` — correct (matches `GetBundleCodeDir` for the
    arkweb package).
  - `Init(fromArk=true)` → `LoadWebEngine(true,false)` → `GetWebEngine(true)` → `GetArkwebLibPath()` =
    `/data/storage/el1/bundle/arkwebcore/libs/arm64`; `ArkWebNWebWebviewBridgeHelper::Init(true, bundlePath)` →
    `ArkWebBridgeHelperSharedInit(runMode=true)` → `ArkWebBridgeHelperLoadLibFile(nweb_ns, that dir, libarkweb_engine.so)`
    (`dlns_init` + `dlns_create(nweb_ns, dir)` + `dlns_get("ndk")` + `dlns_inherit(ndk, allow_all)` + `dlopen_ns`).
  - **The one divergence:** OH expects to *create* `nweb_ns` itself, with the arkwebcore dir as its `lib_path` and
    inheriting **ndk**. The probe had already created `nweb_ns` (for the worker) with `lib_path=/data/local/tmp` and
    inheriting **default**. OH's create then EEXISTs onto the probe's `nweb_ns`, whose `lib_path` has no engine.

## Fix for window 11 (chosen, built a352a36f): co-own `nweb_ns` with both dirs in `lib_path`

The probe keeps creating `nweb_ns` (the permitted target name that cleared window 9's wall) but its `lib_path` now holds
**both** `/data/local/tmp` (the worker) **and** `/data/storage/el1/bundle/arkwebcore/libs/arm64` (the engine), inheriting
`default`:

```
NS_LIB_PATH = "/data/local/tmp:/data/storage/el1/bundle/arkwebcore/libs/arm64"
```

Why this resolves S3, traced against OH's own `ArkWebBridgeHelperLoadLibFile` on the *existing* `nweb_ns`:
- the probe's worker (+ `libarkweb_core_loader`, reached via inherited `default` → platformsdk, confirmed by window-10
  S1) and its 14-lib `/system/lib64`+`ndk` closure resolve through `inherit default`;
- OH's `dlns_create(nweb_ns, arkwebcore dir)` still `EEXIST`s (non-fatal — OH logs and continues), **but** OH then runs
  its own `dlns_get("ndk")` + `dlns_inherit(nweb_ns, ndk, allow_all)` on that existing ns (so OH's intended ndk
  inheritance is still applied — my `inherit default` ⊇ ndk, and OH adds ndk explicitly on top), and its
  `dlopen_ns(nweb_ns, libarkweb_engine.so)` now searches a `nweb_ns` whose `lib_path` **includes the arkwebcore dir** →
  the engine is found (the `errno 2` becomes a hit).

So the one thing window 10 was missing — the arkwebcore dir in the shared `nweb_ns` `lib_path` — is supplied, and OH's
subsequent inherit/open steps still run on the same namespace. No frozen file changes; the entry stays a window-only
bind-mount, rolled back after the window. Entry a352a36f is built ×2 byte-identical and pinned in `run_a0.sh`
(`RT_PROBE_SHA`); worker faad4897 unchanged.

**Cleaner alternative, kept as fallback (not rebuilt now):** name the *worker's* namespace `nweb_ns_legacy` (also a
permitted target, dynlink.c:4189) and leave `nweb_ns` entirely to OH to create fresh with the arkwebcore dir. That avoids
co-owning OH's namespace, but the board runs the evergreen engine (`GetArkwebNameSpace: nweb_ns`), so legacy is untouched
and co-owning `nweb_ns` is safe here; it isn't worth a rebuild round. If window 11's co-owned `nweb_ns` hits an
unforeseen OH expectation on that namespace, rebuild to `nweb_ns_legacy`.

For route a proper this is moot: the WebViewProvider calls `NWebHelper`, which owns `nweb_ns` itself; route a only has to
reach `libarkweb_core_loader` and call in.
