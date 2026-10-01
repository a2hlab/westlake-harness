# N11f patch — branch=3 OWNER_MISMATCH (bridge second copy in `default`)

**N11e verdict (board 22:15):** `branch=3 WLSCPL_FAILB_OWNER_MISMATCH`, `index=0` (`liboh_adapter_bridge.so`). The
`detail` quoting `libartbased` is a **stale dlerror** (the `N11eFailure` bug, fixed below). Decision-table **row 3**.

## Premise correction (board latest ACK(80))
N11e showed the `default` bridge copy is **already present at `:357` (provider-load stage, before Java runs)**, and 5ea
U9's appspawn-x **parent maps have no bridge** (not fork-inherited). So it is **not** the Java NativeLoader that mints it.
Pinning the mint site in the N11e source:
- The loader's artifact loop uses **only** `ops->open_local_now` = `RealOpenLocalNow` → `dlopen_ns(&closure_namespace,…)`
  (`:527`, `:304`). It **never** loads anything into `default`.
- The **only** default-namespace `dlopen` in the whole TU is `WLSCPL_OpenPreparedNamespace` (`:275`), which is handed to
  the host as `child_services.open_sealed_exact` (`westlake_android_child_plugin.c:691`; consumer validated
  `host_runtime_services.c:223`). Its **caller is the OH appspawn stock host** (outside these 3 TUs), on the
  runtime/JNI-owner-prepare path — which runs **before Java**, matching the `:357` observation.

**Conclusion:** the default bridge copy is minted by the **host invoking `open_sealed_exact` (→ `WLSCPL_OpenPreparedNamespace`
→ default `dlopen`) for the bridge during runtime-prepare**, not by the NativeLoader and not by fork inheritance. I cannot
name the exact host call-site from this source subset (it is in the OH appspawn framework), so N11f also **adds an
observation** (branch 6, below) that will confirm the timing on-board.

## Root cause + fix
`WLSCPL_OpenPreparedNamespace` (`:263`) ends in a plain **`dlopen(absolute_path, flags)`** (default ns). Whoever asks it
for `liboh_adapter_bridge.so` (host runtime-prepare, and later the NativeLoader) gets a **fresh second copy**. The loader
then publishes via `dlns_inherit` (`:347`) and verifies by `dlopen_ns(default, …, RTLD_NOLOAD)` (`:357`); the NOLOAD check
**finds the host-minted copy** but it is `!= jni_owner_handles[0]` → `OWNER_MISMATCH` (`:358`). Two bridge copies = the U7
double-load.

Fix (covers **every** caller of the callback, so the premise correction does not change it): stop `default` ever minting
its own copy — intercept the two canonical owner paths in `WLSCPL_OpenPreparedNamespace` and **return the resident sealed
handle** (`n11-single-owner`, master `c2508ebdd`: "intercept only these two canonical names/paths in the host open
callback and return their resident sealed-owner handles"; OH6.1 musl `dynlink.c:2408-2575`). The old `dlns_inherit`+verify
block is deleted (it was the mismatch *detector*, not the fix).

## Changes (3 files: `src/sealed_child_provider_loader.c`, one enum in `include/sealed_child_provider_loader.h`, and the host done line in `src/westlake_android_child_plugin.c`; manifest unchanged)

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
    /* N11f: the two owners are opened in default via this callback (host
     * runtime-prepare, and later the NativeLoader). Return the resident
     * sealed-owner handle instead of dlopen'ing a second copy (branch-3 root).
     * Runs in the host/default context where stderr reaches hilog, so observe
     * here directly. */
    for (size_t owner = 0U; owner < 2U; ++owner) {
        if (strcmp(absolute_path, g_owner_paths[owner]) == 0) {
            if (g_owner_handles[owner] != NULL) return g_owner_handles[owner];
            /* Host asked BEFORE the provider published the owners: this dlopen
             * mints the default copy (branch-3 root). Record OWNER_PUBLISH_LATE
             * in the result struct; it is surfaced by the host's unconditional
             * [N11e-PROBE] done line (loader-stage stderr does NOT reach hilog,
             * so NO fprintf here). Fall through so the host proceeds. */
            g_n11e_failure.branch = WLSCPL_FAILB_OWNER_PUBLISH_LATE;
            g_n11e_failure.index = (uint32_t)owner;
            break;
        }
    }
    return dlopen(absolute_path, flags);
}
```
New enum value (header `include/sealed_child_provider_loader.h`): `WLSCPL_FAILB_OWNER_PUBLISH_LATE = 6`.

### 2a. Surface the result unconditionally — host prints `[N11e-PROBE] done` on success too (fixes two silent-observation bugs)
Two flaws in a first-cut branch-6 observation (both corrected per board): (i) a `fprintf(stderr)` from the loader/callback
stage does **not** reach hilog — N11e already proved this (the branch-3 fatal line came through the host, not the loader);
(ii) the struct's `branch` was only printed by the host on the **failure** path, so after the branch-3 fix (load
succeeds) a non-fatal branch 4/6 would never show. Fix: the **host** prints an **unconditional** done line right after
`WLSCPL_LoadSealedProvider` returns (success *and* failure), in `westlake_android_child_plugin.c`:
```c
    loader_error = WLSCPL_LoadSealedProvider(&g_sealed_child_loader, &load_request, &load_result);
    {   /* N11f: unconditional — carries non-fatal branch 4/6 out even on success */
        char doneline[96];
        (void)snprintf(doneline, sizeof(doneline), "done stage=%u branch=%u index=%u",
                       load_result.last_stage, load_result.fail_branch, load_result.fail_artifact_index);
        WlascGateMarkerText("[N11e-PROBE]", doneline);   /* host ctx: stderr + HiLog, reaches hilog */
    }
    if (loader_error != WLSCPL_OK || … ) { … existing failure prints … }
