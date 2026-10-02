# N11h-r2 fix — CORRECTED: the copy-B source is `CREATE_INHERIT_DEFAULT`, not a missing inherit

## Correction to the proposed direction
The dispatch proposed "after the CL ns is created, add a `dlns_inherit` from `westlake.sealed.child`". That inherit is
**already present** in the N11h-r1 host (`candidate-stock-host.c:216`, marker 12494
`action=inherit target=westlake.anl.bridge.10303.1 owner=westlake.sealed.child shared=bridge:runtime rc=0`) and still
produced two copies. The fix is therefore **not** an added inherit; it is removing the OTHER edge that supplies the
owner libs.

## Root cause (evidence/root-cause-create-inherit-default.txt)
The N11h host creates the CL **bridge** namespace with `CREATE_INHERIT_DEFAULT` (0x1):
```c
// candidate-stock-host.c:196-197   (ANL_CreateDomain -> runtime_gate...create_configured_namespaces -> here)
dlns_create2(bridge_namespace, bridge_search_paths, CREATE_INHERIT_DEFAULT);   // inherits the DEFAULT namespace
...
dlns_inherit(bridge_namespace, &sealed_owner, N11H_OWNER_LIBS);                 // sealed edge, added AFTER
```
`CREATE_INHERIT_DEFAULT` makes the bridge ns inherit **default**, whose reach + the bridge search path
`/system/android/lib64` resolve `liboh_adapter_bridge.so` / `liboh_android_runtime.so` to a **fresh copy (copy B)** at
creation. The sealed.child inherit is added afterward and cannot collapse the already-established default edge. By
contrast the **app** ns (line 224) uses `LOCAL_NS_PREFERED` (0x4) — no default inherit. The app ns's flutter/native
branch additionally does `dlns_inherit(app, default, "…liboh_android_runtime.so…")`, a second copy-B source for the
AssetManager/flutter cluster.

## The fix (single logical change, in candidate-stock-host.c — the N11h host, NOT ANL / not runtime.so)
Stop `default` from supplying the two owner libs; make `westlake.sealed.child` their only source:
1. **bridge ns**: do not create with `CREATE_INHERIT_DEFAULT`. Use `LOCAL_NS_PREFERED` (like the app ns) plus an
   explicit `dlns_inherit(bridge, default, <BASE libs only>)` that lists libc/libdl/libm/libc++/liblog/libEGL/… but
   **excludes** `liboh_adapter_bridge.so` and `liboh_android_runtime.so`. The existing
   `dlns_inherit(bridge, sealed_owner, N11H_OWNER_LIBS)` (line 216) then becomes the sole source of the two owner libs
   → copy A only.
2. **app ns flutter/native branch**: remove `liboh_android_runtime.so` (and the bridge soname) from the default-inherit
   soname list; keep them only in the sealed.child inherit.

Each change its own file/patch, single variable (the owner-lib default edge), as the dispatch required.

## Still required — the JNI_OnLoad guard (precondition B, unchanged)
Once the owner libs resolve to copy A only, the CL-side `System.loadLibrary` lands on copy A. ART
`JavaVMExt::LoadNativeLibrary` keys `libraries_` by path; copy A was dlopen'd natively (host/child), not via ART, so
ART would call `JNI_OnLoad` on copy A. **Copy A's bridge already ran `JNI_OnLoad` once** (hilog 12254, early, INCOMPLETE
— `FindClass(AppSpawnXInit) returned null`). Guard requirements (`evidence/jni-onload-state.txt`):
- one-time init guarded by a once-flag that is set **only on complete success** (not on the early incomplete entry, or
  it locks in a half-init that registered 0 entries);
- the `RegisterNatives` section may re-run (ART tolerates duplicate same-class registration);
- confirm whether runtime's RegHook is driven by the bridge `JNI_OnLoad` delegating, or runtime is itself
  `System.loadLibrary`'d (if the latter, runtime needs the same guard).

## Static proof + build (for whoever owns the host build — cx-bms lineage)
`open_site_scan.py --owners liboh_adapter_bridge.so liboh_android_runtime.so` on the patched host/ANL outputs must show
the owner libs no longer reach the default namespace (only the sealed inherit edge). Then `n11h_readout.py` on a window
must show single-owner PASS (bridge=1, runtime=1) with no double `JNI_OnLoad`. Build log tee'd + byte-identical ×2 +
default-disabled ≤30-min 61b window (base U10.1T8).

## Who implements
The change is in `candidate-stock-host.c` (the route-A N11h host) — the cx-bms lineage that authored N11h-r1, built on
hw248's frozen toolchain. cc-wiki located the root cause + the exact edit; the host rebuild + window should be
coordinated with cx-bms / the outer rather than rebuilt blindly here.
