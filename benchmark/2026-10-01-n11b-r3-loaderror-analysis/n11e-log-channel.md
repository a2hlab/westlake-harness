# N11e — a log channel that survives the sealed-child namespace (+ an entry-survival marker)

**Problem (N11d closeout):** the N11d probe added logging *inside* the sealed-child loader
(`sealed_child_provider_loader.c`) via `dlsym(jni_owner_handles[1], "HiLogPrint")` and stayed **silent on-board** — the
weakly-referenced `HiLogPrint` resolves to **NULL** in the `westlake.sealed.child` musl namespace, so nothing printed
and we still can't tell which early-owner branch fails (`:313` `dlns_inherit` vs `:321` owner-verify `NOLOAD`/handle
mismatch vs `:333` the smoke-emit `dlsym` gate itself).

**Evidence this is a namespace problem, not a logging-API problem** — R3 capture
(`2026-10-01-n11b-early-owner/window-r3/board61b/capture/hilog.txt`, child PID 6203), grep counts:

| emitter | where it runs | lines in R3 capture |
|---|---|---|
| `WlascGateMarker*` (host plugin, `WLCGATE:LSP:*`, APPSPAWN tag) | **host** namespace | **8** (incl. `LOAD_ERROR:10 RESULT_ERROR:10 VALIDATED_COUNT:26 FAIL_LOAD_RESULT`) |
| loader `dlsym(HiLogPrint)` smoke markers (`N10b-JNI-OWNER`/`N11b-EARLY-OWNER`) | **sealed child** | **0** |
| loader `fprintf(stderr,…)` (`[stderr]`-tagged) at LSP time | **sealed child** | **0** |

So at loader-failure time the **only proven channel is the host**. Both in-loader channels are dead here — not just
HiLogPrint (`dlsym`→NULL) but **stderr too** (the child's stderr is not wired to hilog this early; the `[stderr]` lines
Toutiao shows are post-`handleBindApplication`, far later). N11d's approach could not have worked.

## Where the markers come from (so we extend the right thing)

`WLCGATE:LSP:*` is printed by the **host** in `stock_child_plugin/src/westlake_android_child_plugin.c`:
- `WlascGateMarker(text,len)` (`:28`) — **unconditional `write(STDERR_FILENO,…)`** then `dlsym(RTLD_DEFAULT,"HiLogPrint")`.
- `WlascGateMarkerValue(text,uint32)` (`:46`) — `dlsym(RTLD_DEFAULT,"HiLogPrint")` then `print_log("%{public}s:%{public}u")`.
  (No stderr fallback; but in the host ns `HiLogPrint` resolves — that is why we see `…:10`, `…:26` under the APPSPAWN
  tag.)

The host calls the loader at `LoadSealedProviderAfterHooks` (`:568`):
```c
loader_error = WLSCPL_LoadSealedProvider(&g_sealed_child_loader, &load_request, &load_result);
if (loader_error != WLSCPL_OK || load_result.error != WLSCPL_OK || … || load_result.provider_handle == 0) {
    WlascGateMarkerValue("WLCGATE:LSP:LOAD_ERROR",   (uint32_t)loader_error);      // R3: 10
    WlascGateMarkerValue("WLCGATE:LSP:RESULT_ERROR", (uint32_t)load_result.error); // R3: 10 = WLSCPL_ERROR_DLOPEN
    WlascGateMarkerValue("WLCGATE:LSP:VALIDATED_COUNT", load_result.validated_artifact_count); // R3: 26
    WLASC_GATE_MARKER("WLCGATE:LSP:FAIL_LOAD_RESULT");
    return -1;
}
```
`load_result` is a **host-stack out-param** (`WlscplLoadResultV1`, declared in the host frame). The loader already writes
`error`, `validated_artifact_count`, `child_pid`, `artifact_generation`, `provider_handle` into it — the host reads them
after return. **This is the channel: the loader writes to host memory (no symbol resolution, works in any namespace); the
host prints it where logging works.** The loader just collapses every early-owner failure into `error = WLSCPL_ERROR_DLOPEN`
(`10`) and a NULL handle, with no branch / library-index / `dlerror` detail.

Header today — `stock_child_plugin/include/sealed_child_provider_loader.h:82`:
```c
typedef struct WlscplLoadResultV1 {
    uint32_t abi_version; uint32_t struct_size; WlscplError error;
    uint32_t validated_artifact_count; uint64_t child_pid; uint64_t artifact_generation; void *provider_handle;
} WlscplLoadResultV1;
```

## N11e design — carry the detail out in the result struct; host prints it (PRIMARY)

