# #96 — fixing the 8 ABI signature drifts (5 functions) so the rebuilt bridge becomes a faithful 846 replacement

`scripts/lab/abi_diff.py --old <846> --new <7cf8ebcc>` (master 9ae7bbe3d) quantifies the gap the export-table
scan missed: **exports old 2357 / new 2661; removed 14; added 318; signature drift 8 (5 functions); consumer
breaks 0.** The 8 drift rows are the 5 functions below (the `ComponentResolverServiceV1` ctor contributes several
rows because its `C1`/`C2` variants each diff). Exit criterion for any new artifact: **`abi_diff` exit 0**.

## 1. The 5 drifted functions (exact old → new, demangled)

| # | function | 846 (old) | rebuild 7cf8ebcc (new) | delta |
|---|---|---|---|---|
| 1 | `OHInputBridge::injectKeyEvent` | `(int,int,int,int,long,long)` | `(…,long,long, **long**, **std::function<void()>**)` | +1 `long` +1 callback |
| 2 | `OHInputBridge::injectTouchEvent` | `(int,int,float,float,long,long)` | `(…,long,long, **long**, **std::function<void()>**)` | +1 `long` +1 callback |
| 3 | `ComponentResolverServiceV1::ctor` (C1+C2) | `(ComponentCatalogProviderV1*, PackageGuardReaderV1*, ResolveFaultInjectorV1*)` | `(…, **ComponentStateReaderV1***)` | +1 ptr |
| 4 | `ConfigureComponentResolverRuntimeV1` | `(Catalog*, Guard*, CallerResolveContextProviderV1*, FaultInjector*, string*)` | `(…, **ComponentStateReaderV1***)` | +1 ptr |
| 5 | `OHWindowManagerClient::createSession` | `(_JavaVM*, _jobject*, 4×string const&, int,int,int,int, unsigned long)` — mangled `…iiiim` | `(…, int,int,int,int, **int**, unsigned long)` — `…iiiiim` | +1 `int` (5th int, before the trailing handle) |

All five are the N2 source being a **later revision than 846** (B1): the API evolved. #5 is the one the on-board
t3 window implicated — every app died at the first `addView` with `WindowManager$InvalidDisplayException: the
specified display can not be found` (see `t3-window-5ea-result.md`).

## 2. The load-bearing fact: `consumer_breaks = 0`

`abi_diff` with the deployed runtime as `--consumer` finds **no** undefined symbol that 846 satisfied and the
rebuild doesn't. So **no deployed binary links the 846-mangled versions of these 5 symbols**; the callers are
**internal to the bridge** — e.g. the `adapter.activity.WindowSessionProxy` JNI binding (registered by the bridge
itself) calls the bridge's own `createSession`. Two consequences:

- **Re-emitting old-signature *exports* alone does not change what runs.** The bridge's internal caller is
  compiled against the *new* signature, so it calls the new `createSession`; an old-signature export wrapper would
  sit unused. Option A **makes `abi_diff` exit 0 but does not, by itself, fix the t3 `InvalidDisplayException`.**
- **"Recompile the callers to the new signature" (Option B as literally stated) is already done internally** — the
  bridge's own callers are same-source and already on the new API. So B-as-stated is a no-op here, and the board
  still fails. The gap is the new `createSession`'s **behavior** against the deployed OH window environment.

## 3. Recommended fix (two parts; both needed)

### Part 1 — pass the `abi_diff` export gate: add 846-signature compat entry points (Option A), strict superset
For all 5 functions, add an exported symbol with the **846 mangled name/signature** that forwards to the new impl,
so the rebuild exports BOTH signatures (a strict ABI superset of 846) → `abi_diff` exit 0. Defaults for the new
params, by function:
- **#1/#2 `injectKeyEvent`/`injectTouchEvent`**: the extra `long` + `std::function<void()>` are a new event
  field (likely an eventId/deviceId/displayId `long`) and a completion callback. Old-sig wrapper forwards with the
  `long` = `0` and the callback = **empty** (`std::function<void()>{}`) — safe iff the new impl treats an empty
  callback as "no completion notify" (verify in source; the new code must null-check before invoking it).
