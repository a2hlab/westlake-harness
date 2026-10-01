# N11f patch — branch=3 OWNER_MISMATCH (bridge second copy in `default`)

**N11e verdict (board 22:15):** `branch=3 WLSCPL_FAILB_OWNER_MISMATCH`, `index=0` (`liboh_adapter_bridge.so`). The
`detail` quoting `libartbased` is a **stale dlerror** (the `N11eFailure` bug, fixed below). Decision-table **row 3**.

## Root cause (pinned in the N11e source)
`benchmark/2026-10-01-n11e-result-channel/src/sealed_child_provider_loader.c`:
- The host open callback **`WLSCPL_OpenPreparedNamespace`** (`:263`) ends in a plain **`dlopen(absolute_path, flags)`** —
  a **default-namespace** load. When the Java NativeLoader opens `liboh_adapter_bridge.so` in `default`, this mints a
  **fresh second copy** of the bridge.
- The loader then tries to publish the sealed owners into `default` by `dlns_inherit` (`:347`) and verify by
  `dlopen_ns(default, …, RTLD_NOLOAD)` (`:357`). The NOLOAD check **finds a handle** (the fresh copy) but it is
  `!= jni_owner_handles[0]` (the sealed copy) → `OWNER_MISMATCH` (`:358`). Two bridge copies = the exact U7 double-load.

So the publish-by-inherit is the wrong lever: the fix is to stop `default` ever minting its own copy — intercept the two
canonical owner paths in `WLSCPL_OpenPreparedNamespace` and **return the resident sealed handle**
(`n11-single-owner`, master `c2508ebdd`: "intercept only these two canonical names/paths in the host open callback and
return their resident sealed-owner handles"; OH6.1 musl `dynlink.c:2408-2575` direct-inherited resident objects /
inode reuse before a new map).

## Changes (all in `sealed_child_provider_loader.c`; host plugin + manifest unchanged)

### 1. Promote the owner handles/paths to file-static (so the callback can read them)
They are currently function-static inside `RealOpenLocalNow` (`:311-315`). Move them to file scope next to
`closure_namespace` (`:260`):
```c
static Dl_namespace closure_namespace;
static int namespace_prepared;
/* N11f: the two canonical JNI owners, resident in closure_namespace, shared to
 * the default namespace by the open callback below (NOT by dlns_inherit). */
static void *g_owner_handles[2];
static const char *const g_owner_paths[2] = {
    "/system/android/lib64/liboh_adapter_bridge.so",
    "/system/android/lib64/liboh_android_runtime.so"
};
```
and delete the `static void *jni_owner_handles[2];` + the local `owner_paths[]` at `:311-315`, renaming uses in the
provider branch to `g_owner_handles` / `g_owner_paths`.

### 2. `WLSCPL_OpenPreparedNamespace`: return the resident sealed handle for the two owners
```c
void *WLSCPL_OpenPreparedNamespace(const char *absolute_path, int flags)
{
    static const char prefix[] = "/system/android/lib64/";
    if (namespace_prepared != 1 || !AbsoluteCanonicalForm(absolute_path) ||
        strncmp(absolute_path, prefix, sizeof(prefix) - 1U) != 0 ||
        absolute_path[sizeof(prefix) - 1U] == '\0' ||
        (flags & (RTLD_NOW | RTLD_GLOBAL)) != RTLD_NOW) return NULL;
    /* N11f: the Java NativeLoader opens the two JNI owners in the default
     * namespace. Return the resident sealed-owner handle instead of dlopen'ing
     * a second copy (the branch-3 OWNER_MISMATCH root). Single copy by
     * construction; no dlns_inherit. */
    for (size_t owner = 0U; owner < 2U; ++owner) {
        if (strcmp(absolute_path, g_owner_paths[owner]) == 0) {
            if (g_owner_handles[owner] != NULL) return g_owner_handles[owner];
            break;  /* not published yet: fall through (ordering note below) */
        }
    }
    return dlopen(absolute_path, flags);
}
```
**Ordering note:** the provider (`libwestlake_android_runtime_provider.so`) loads the two owners into `closure_namespace`
*before* provider init, and the Java NativeLoader resolves the owners *after* that (n11-single-owner design). So
`g_owner_handles` is populated before this callback is asked for them. If a future trace shows `default` asking first
(handle still NULL → falls through to `dlopen` = a second copy), publish the owners from the host **before** provider
init instead; flagged, not expected.

### 3. Delete the `dlns_inherit` + NOLOAD-verify block (`:340-371`)
Remove the entire `Dl_namespace default_namespace; dlns_init(..., "default"); … dlns_inherit(…) … for(owner…){ dlopen_ns(default, NOLOAD); verify } …` block. Publication is now the callback's job; the loader only has to load the owners
into `closure_namespace` (the `:323-337` loop, kept) and record stage. Keep `g_n11e_failure.stage` updates
(`BEFORE_INHERIT`→ now `AFTER_OWNER_PUBLISH`) so the entry/fail channel still reports progress.