### 1. Extend `WlscplLoadResultV1` (append-only)
```c
typedef struct WlscplLoadResultV1 {
    /* … existing 7 fields, unchanged order … */
    uint32_t last_stage;        /* entry-survival marker: highest WLSCPL_STAGE_* reached (see below) */
    uint32_t fail_branch;       /* 0 = none; else WLSCPL_FAILB_* */
    uint32_t fail_artifact_index; /* manifest index of the artifact/owner in play at failure, else 0xFFFFFFFF */
    int32_t  fail_errno;        /* errno snapshot at the failing dl* call (0 if n/a) */
    char     fail_detail[160];  /* dlerror() text snapshot, NUL-terminated, truncated */
} WlscplLoadResultV1;
```
Append at the **end** so the existing field offsets do not move. Both the loader `.so` and the host plugin are rebuilt
from this one header, so the host's `load_result.struct_size != sizeof(load_result)` gate stays self-consistent.
**Bump `WLSCPL_ABI_VERSION`** too (and let `WLSCPL_GetBuildGeneratedManifest` regenerate its `abi_version`): a mixed
old-host/new-loader (or vice-versa) deploy then fails the `abi_version`/`struct_size` gate *loudly* instead of reading a
short struct. (Deploy both artifacts together — they are co-built from `stock_child_plugin/`.)

Branch / stage enums (new, in the header):
```c
enum { WLSCPL_FAILB_NONE=0, WLSCPL_FAILB_DLNS_INHERIT=1,      /* :313 dlns_inherit(default<-closure) != 0        */
       WLSCPL_FAILB_OWNER_NOLOAD=2,  /* :321 dlopen_ns(NOLOAD) == NULL  (owner not resident in default)        */
       WLSCPL_FAILB_OWNER_MISMATCH=3,/* :321 shared != jni_owner_handles[owner] (wrong handle identity)        */
       WLSCPL_FAILB_EMIT_RESOLVE=4,  /* :333 dlsym(owner,"HiLogPrint")==NULL (the smoke-emit gate — remove, see §4) */
       WLSCPL_FAILB_ARTIFACT_DLOPEN=5 /* per-artifact dlopen in the main loop                                    */ };
enum { WLSCPL_STAGE_ENTER=1, WLSCPL_STAGE_ARTIFACTS_DONE=2, WLSCPL_STAGE_BEFORE_INHERIT=3,
       WLSCPL_STAGE_AFTER_INHERIT=4, WLSCPL_STAGE_BEFORE_OWNER_VERIFY=5, WLSCPL_STAGE_AFTER_OWNER_VERIFY=6,
       WLSCPL_STAGE_PROVIDER_OPEN=7, WLSCPL_STAGE_DONE=8 };
```

### 2. Loader fills the fields (no logging — plain stores to host memory + `dlerror()`)
The failing branches are in a helper that returns `void*` (R3 build = the N11b early-owner loader,
`2026-10-01-n11b-early-owner/src/sealed_child_provider_loader.c:308–345`), so it cannot see `result`. Use a
**file-static fail record** the helper sets, which `WLSCPL_LoadSealedProvider` copies into `*result` right before it
sets `result->error = WLSCPL_ERROR_DLOPEN`:
```c
static _Thread_local struct { uint32_t stage, branch, index; int err; char detail[160]; } g_wl_fail;
#define WL_STAGE(s)            (g_wl_fail.stage = (s))
#define WL_FAIL(b,i)  do { g_wl_fail.branch=(b); g_wl_fail.index=(i); g_wl_fail.err=errno; \
                           const char* e=dlerror(); /* resolvable in sealed ns — loader already calls it at :301 */ \
                           if(e){ size_t n=strlen(e); if(n>sizeof(g_wl_fail.detail)-1) n=sizeof(g_wl_fail.detail)-1; \
                                  memcpy(g_wl_fail.detail,e,n); g_wl_fail.detail[n]=0; } } while(0)
```
Then, at each branch (early-owner block):
```c
WL_STAGE(WLSCPL_STAGE_BEFORE_INHERIT);
if (dlns_inherit(&default_namespace,&closure_namespace,"liboh_adapter_bridge.so:liboh_android_runtime.so")!=0){
    WL_FAIL(WLSCPL_FAILB_DLNS_INHERIT, 0xFFFFFFFFu); (void)dlclose(handle); return NULL; }   /* :313 */
WL_STAGE(WLSCPL_STAGE_AFTER_INHERIT);
for (owner=0; owner<2U; ++owner){
    WL_STAGE(WLSCPL_STAGE_BEFORE_OWNER_VERIFY);
    void* shared = dlopen_ns(&default_namespace, owner_paths[owner], RTLD_NOW|RTLD_LOCAL|RTLD_NOLOAD);
    if (shared==NULL){ WL_FAIL(WLSCPL_FAILB_OWNER_NOLOAD, owner); (void)dlclose(handle); return NULL; }   /* :321 */
    if (shared!=jni_owner_handles[owner]){ WL_FAIL(WLSCPL_FAILB_OWNER_MISMATCH, owner);
        (void)dlclose(shared); (void)dlclose(handle); return NULL; }
    (void)dlclose(shared);
}
WL_STAGE(WLSCPL_STAGE_AFTER_OWNER_VERIFY);
```
`dlerror()` / `strlen` / `memcpy` / `errno` are plain libc and resolve in the sealed ns (the loader already uses
`fprintf`+`dlerror()` at `:301`). **No `HiLogPrint`, no new DT_NEEDED, no `dlns` change — only stores.**

