# N11h refuted — who opens the second bridge/runtime copy

Offline forensics. The N11h 61b window (18:27–18:57, root
`$WORKSPACES/westlake-harness-u7-executor/benchmark/2026-10-02-n11h-window/n11h-61b-20261002T182700/61b/`) was
**refuted**: the host owner markers all fired (`[N11h-HOST-OWNER] action=inherit … owner=westlake.sealed.child rc=0`),
but the helloworld child still maps `liboh_adapter_bridge.so` and `liboh_android_runtime.so` at **two r-xp load-bases
each** — single-owner not achieved; 61b reverted to U10.1T8. This pins **which opener makes the second copy**, so the
next attempt is a targeted fix, not another board round.

## The two copies (helloworld PID 10303, maps-t5; `evidence/hilog-evidence.txt`)
| lib | copy A (base) | copy B (base) | inode |
|---|---|---|---|
| liboh_adapter_bridge.so | `7eec078000` | `7efa9f8000` | 467241 |
| liboh_android_runtime.so | `7ed6a2d000` | `7eebded000` | 463980 |

Same inode, two independent r-xp bases = two loads of the same file. **Copy B is the one the Java/runtime side uses**:
the OH_RegHook JNI registrations resolve into `7EEBF…` (runtime B) and `[OH_IIMAdapter] nativeBridge=0x7efaae…` is in
bridge B. Copy A sits in the vendor-HAL address cluster (appspawn/host side); copy B sits with the Android system libs
(libicuuc/libandroidfw) and the route-a provider libs (app/runtime-CL side).

## Who opens each — static (`open_site_scan.py`) + runtime (hilog) agree
**Copy A = the sealed owner.** `open_site_scan --u9` (`evidence/u9-open-sites.json`):
`libwestlake_android_child.z.so:RealOpenLocalNow@0x41c8 dlopen_ns ns=global:closure_namespace
path=/system/android/lib64/liboh_android_runtime.so` (and `@0x419c` for the bridge). `closure_namespace` holds
`westlake.sealed.child`. The N11h host then inherits this owner into the configured namespaces — hilog shows
`[N11h-HOST-OWNER] action=inherit target=westlake.anl.bridge.10303.1 / westlake.anl.app.10303.1
owner=westlake.sealed.child shared=liboh_adapter_bridge.so:liboh_android_runtime.so rc=0` (and the appspawn-x
`StockCreateConfiguredNamespaces@0xccf0 dlns_inherit parent=westlake.sealed.child
shared=liboh_android_runtime.so:…`). So the configured bridge/app namespaces DO share copy A. That part works.

**Copy B = the B8 runtime-CL native namespace — never linked to the sealed owner.** hilog:
`[B8-NATIVE] native namespace created for runtime CL (search=/system/android/lib64:/system/lib64/platformsdk:…)` then
`[B8-NATIVE] loaded …/libwestlake_jni_gapfill.so`, `…/liboh_tls_boundary.so`. This is the Android per-ClassLoader
native-library namespace (`ClassLoaderFactory::createClassloaderNamespace` → libnativeloader), created Java-side by
AppSpawnXJava — a SEPARATE namespace from `closure_namespace`/sealed.child and from the host's configured
bridge/app namespaces. It has its own search path `/system/android/lib64`, so when its libraries resolve
bridge/runtime they load a fresh copy into it. `open_site_scan` on the bridge confirms the in-namespace pull:
`liboh_adapter_bridge.so:nativeRegisterInputChannel_impl@0xd554c dlopen path=liboh_android_runtime.so DEFAULT-NS`
(caller-default → whatever namespace the bridge sits in, i.e. the CL namespace). `open_site_scan` finds `runtime` is
**MULTI-NS confirmed**: appspawn-x configured ns (`@0xcd70`) + child `closure_namespace` (`@0x41c8`) — two namespaces,
two copies; the CL namespace is a third surface the host owner never reaches.

Corroborating: `MUSL-LDSO: load liboh_android_runtime.so failed, namespace=westlake.sealed.child, errno=2` — the sealed
namespace is inherit-only (NOLOAD); a consumer that is NOT linked to it (the CL namespace) cannot borrow its copy and
loads its own.

## Control — U10.1T8 window5, same keys: identical origins (N11h changed nothing here)
`n11h_readout.py --selftest` over window5 (U10.1): **24 keys, all N11h-marker-free, all bridge double (==2)**. A window5
key shows `[B8-NATIVE] native namespace created` = 1, `[U10-COMPAT-VISIBLE]` = 2, `[N11h-HOST-OWNER/OPEN]` = 0,
bridge=2, runtime=2 — i.e. **the two copies and the B8 CL namespace are exactly as in N11h**. The only N11h delta is
+8 `[N11h-HOST-OWNER]` markers (host ran) with **zero effect on the copy count**. The second copy's origin is the same
before and after N11h.

The readout tool on the N11h window captures the refutation in one line each
(`evidence/n11h-window-readout.json`): `helloworld`/`zigzag` → `single_owner=FAIL br=2 rt=2 inherit_rc0=1 OWNER=8`.

## Conclusion + minimal fix (static-first; board only after)
N11h unified the sealed owner across the host's **configured** bridge/app namespaces, but the **B8 runtime-CL native
namespace** (the Android per-ClassLoader namespace created by `createClassloaderNamespace`/libnativeloader, Java-side)
is never linked to `westlake.sealed.child`, so it loads copy B. That is the entire second copy.

**Minimal fix (one open/namespace site):** at the B8 runtime-CL namespace creation, add a
`dlns_inherit` from `westlake.sealed.child` sharing `liboh_adapter_bridge.so:liboh_android_runtime.so` — exactly what
`StockCreateConfiguredNamespaces@0xccf0` already does for the configured namespaces. Concretely that means the
westlake B8 native-namespace step (the `[B8-NATIVE] native namespace created for runtime CL` path in AppSpawnXJava /
the libnativeloader `createClassloaderNamespace` adapter) must link the sealed owner for the two owner libs, so the CL
namespace resolves bridge/runtime to copy A instead of mapping copy B. No host-marker change is needed (the host side
already works); the fix is on the CL-namespace creation, not the appspawn configured-namespace path N11h touched.
Prove statically with `open_site_scan` on the patched builder (owner must no longer reach a second namespace), then a
board window.

## Rule set this time
A refuted single-owner window with **all host markers green** means the owner was unified only in the namespaces the
host creates — enumerate EVERY namespace that opens the owner lib (`open_site_scan --owners`), not just the host's. The
Android per-ClassLoader native namespace (libnativeloader) is a separate owner surface from the appspawn configured
namespaces and the child closure namespace; a single-owner change must cover it too.

## Files
- `scripts/lab/n11h_readout.py` — per-key window readout (load-bases, the three host markers split out, AssetManager
  GetLongField/JniAbort, first fatal); `--selftest` = window5 known-answer (N11h-marker-free + bridge double).
- `evidence/hilog-evidence.txt`, `evidence/n11h-window-readout.json`, `evidence/u9-open-sites.json`,
  `evidence/nativeloader-open-sites.json`.