### 4. Make the `:373` smoke-emit **non-fatal** (so the fixed load can complete)
After branch 3 is fixed the load reaches `:373` `dlsym(g_owner_handles[1],"HiLogPrint")`; `bridge`/`runtime` may not
resolve `HiLogPrint`, which would re-abort as branch 4 and **prevent the single-copy maps the window is meant to show**.
Record it but do **not** `return NULL` (decision-table row 4, folded in because the row-3 success criterion
*"maps = 1 each"* requires the load to complete):
```c
    N10bLogFn emit = (N10bLogFn)dlsym(g_owner_handles[1], "HiLogPrint");
    if (emit == NULL) {
        N11eFailure(WLSCPL_FAILB_EMIT_RESOLVE, 1U, NULL, "HiLogPrint resolution failed");
        /* N11f: diagnostic only — DO NOT abort the load (was: dlclose+return NULL). */
    } else {
        (void)emit(3,4,0xD000F00u,"N10bOwner","[N10b-JNI-OWNER] bridge/runtime preloaded in westlake.sealed.child");
        (void)emit(3,4,0xD000F00u,"N11bOwner","[N11f-OWNER] default shares sealed bridge/runtime via open callback");
    }
```
The N11e result-struct channel (`result->fail_*`, `:418`) and the host-side `[N11e-PROBE] entry`/`fail` logging
(`westlake_android_child_plugin.c`) are **unchanged** — N11f still reports.

### 5. `N11eFailure`: capture `dlerror()` at the failing call, not at record-time (the stale-text bug)
`N11eFailure` currently calls `dlerror()` itself (`:54`), which latches whatever the *last* dl* call left — that is why
R3 reported `libartbased` (an earlier, unrelated probe's error) instead of the branch's own. Pass the detail captured
immediately at the failing call:
```c
static void N11eFailure(uint32_t branch, uint32_t index, const char *detail_now, const char *fallback)
{
    const char *detail = detail_now ? detail_now : fallback;
    g_n11e_failure.branch = branch;
    g_n11e_failure.index  = index;
    g_n11e_failure.error  = errno;                 /* caller captures errno-relevant sites too */
    if (detail == NULL) detail = "no linker detail";
    size_t length = strlen(detail);
    if (length >= sizeof(g_n11e_failure.detail)) length = sizeof(g_n11e_failure.detail) - 1U;
    memcpy(g_n11e_failure.detail, detail, length);
    g_n11e_failure.detail[length] = '\0';
}
```
At each remaining failure site capture `dlerror()` into a local **on the line after** the failing dl* call and pass it:
```c
    const char *dl;
    art = dlopen_ns(&closure_namespace, "libart.so", RTLD_NOW|RTLD_NOLOAD|RTLD_LOCAL);
    dl = dlerror();                                                   /* immediately */
    if (art == NULL) { N11eFailure(WLSCPL_FAILB_ARTIFACT_DLOPEN, UINT32_MAX, dl, "route-a ART NOLOAD failed"); … }
    …
    g_owner_handles[owner] = dlopen_ns(&closure_namespace, g_owner_paths[owner], RTLD_NOW|RTLD_LOCAL);
    dl = dlerror();                                                   /* immediately */
    if (g_owner_handles[owner] == NULL) { N11eFailure(WLSCPL_FAILB_ARTIFACT_DLOPEN, (uint32_t)owner, dl, "JNI owner preload failed"); … }
```
Clear the latched error with a `(void)dlerror();` before each dl* call whose result you will check, so the capture is
that call's own error. (Same change in the manifest-artifact failure at `:532`.)

## Expected result (the window's pass criteria)
- Board maps for the app process show **exactly one** mapping each (same inode, one load base) for: `libart.so`,
  `libopenjdkjvm.so`, `liboh_adapter_bridge.so`, `liboh_android_runtime.so` — the N11 single-owner oracle
  (master `c2508ebdd`), ART/JVM already single; bridge and runtime now single (was 2+2).
- No `[N11e-PROBE] fail branch=3` (OWNER_MISMATCH gone). `[N11e-PROBE] entry` still present (entry-survival).
- If anything still fails, the result struct + host `[N11e-PROBE] fail …` reports it with a **fresh** dlerror (not
  `libartbased`). Branch 4 can no longer abort (now non-fatal) — if `HiLogPrint` doesn't resolve it is recorded, not
  fatal.
- `abi_diff --calls` and DT_NEEDED on the rebuilt `libwestlake_android_child.z.so` unchanged except the removed
  `dlns_inherit` call edge; `check_frozen` 0 violations; controls (helloworld hard, zigzag advisory) lit;
  `before_unlock` restores U9 (`boot 4db882a81732`, board runtime fp).

## Hand-off
- Patch file: `n11f-branch3-owner-mismatch.patch` (unified diff vs `2026-10-01-n11e-result-channel/src/`). If the tree
  drifts, this `.md`'s before/after blocks are authoritative — re-anchor the diff.
- cx-t0 builds N11f on top of the merged U10 (per board 22:15), co-building loader + host from the same header, then
  schedules the branch-3 window with the `n11e-smoke.json` fixes-marker already set (retro-20).
- Scope: this patch folds in row 4 (`:373` made non-fatal) — **approved by the outer ring** ("分支 3 修掉后加载会走到那
  里"): the row-3 success criterion "maps = 1 each" requires the load to complete past `:373`. It does **not** delete the
  emit block or the reporting — only its abort; a non-resolving `HiLogPrint` is recorded (branch 4) in the result
  channel but no longer fatal.
- Patch verified: `n11f-branch3-owner-mismatch.patch` applies `-p1` cleanly to the current
  `2026-10-01-n11e-result-channel/src` tree (dry-run + apply reproduce the intended file; brace balance 88/88
  unchanged). cx-t0 re-anchors if the post-U10-merge tree has drifted around these hunks.

Evidence: N11e source `2026-10-01-n11e-result-channel/src/sealed_child_provider_loader.c`
(`WLSCPL_OpenPreparedNamespace:263`, early-owner `:305-383`, `N11eFailure:51`); N11e verdict board 22:15
(`branch=3 index=0`); donor `n11-single-owner` (master `c2508ebdd`, musl `dynlink.c:2408-2575`).