```
`WlascGateMarkerText` is the existing host marker (`:62`) that writes stderr **and** HiLog from the host context (the one
proven to surface — the 8 `WLCGATE` lines in R3). The branch-6/4 record set in the loader/callback is copied into
`load_result.fail_branch` at the loader's result copy-out, so the host done line prints it. **The smoke marker keys on
`\[N11e-PROBE\] done`** (unconditional → safe to register; retro-20) — see `n11e-smoke.json`.

**Branch 6 (OWNER_PUBLISH_LATE) decision.** The owners are populated in `g_owner_handles` only when the provider's
closure-load branch runs (`:327`). If the host calls `open_sealed_exact(bridge)` on its runtime-prepare path **before**
that, the callback falls through to `dlopen` and mints the default copy; it records branch 6, and the host done line
reports it. Next window: **branch=0 + single-copy maps → fixed** (host asks after publication); **branch=6 + two copies →
host asks first**, and N11g publishes owners earlier (into `closure_namespace` at child-init before the first
`open_sealed_exact`, or a host "prepare owners" step). The callback intercept is correct either way; branch 6 only decides
whether publication must move earlier.

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
- `[N11e-PROBE] done stage=.. branch=.. index=..` prints on **every** load return (the smoke marker + branch carrier).
  `branch=0` = clean. No `[N11e-PROBE] fail branch=3` (OWNER_MISMATCH gone).
- **Branch-6 decision (the key new signal), read off the `done` line:** `branch=0` + single-copy maps → the host asked
  after publication → **fixed**. `branch=6` (OWNER_PUBLISH_LATE) + bridge still two copies → the host's runtime-prepare
  `open_sealed_exact(bridge)` runs before the provider publishes the owners → N11g must publish earlier (owners into
  `closure_namespace` at child-init before the first `open_sealed_exact`). `branch=4` = HiLogPrint unresolved (non-fatal).
- If anything still fails, the result struct + host `[N11e-PROBE] fail …` reports it with a **fresh** dlerror (not
  `libartbased`). Branch 4 can no longer abort (now non-fatal) — if `HiLogPrint` doesn't resolve it is recorded, not
  fatal.
- `abi_diff --calls` and DT_NEEDED on the rebuilt `libwestlake_android_child.z.so` unchanged except the removed
  `dlns_inherit` call edge; `check_frozen` 0 violations; controls (helloworld hard, zigzag advisory) lit;
  `before_unlock` restores U9 (`boot 4db882a81732`, board runtime fp).

## Hand-off
- Patch file: `n11f-branch3-owner-mismatch.patch` — **3-file** unified diff (`include/…loader.h`, `src/…loader.c`,
  `src/westlake_android_child_plugin.c`) vs `2026-10-01-n11e-result-channel`. If the tree drifts, this `.md`'s before/after
  blocks are authoritative — re-anchor the diff.
- cx-t0 builds N11f on top of the merged U10 (per board 22:15), co-building loader + host from the same header, then
  schedules the branch-3 window with the `n11e-smoke.json` fixes-marker (`\[N11e-PROBE\] done`, retro-20) already set.
- Scope: this patch folds in row 4 (`:373` made non-fatal) — **approved by the outer ring** ("分支 3 修掉后加载会走到那
  里"): the row-3 success criterion "maps = 1 each" requires the load to complete past `:373`. It does **not** delete the
  emit block or the reporting — only its abort; a non-resolving `HiLogPrint` is recorded (branch 4) in the result
  channel but no longer fatal.
- Patch verified: applies `-p1` cleanly to the current `2026-10-01-n11e-result-channel` tree (dry-run + apply reproduce
  all 3 intended files; brace balance loader 88/88, host 103/103). cx-t0 re-anchors if the post-U10-merge tree has
  drifted around these hunks.

Evidence: N11e source `2026-10-01-n11e-result-channel/src/sealed_child_provider_loader.c`
(`WLSCPL_OpenPreparedNamespace:263`, early-owner `:305-383`, `N11eFailure:51`); N11e verdict board 22:15
(`branch=3 index=0`); donor `n11-single-owner` (master `c2508ebdd`, musl `dynlink.c:2408-2575`).
