# N3b default-owner namespace wall — root cause + fix draft (cc-t3, 2026-09-30)

**For cx-t0 / N4.** Offline analysis only — no build, no board. Root cause is confirmed from source + the
deployed U4 hilogs (the failing `dlerror()` text is captured verbatim, 11/11 apps). One-token primary fix.

## Symptom
11 apps fail with `java.lang.UnsatisfiedLinkError: Flutter default-owner namespace configuration failed: 2`
(often wrapped `RuntimeException → ExecutionException → …`). Fatal for 8, caught/downstream for 3 — see the
outcome table. This is the ONE wall U4/N3b newly introduced; it is native, not JAR.

## Where the message comes from (report site, unchanged N2→N3)
`bms/src/adapter/framework/app-native-loader/src/flutter_domain.inc:47`
```c
int rc = domain->runtime_gate.namespace_host_ops.create_configured_namespaces(…);
if (rc != 0) return failf("Flutter default-owner namespace configuration failed: %d", rc);
```
`create_configured_namespaces` is a **host op** (function pointer), not ANL code. `flutter_domain.inc` and
`app_native_loader.c` are **byte-identical N2→N3** (verified `git diff --no-index` on the
`bms-deploy/benchmark/2026-09-30-n{2,3}-native/` snapshots). So the ANL only *reports* rc; the wall is entirely
host-side.

## Root cause (host op, ADDED in N3)
Impl = `StockCreateConfiguredNamespaces` in
`bms/src/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/src/westlake_stock_host_main.c`.
`rc = 2 = ENOENT` (confirmed: `NamespaceResultFence()` is a pass-through volatile barrier, no remap; `EINVAL`
would be 22). N3 **added** a resident-runtime-publish block that N2 did not have (n3-native snapshot lines
277–289):
```c
if (needs_runtime) {
    /* NOLOAD prevents a duplicate runtime/constructor set when a declared owner edge is wrong. */
    void* resident = dlopen_ns(app_namespace,
        "/system/android/lib64/liboh_android_runtime.so",
        RTLD_NOW | RTLD_GLOBAL | RTLD_NOLOAD);          // ← the bug
    if (resident == NULL) {
        APPSPAWN_LOGE("[N3-OWNER] resident runtime unavailable: %{public}s", dlerror());
        return NamespaceResultFence(ENOENT);            // ← rc = 2
    }
    APPSPAWN_LOGI("[N3-OWNER] resident runtime published for %{public}s", app_name);
}
```
**Mechanism:** `RTLD_NOLOAD` returns a handle *only if the library is already mapped into this namespace's
local scope*, and never loads it otherwise. The two `dlns_inherit(app_namespace, …, "…liboh_android_runtime.so…")`
calls immediately above (from `default` and from `westlake.sealed.child`, lines 266–270) grant a **lazy
linkability edge** — the soname becomes resolvable on demand, but is **not eagerly mapped** into the freshly
created app namespace. So at namespace-creation time `RTLD_NOLOAD` always misses → `resident == NULL` →
`return ENOENT` → rc=2. The author's intent (get liboh_android_runtime.so into the app namespace's GLOBAL
symbol scope without constructing a second copy) is legitimate — OH 6.1 musl only globalizes symbols via a
`dlopen(RTLD_GLOBAL)`, not via inherit (the code says so itself at line ~309) — but `RTLD_NOLOAD` is the wrong
way to achieve it here.

### Proof (deployed U4 hilogs, verbatim)
All 11 target apps print exactly, once each (11/11 across `u4-sweep/runs`):
```
[N3-OWNER] resident runtime unavailable: Library /system/android/lib64/liboh_android_runtime.so is not already loaded
```
`is not already loaded` is the textbook `RTLD_NOLOAD`-miss `dlerror()` string — it is *not* a missing file or a
permission error. This nails the mechanism: the file exists and is loadable; NOLOAD simply refuses to load it.

### Smoking gun inside the same function
Three lines below (n3-native line ~317) the ABI lib is published with the **correct** pattern and works:
```c
void* handle = dlopen_ns(app_namespace, ".../libwestlake_native_abi.so", RTLD_NOW | RTLD_GLOBAL);  // no NOLOAD
… "[N2-OWNER] %s ABI global ready …"
```
The failing call is identical **except for the extra `RTLD_NOLOAD`**.

## Who hits it — `needs_runtime` list = exactly 11 (reconciles cx-bms "owner 配置 11")
`needs_runtime` = `flutter_private` (the 6 Flutter packages in `flutter_package_path`) **OR** an explicit 5-app
native `strstr` list. Native-cluster apps NOT in this sub-list (firefox, fennec, vlc, anki, unciv, nextcloud,
mindustry, shatteredpixeldungeon) run the inherit edges but **skip** the resident-publish, so they do NOT hit
this wall (they die on their own walls — consistent with C2/C5/C7 in DEATH-CLUSTERS.md).

