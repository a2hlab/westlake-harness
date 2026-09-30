# dlopen_ns 4-app attribution: JAR classloader→namespace vs native-loader (2026-09-30)

**One line:** the four "dlopen_ns" apps are **not** a runtime-JAR classloader→namespace fix that cc-t3 owns
today. Three fail because a system/NDK dependency their own `.so` needs is unreachable from the app's linker
namespace — and that namespace's search+permitted paths are built in **native-loader-oh / appspawn-x
(native)**, not in `oh-adapter-runtime.jar`. The fourth is a native relocation error. Route the
dlopen/namespace half to **cx-t0**.

## What the earlier cluster guess said, and what the raw evidence corrects

`benchmark/2026-09-30-r17p-deadapp-clusters` tagged these `native (dlopen_ns app native libs)` — correct
direction, but two corrections the raw logs force (FLAW-008: read the first-fatal, don't infer from the
cluster label):

1. **fd-client is not a dlopen wall.** Its activity crash is an **app-internal DI NPE** (`accountManager`
   null in `SessionMixin.<init>`), same family as fd-reader. The conscrypt/liblog dlopen is a separate,
   earlier line. Fixing the dlopen would not light it.
2. **fd-im-vector is a symbol/relocation error**, not "library not found" — a path change cannot help it.

## The raw dlopen lines (61b r17p sweep, `<app>/hilog.txt`)

| app | app's own `.so` (installed+verified) | missing dep (raw) | dep exists on board at |
|---|---|---|---|
| fd-app (unciv) | `libgdx.so` | `Error loading shared library libstdc++.so: (needed by …/libgdx.so)` | `/system/android/lib64/libstdc++.so` |
| mindustry | `libarc.so` | `Error loading shared library libOpenSLES.so: (needed by …/libarc.so)` | `/system/lib64/libOpenSLES.so` |
| fd-client (nextcloud) | `libconscrypt_jni.so` | `Error loading shared library liblog.so: (needed by …/libconscrypt_jni.so)` | `/system/android/lib64/liblog.so` (and *is* a shared soname) |
| fd-im-vector (element) | `librealm-jni.so` | `F02-A12-UNSUPPORTED-SYMBOL` (relocation, not "not found") | n/a |

**Every dep exists on the image.** The failure is reachability, not absence.

## Why the deps are unreachable — and who owns the paths

App namespace search path (observed): `/system/android/lib64:/system/lib64/platformsdk:/system/lib64/chipset-sdk:/system/lib64/chipset-sdk-sp`.
Native policy (`native-loader-oh/include/nativeloader/native_bridge_policy.h`):
`kBridgeSearchPaths = {/system/android/lib64, /system/lib64/platformsdk}`, `kBridgeSharedSonames = {libandroid, libEGL, liblog, …}` (6).

- **mindustry / libOpenSLES.so** — lives in `/system/lib64`, which is in **neither** the app paths **nor**
  the bridge paths, and is not a shared soname → unreachable.
- **fd-app / libstdc++.so** — lives in `/system/android/lib64` (bridge-searchable) but is **not** a shared
  soname → the bridge won't expose it to the app namespace.
- **fd-client / liblog.so** — bridge-searchable **and** a shared soname, yet still "not found" → a
  namespace-**link** gap, deeper in native-loader-oh.

### The decisive source fact (the JAR-vs-native discriminator)

`native-loader-oh/src/native_loader.cpp` `BuildAppConfig` (lines 64–90) reads the app's **`library_path`
and `permitted_path` as JStrings passed from Java** and splits them into `app_search_paths` /
`app_permitted_paths`; only `bridge_*` come from the C++ policy. So the app paths *are* Java-supplied — the
JAR-angle is plausible **in principle**.

But grepping the runtime-JAR Java sources (`bms/src/adapter/framework/*/java`) for anyone that builds that
`library_path`/`permitted_path` string returns **only `B7BindFixes.java` — and that is
`createNativeNamespace` for the *runtime* classloader (the WESTLAKE `.so` namespace), not the app's.** No
class in `oh-adapter-runtime.jar` assembles the **app's** paths; that string is produced by
native-loader-oh / appspawn-x. Corroboration: fd-client also logs
`UnsatisfiedLinkError: path is outside app domain: /system/android/lib64/libwestlake_html_compat.so` — a
**permitted-paths rejection**, enforced natively.

## Verdict

**Route to cx-t0 (native-loader-oh).** None of the four is a JAR fix cc-t3 owns today:
- fd-app / mindustry: missing soname/searchpath governed by the native `kBridge*` policy + native-built app
  paths.
- fd-client: dlopen half is a native namespace-link gap; the **lit-blocker** is an app-internal
  `accountManager` NPE (parked with the fd-reader / DI-null family).
- fd-im-vector: native ABI/relocation.

## The one JAR experiment worth a shot (hypothesis, not an attribution — FLAW-008)

If a JAR angle is pursued, the single discriminating test: from the runtime JAR, reflectively **append
`/system/lib64:/system/android/lib64` to the app `library_path` *and* `permitted_path`** just before the
native `createClassloaderNamespace` call (intercepting `ApplicationLoaders`/`LoadedApk`). Re-run
**mindustry** (libOpenSLES in `/system/lib64`) and **fd-app** (libstdc++ in `/system/android/lib64`).
- deps load → a JAR increment is viable after all;
- still `path is outside app domain` / `not found` → the path is native-built → cx-t0.

## Files

- `dlopen-ns.json` — machine-readable table (per app: `.so`, missing dep, dep location, why, layer).
- Source runs: `benchmark/2026-09-30-r17p-{5ea,61b}-sweep/runs/.../{fd-app,fd-client,fd-im-vector-app,mindustry}/hilog.txt`.