In `WLSCPL_LoadSealedProvider`, wherever it maps a helper NULL to `result->error = WLSCPL_ERROR_DLOPEN`, also do:
```c
result->last_stage = g_wl_fail.stage; result->fail_branch = g_wl_fail.branch;
result->fail_artifact_index = g_wl_fail.index; result->fail_errno = g_wl_fail.err;
memcpy(result->fail_detail, g_wl_fail.detail, sizeof(result->fail_detail));
```
Set `result->last_stage = WLSCPL_STAGE_DONE` on the success path (the entry-survival marker is emitted every run, pass or
fail).

### 3. Host prints the new fields — one tag prefix `[N11e-PROBE]`, with an UNCONDITIONAL entry line
Single prefix `[N11e-PROBE]` for everything (retro-20 wants "同一标签前缀"), bracket style to match the `fixes[].markers`
regex convention already on the board (`\[N11b-EARLY-OWNER\] …`). New host helper, modelled on `WlascGateMarker` so it
has the same unconditional-stderr + HiLog dual emit and prints a **runtime** string:
```c
static void WlascGateMarkerText(const char *prefix, const char *val){
    (void)write(STDERR_FILENO, prefix, strlen(prefix)); (void)write(STDERR_FILENO, " ", 1);
    (void)write(STDERR_FILENO, val, strnlen(val, 180)); (void)write(STDERR_FILENO, "\n", 1);
    void *s = dlsym(RTLD_DEFAULT,"HiLogPrint"); WlascHiLogPrintFn p=(WlascHiLogPrintFn)0; memcpy(&p,&s,sizeof p);
    if (p) p(3,4,0xD000F00u,"APPSPAWN","%{public}s %{public}s", prefix, val);
}
```
**Unconditional entry-survival marker** — emit at the top of `LoadSealedProviderAfterHooks` (right after
`WLCGATE:LSP:ENTER`), on **every** run, pass or fail. It has to be unconditional so it is safe to register in
`fixes[].markers` (a conditional marker would spuriously fail the window on the run where it does not appear):
```c
WlascGateMarkerText("[N11e-PROBE]", "entry");    /* ALWAYS — proves the probe build is live + host reached the loader call */
```
Then on the existing **failure** branch, after the three current `WlascGateMarkerValue` calls, print the detail the
loader carried out — same prefix, so one registered tag covers it:
```c
char line[256];
snprintf(line, sizeof line, "fail stage=%u branch=%u index=%u errno=%d detail=%s",
         load_result.last_stage, load_result.fail_branch, load_result.fail_artifact_index,
         load_result.fail_errno, load_result.fail_detail);
WlascGateMarkerText("[N11e-PROBE]", line);
```
Both run in the **host** ns (HiLogPrint resolves, proven by the 8 existing markers) and also write host stderr.

### Expected R3-equivalent output after N11e
`[N11e-PROBE] entry` appears on every run (the entry-survival beacon). On the R3 repro the failure line then reads e.g.:
```
[N11e-PROBE] entry
WLCGATE:LSP:VALIDATED_COUNT:26
[N11e-PROBE] fail stage=5 branch=2 index=0 errno=2 detail=dlopen_ns ... not found in namespace default
WLCGATE:LSP:FAIL_LOAD_RESULT
```
(`stage=5` = BEFORE_OWNER_VERIFY, `branch=2` = WLSCPL_FAILB_OWNER_NOLOAD, `index=0` = `liboh_adapter_bridge.so`,
`errno=2` = ENOENT) — directly answering the N11d question (which branch / which owner / what the linker said).

### 3a. Smoke spec (retro-20: `expect`-referenced tags MUST be in `fixes[].markers`)
From retro-20, `board_run` refuses a window whose `expect`/`offline_precheck.expect` references a log tag not present in
the smoke spec's `fixes[].markers`. Because `[N11e-PROBE] entry` is **unconditional**, it is the marker to register — the
window boards, and matching it proves the probe is live. The failure detail shares the prefix, so the one registered
regex `\[N11e-PROBE\]` covers reading it offline. Concrete `n11e-smoke.json` (shipped alongside this doc):
```json
"fixes": [
  { "id": "N11e-PROBE-ENTRY", "key": "helloworld",
    "markers": ["\\[N11e-PROBE\\] entry"] }
]
```
The branch detail (`[N11e-PROBE] fail stage=… branch=…`) is read **offline** from the shard hilog in
`offline_precheck.expect` (same pattern N11d used for its branch log), NOT asserted in `fixes` — on a run where the load
*passes* the fail line is absent and must not fail the window. Keep `expect.boot_fp`/`runtime_fp` = U9
(`boot 4db882a81732`, runtime per board); `probe.files` pins the N11e child `.so` sha (cx-bms fills).

