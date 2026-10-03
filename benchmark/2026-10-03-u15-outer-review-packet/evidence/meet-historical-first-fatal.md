 two-stage scope failure, not an unpacking-denial wall

PID **28539**, main TID28563, background create-react-context TID28583. Public verified SHAs: libc++ `3e852764`, Hermes `ebf7bc5c`, React Native `f5e13c08`.

```text
25374: relocating failed: symbol not found. dso=/data/app/el1/bundle/public/org.jitsi.meet/android/lib/arm64-v8a/libhermes.so s=__register_atfork use_vna_hash=1 van_hash=50d63
25376: relocating failed: symbol not found. dso=/data/app/el1/bundle/public/org.jitsi.meet/android/lib/arm64-v8a/libreactnative.so s=__register_atfork use_vna_hash=1 van_hash=50d63
25477: Reunpacking BackupSoSources ... libreactnative.so: __register_atfork: symbol not found ...
25483: extracting DSO libc++_shared.so
25507: relocating failed: symbol not found. dso=/data/app/el2/100/base/org.jitsi.meet/lib-main/libc++_shared.so s=android_set_abort_message use_vna_hash=1 van_hash=50d63
25527: [CHILD_CK] J_invokeStaticMain_main_threw: com.facebook.soloader.B: java.lang.UnsatisfiedLinkError: F02-A12-UNSUPPORTED-SYMBOL: dlopen_ns failed for /data/app/el2/100/base/org.jitsi.meet/lib-main/libc++_shared.so: Error relocating /data/app/el2/100/base/org.jitsi.meet/lib-main/libc++_shared.so: android_set_abort_message: symbol not found
```

SoLoader logs a warning about removing write permission, but then extracts and reaches the native linker. **Permission-only repair moves 0**: both public and fallback paths fail at symbol relocation, not an EACCES open. The later background `[B8-UEH] process kept alive` log cannot erase the main terminal.

| Required symbol | Actual deployed providers | Why not a global missing-export diagnosis |
|---|---|---|
| `android_set_abort_message@LIBC` | compat015aa, unversioned GLOBAL; ABI/libc/log/pthread-bridge have LIBC providers | Same-PID `owner_verified` queries precede failure; handle visibility is not consumer relocation scope |
| `__register_atfork@LIBC` | pthread bridge and private ABI d205 export `__register_atfork@@LIBC` | Compat015aa omits it, factory fd3c omits it, but the deployed provider inventory does not |

`selected-provider-facts.json` and the original `-V`/dynsym output show versions. `van_hash=0x50d63` is LIBC. Do not declare version mismatch: matching LIBC atfork providers exist, and the previously audited fd3c behavior accepts unversioned providers with absent version tables. Reference source is not claimed to reproduce fd3c.

Static route: receipt-selected ANL eebd's `native_cluster_path:63-67` **does not include org.jitsi.meet**. Its `ANL_Dlopen:450-473` passes the ordinary app namespace, unlike Element/Mindustry's selected private branch. The log prints B8 runtime-CL namespace creation, **not the numerical namespace of these SoLoader calls**; do not invent `app.28539.N` or equate it to that B8 namespace. ANL's opens and namespace construction are callback-indirect, so `open_site_scan` has zero direct sites/edges for ANL; source plus disassembly supplies this limitation, not proof of no operations.

Host r3 scanner retains **8 opens, 17 namespace edges, 0 INHERIT-REPEAT, 4 old INHERIT-AFTER-OPEN may-path findings**. The ordinary app already has a compat edge at `cffc`; adding its name again is not the missing remedy. Coordinate the N11h/Gecko common constructor and arrange the **existing unique compat and atfork owner in the consumer's actual saved relocation scope before app relocation**, then verify selected addresses on both public and fallback paths. Preserve once-only inheritance. Do not blindly whitelist Meet into the private old-runtime route: React Native imports six AAsset operations and can expose the known duplicated AssetManager/runtime owner problem.

Conditional complete scope repair moves **1 key**, not one per failed symbol/retry/thread. Abort-only visibility leaves the preceding atfork recovery root; exact next fatal after both owners are accessible is unknown. No export/route candidate is produced here.

The scope diagnosis is the leading explanation from the route and matching-version inventory, **not a captured selected-owner/GOT oracle**. `results.json` marks that evidence boundary explicitly. The old r3 `owner_verified` log is not promoted to a successful consumer relocation proof.

