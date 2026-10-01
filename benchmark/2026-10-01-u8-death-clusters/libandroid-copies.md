# libandroid copies inventory (fid==null cluster)

Dispatch (ACK(90) 2026-10-01T16:51:20): inventory the libandroid.so copies in the U8 package, find which one N10b's asset-offsets-init.cpp fills, and which copies are left unfilled.

## Copies found (3)

| Path | sha256 | Domain dir | Domain | Exports AAssetManager_fromJava | Has gAssetManagerOffsets | Filled by N10b |
|---|---|---|---|---|---|---|
| `native/payload/android/lib64/libandroid.so` | `3ee198cdbf…` | `lib64` (default/native domain) | default | **yes** (T 0x7d9d8) | **yes** (B 0x8b9e0) | **yes** |
| `native/payload/android/lib64/westlake_flutter/libandroid.so` | `7f03685545…` | `westlake_flutter` | westlake_flutter | **no** | **no** | **no** |
| `native/payload/android/lib64/westlake_native/libandroid.so` | `627ce1258c…` | `westlake_native` | westlake_native | **no** | **no** | **no** |

## Namespace configuration

From `native/native-checks/namespace-manifest.json` (schema v1) and `native/native-checks/flutter_domain.inc` (sha256 `43c3247d…`):

| Domain | Library dirs | Search paths | Permitted paths | Shared from | Source evidence |
|---|---|---|---|---|---|
| `westlake_flutter` | `/system/android/lib64/westlake_flutter` | same | same | none | `flutter_domain.inc` (private_root_line:22, search_line:30, permitted_line:31) |
| `westlake_native` | `/system/android/lib64/westlake_native` | same | same | none | (not in namespace-manifest.json domains; only flutter listed) |
| default | `/system/android/lib64` | same | same | none | (implicit; not in namespace-manifest.json) |

`flutter_domain.inc` lists six package path components for flutter domain ownership: `chat.fluffy.fluffychat`, `app.alextran.immich`, `com.tombursch.kitchenowl`, `deckers.thibault.aves.libre`, `com.adilhanney.saber`, `org.localsend.localsend_app`.

## N10b asset-offsets-init.cpp target

Source: `benchmark/2026-10-01-n10b-child/src/asset-offsets-init.cpp` (master). It fills `native/payload/android/lib64/libandroid.so` (default/native domain) — the only copy with `gAssetManagerOffsets` and `AAssetManager_fromJava`.

**Unfilled copies:** `native/payload/android/lib64/westlake_flutter/libandroid.so` and `native/payload/android/lib64/westlake_native/libandroid.so` — both lack `gAssetManagerOffsets` and are not filled by N10b.

## Impact

The fid==null cluster (glmark2 / fluffychat / immich / saber) is in the `westlake_flutter` domain. Their `libandroid.so` copy has no `gAssetManagerOffsets` and is not filled by N10b. The fid==null wall (N10b-NDK-ASSET-OFFSETS) is only fixed for the default/native domain; flutter domain apps still hit fid==null.