- **#3/#4 resolver ctor / `ConfigureComponentResolverRuntimeV1`**: the extra `ComponentStateReaderV1*` — old-sig
  wrapper passes `nullptr` iff the new impl tolerates a null state-reader (verify: the resolver must guard every
  `stateReader_->…` with a null check, else fall back to the pre-state-reader behavior). If it cannot tolerate
  null, the wrapper must pass a process-static **no-op `ComponentStateReaderV1`** instance.
- **#5 `createSession`**: old-sig (4-int) wrapper forwards to the 5-int impl with the inserted int = **the value
  846 used implicitly** for that slot — see Part 2; a wrong default reproduces the `InvalidDisplayException`.

### Part 2 — fix the board failure: make the window-session path 846-faithful
Because the internal caller uses the new API (Part 1's export wrapper is not on that path), the
`InvalidDisplayException` fix must be in the **impl + its internal caller**:
1. **Determine the new 5th int's semantic** (offline, source + disasm): the t3 symptom ("display can not be
   found") says it is display/window-type/flags-related. Confirm by (a) reading the rebuilt bridge's
   `createSession` source for how the 5th int is consumed (does it feed a `displayId` / `SetDisplayId` / scene
   window-type?), and (b) disassembling 846's `createSession` to see what value occupied that slot's role (846
   had 4 ints — which one carried the display, and what default did it use).
2. **Then either:**
   - **(A-faithful)** point the bridge's `WindowSessionProxy` JNI binding at the **846-signature** `createSession`
     entry (Part 1's wrapper), so the window path goes through the 4-int signature with the display derived the
     846 way; **or**
   - **(impl fix)** in the new 5-int `createSession`, default/derive the inserted int so the session targets the
     valid default display (displayId 0 / the app's current display from `getDisplayInfo(0)=1200x1920` that the
     app already resolved) when the caller doesn't supply a meaningful one.
3. **Re-run the t3 window** (the `board_run` plan in this dir, with the new artifact): Gate 0 child-view sha +
   HW/ZZ controls must come up (no `InvalidDisplayException`, no `System.exit(1)`), then the View/Compose/lit
   shard.

### The clean alternative (if a faithful 846 drop-in is the goal)
Since the drift is purely B1 (N2 is a later rev), the least-surprising artifact re-emits **846's signatures
end-to-end** — exports AND the bridge-internal callers — for these 5 functions, i.e. build these TUs from (or patch
them to) the 846 API shape. That yields `abi_diff` exit 0 *and* 846 behavior without carrying the new rev's evolved
window/input/resolver API. This is the t2-D "compat-export rebuild" fallback, extended to the internal callers.

## 4. Exit criteria (gate order)
1. `abi_diff --old <846> --new <new-artifact>` → **exit 0** (no drift, no consumer break). Offline, before any board.
2. On-board t3 re-run (single variable, this dir's `board_run` plan): HW/ZZ + View/Compose/lit shards show **no
   `InvalidDisplayException`/`System.exit(1)`** and parity with the U8+846 baseline.
Only then freeze-replace 846 with the new artifact.

## 5. Status
- 8 drifts = 5 functions, exact signatures captured (§1). createSession +1 int = the t3 suspect, confirmed by
  `abi_diff`.
- Fix = Option A compat exports (→ `abi_diff` exit 0) **plus** a behavioral createSession fix (Part 2), because
  `consumer_breaks=0` means the internal caller won't hit the export wrapper on its own. Offline-designed; new
  artifact + both gates before any board window.
- Evidence: `abi_diff` JSON drift rows (reproduce: `abi_diff.py --old vm-copies/bridge-84695d62/… --new
  _cc-wiki-t3-bridge/…rebuilt-7cf8ebcc`), `t3-window-5ea-result.md` (the InvalidDisplayException).