| app | entry path | outcome in U4 |
|---|---|---|
| fd-fluffychat, fd-immich, fd-kitchenowl, fd-libre (aves.libre), fd-saber, localsend | `flutter_private` | **fatal** (namespace ENOENT is first fatal) |
| burgerking (com.emn8.mobilem8.nativeapp.bk), fd-im-vector-app (im.vector.app) | native strstr | **fatal** |
| mcdonalds, fd-organicmaps | native strstr | rc=2 at bind (caught by androidx.startup / logged), then **downstream app NPE** |
| ppsspp | native strstr | rc=2 **caught** (`LoadLibrary failed …`), app survives-degraded |

8 fatal + 2 downstream + 1 caught = 11. (im-vector also has a Sentry/realm wall behind this; mcdonalds/organicmaps
have their own NPEs behind it — so clearing this wall is necessary but not sufficient for those three.)

## Fix draft (source, NOT compiled)
File: `…/stock_child_plugin/src/westlake_stock_host_main.c`, `StockCreateConfiguredNamespaces`, the
`needs_runtime` block.

### Fix A — recommended, minimal: drop `RTLD_NOLOAD` (align with the ABI publish below)
```diff
         void* resident = dlopen_ns(app_namespace,
             "/system/android/lib64/liboh_android_runtime.so",
-            RTLD_NOW | RTLD_GLOBAL | RTLD_NOLOAD);
+            RTLD_NOW | RTLD_GLOBAL);
         if (resident == NULL) {
             APPSPAWN_LOGE("[N3-OWNER] resident runtime unavailable: %{public}s", dlerror());
             return NamespaceResultFence(ENOENT);
         }
```
liboh_android_runtime.so was just inherited from both `default` and `westlake.sealed.child`, so a real
`dlopen_ns` by absolute path binds to the resident copy via the inherit edge and promotes it to GLOBAL. This is
exactly what the `libwestlake_native_abi.so` publish 3 lines below already does successfully.

### Fix B — risk-averse variant: NOLOAD first, fall back to a real global open
Keeps the "no duplicate when already mapped" fast path; only does a real load when NOLOAD misses.
```diff
         void* resident = dlopen_ns(app_namespace,
             "/system/android/lib64/liboh_android_runtime.so",
             RTLD_NOW | RTLD_GLOBAL | RTLD_NOLOAD);
+        if (resident == NULL) {
+            /* Inherit is lazy: at ns-creation the soname is linkable but not yet
+             * mapped in the child ns, so NOLOAD misses. Bind it for real via the
+             * inherit edge (resolves to the resident owner copy, not a 2nd instance). */
+            resident = dlopen_ns(app_namespace,
+                "/system/android/lib64/liboh_android_runtime.so",
+                RTLD_NOW | RTLD_GLOBAL);
+        }
         if (resident == NULL) {
             APPSPAWN_LOGE("[N3-OWNER] resident runtime unavailable: %{public}s", dlerror());
             return NamespaceResultFence(ENOENT);
         }
```

### The one thing to verify on-board (the author's original fear)
Both fixes do a real `dlopen_ns(RTLD_GLOBAL)`. Confirm OH musl **deduplicates by realpath across the inherit
edge** and does NOT construct a second liboh_android_runtime instance (which would re-run its
constructors/DFX/runtime singletons → possible abort). Check after the fix:
- the `[N3-OWNER] resident runtime unavailable` line disappears for all 11;
- no second liboh_android_runtime constructor/DFX-init banner in the child hilog;
- the app proceeds past `create_configured_namespaces`.
If a duplicate DOES appear, the resident is already reachable through the inherit edges alone — then make the
`resident == NULL` branch **non-fatal** (log + continue) instead, accepting that global-scope runtime symbols
come only from inherit (test whether the app still resolves them).

## 2 representative verification apps (cleanest signal — die ONLY on this wall)
1. **fd-fluffychat** — `flutter_private` branch (Flutter engine; westlake_flutter prefix + package match). First
   and only fatal is this namespace ENOENT; nothing behind it. Fix works ⇒ `[N3-OWNER] unavailable` gone and it
   gets past namespace creation.
2. **burgerking** (`com.emn8.mobilem8.nativeapp.bk`) — native `strstr` branch, non-Flutter, also hard-fails
   cleanly here (uncaught = first fatal). Covers the second entry path into `needs_runtime`.

Avoid im-vector / mcdonalds / organicmaps as primary probes (downstream walls behind this one) and ppsspp
(catches rc=2, so "no crash" ≠ "lit").

## Files / evidence pointers
- Report site: `bms/.../app-native-loader/src/flutter_domain.inc:47`
- Root cause: `bms/.../appspawn-x/.../stock_child_plugin/src/westlake_stock_host_main.c` →
  `StockCreateConfiguredNamespaces` (needs_runtime block; n3-native snapshot lines 277–289, `RTLD_NOLOAD` at 283)
- N2→N3 delta: `git diff --no-index bms-deploy/benchmark/2026-09-30-n2-native/src/westlake_stock_host_main.c \
  bms-deploy/benchmark/2026-09-30-n3-native/src/westlake_stock_host_main.c` (the whole needs_runtime block is +added)
- dlerror proof: `grep -r "\[N3-OWNER\] resident runtime unavailable" bms-deploy/benchmark/2026-09-30-u4-sweep/runs`
  → 11 hits, `… is not already loaded`