## §4 — a free bug this surfaces
Branch `:333` (`dlsym(jni_owner_handles[1],"HiLogPrint")==NULL → dlclose; return NULL`) means the loader **fatalises the
whole provider load if its own smoke-marker symbol does not resolve** — the exact dead channel we just proved. This emit
block should be **deleted** in N11e (it is pure diagnostics, and it is both useless *and* a failure mode). If the goal is a
heartbeat, use the result-struct `last_stage` instead. Flag to cx-bms: removing `:328–343` is part of N11e, not a
separate change — it cannot both be the log channel and a load gate.

## Fallbacks (ranked; why not primary)
1. **dlsym `HiLogPrint` inside the loader** (N11d's approach) — **rejected**: proven NULL in `westlake.sealed.child`
   (R3: 0 lines). Resolving via `jni_owner_handles[*]` is what `:333` already tries and is itself the failure.
2. **`fprintf(stderr)` inside the loader** — **rejected as primary**: proven not captured at LSP time (R3: 0 `[stderr]`
   lines). It *does* reach hilog later (post-bind), so it is fine for post-bootstrap diagnostics, not for the loader.
3. **`/dev/kmsg`** — namespace-agnostic (raw `open`/`write`, no symbol resolution, survives the sealed ns), but **two
   blockers**: (a) the appspawn child likely lacks write permission / `CAP_SYS_ADMIN` on `/dev/kmsg` (expect `EACCES` —
   must be tested, read-only, before relying on it); (b) **the harness capture does not pull kmsg/dmesg** — there is no
   `kmsg`/`dmesg` reference anywhere in `scripts/lab/`, so even a successful write is invisible until capture is extended
   with a `hdc shell dmesg`/`cat /proc/kmsg` pull. Use only as a last resort *and* only after extending capture; the
   result-struct channel needs neither.

## Why the struct channel is the right rule (not just this bug)
The sealed child exists to deny the provider ambient capability — including, incidentally, a resolvable logger. Any future
diagnostic that needs to speak from inside that namespace will hit the same wall. **Rule set by N11e: sealed-child code
reports outward by writing a versioned, host-allocated result struct; the host (which has a working logger) renders it.**
Logging *from* the sealed ns (HiLogPrint or stderr) is unreliable by construction and must not be a load gate.

## Hand-off (cx-bms, U11/U-next window)
- Files: `stock_child_plugin/include/sealed_child_provider_loader.h` (struct + enums + ABI bump);
  `…/src/sealed_child_provider_loader.c` (stage/fail stores on each branch; **delete** the `:328–343` emit gate);
  `…/src/westlake_android_child_plugin.c` (`WlascGateMarkerText` + the unconditional `[N11e-PROBE] entry` beacon + the
  `[N11e-PROBE] fail …` line in the LSP failure branch).
- Smoke spec shipped: `benchmark/2026-10-01-n11b-r3-loaderror-analysis/n11e-smoke.json` — `fixes[].markers` already
  registers `\[N11e-PROBE\] entry` so the window clears retro-20; cx-bms fills `probe.files` sha + `expect.runtime_fp`.
- Co-build and co-deploy loader `.so` + host plugin (same header); single-file replace with rollback per `deploy_generation.sh`.
- Window: re-run the R3 repro on 61b (U9 base); **offline_precheck** = hypothesis "`[N11e-PROBE] fail stage/branch/index`
  identifies the early-owner branch", evidence = `[N11e-PROBE] entry` unconditional + the `[N11e-PROBE] fail …` line under
  the APPSPAWN tag; expect fingerprint back to U9 on `before_unlock`. Diagnostics-only (no behavioural change beyond
  deleting the emit gate) → not lit-gated.
- Then N11f: fix the branch the probe names (the actual `dlns_inherit`/owner-verify repair), which was the original N11
  goal.

Evidence: R3 capture `2026-10-01-n11b-early-owner/window-r3/` (hilog lines 30–46; PID 6203; `LOAD_ERROR:10` =
`WLSCPL_ERROR_DLOPEN`). Source: `stock_child_plugin/{include,src}/…` and the N11b loader
`2026-10-01-n11b-early-owner/src/sealed_child_provider_loader.c:308–345`. Marker impl
`westlake_android_child_plugin.c:28–61`. Capture mechanism: `scripts/lab` (no kmsg/dmesg pull).
