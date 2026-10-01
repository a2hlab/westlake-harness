# N11f decision table — one verified success-path fix per N11e branch

**Purpose.** N11e is a probe: it names which of 5 branches the sealed-child loader dies on (R3 = `WLSCPL_ERROR_DLOPEN`,
no detail). N11f is the fix, and it is **data-driven** — you do not apply all five, you read `[N11e-PROBE] fail
branch=<b> index=<i> detail=<dlerror>` from the window and apply the one row below. Every fix is copied from an
**already-verified** implementation in our own history (AGENTS.md "验证过的就抄"); none is invented here.

Branch source = the deployed N11e loader `benchmark/2026-10-01-n11e-result-channel/src/sealed_child_provider_loader.c`
(cx-bms build): `N11eFailure(branch,index,detail)` with the enum in `sealed_child_provider_loader.h`.

## The early-owner block, annotated (what each branch means)
The block publishes the two canonical JNI owners (`liboh_adapter_bridge.so`, `liboh_android_runtime.so`) from the sealed
`closure_namespace` to the `default` namespace so the Java NativeLoader reuses the **same** mapping (single copy). It is
`n10-bridge-owner` Candidate B (`drafts/B-owner-inherit.diff`, adapting real-work `be16148da`
`WLSCPL_InheritAndroidRuntimeV1`) applied inline. Lines (n11e-result-channel loader):
- `:318` route-a ART `dlopen_ns(closure, RTLD_NOLOAD)` → `branch 5 ARTIFACT_DLOPEN` if NULL
- `:327` per-owner load into `closure` → `branch 5 ARTIFACT_DLOPEN` if NULL (`index`=owner)
- `:347` `dlns_inherit(default ← closure, "bridge:runtime")` → `branch 1 DLNS_INHERIT` if `!=0`
- `:357` per-owner `dlopen_ns(default, RTLD_NOLOAD)` → `branch 2 OWNER_NOLOAD` (NULL) / `branch 3 OWNER_MISMATCH` (handle ≠ sealed)
- `:373` `dlsym(owner,"HiLogPrint")` → `branch 4 EMIT_RESOLVE` if NULL
- `:532` manifest artifact `open_local_now` → `branch 5 ARTIFACT_DLOPEN` (`index`=artifact)

Cross-cutting gate for every build fix below (the N11 single-owner oracle, master `c2508ebdd`): board maps show
**ART=1, JVM=1, bridge=1, runtime=1** instance each (not path-count); `abi_diff --calls` and DT_NEEDED unchanged on the
touched `.so`; `check_frozen` 0 violations; controls (helloworld hard, zigzag advisory) lit; `before_unlock` restores U9
(`boot 4db882a81732`, board runtime fp). Diagnostics (branch-4) excepted — it changes no load behaviour.

## Decision table

| N11e branch | symptom | root cause | verified success-path fix (donor) | exact change | how the gate passes |
|---|---|---|---|---|---|
| **1 DLNS_INHERIT** (`:347`) | `dlns_inherit(default←closure,"bridge:runtime")` returns `!=0` | the owners are **already resident in `default`** (warm) before inherit runs, so musl refuses to merge their singleton state — Candidate B's own precondition: *"neither DSO already exists in default; otherwise changing inheritance cannot merge its mutable singleton state"* (`B-owner-inherit.diff`) | **Publish via the host open callback, not post-hoc inherit** (`n11-single-owner`, master `c2508ebdd`): intercept the two canonical names in `WLSCPL_OpenPreparedNamespace` and return the **resident sealed-owner handle**, so `default` never cold-loads them and no inherit is needed. musl `dynlink.c:2408-2448` (direct inherited resident objects) supports this; `LOCAL_NS_PREFERED` is why recursive inherit is fragile. | In `stock_child_plugin` host: `WLSCPL_OpenPreparedNamespace(path,flags)` (`sealed_child_provider_loader.h:102`, wired as `child_services.open_sealed_exact`) — for the 2 canonical paths return `jni_owner_handles[owner]`; **remove** the loader `:347` `dlns_inherit` + `:357` verify (the callback now owns publication). Ordinary libs unchanged. | single-owner oracle: bridge/runtime=1 each; `[N11-CL-OWNER]` host-callback success log; no `dlns_inherit` dependency |
| **2 OWNER_NOLOAD** (`:357`) | after inherit, `dlopen_ns(default, owner, RTLD_NOLOAD)` returns NULL — owner still not visible in `default` | inherit "succeeded" (`!=0` not hit) but did not actually make the name resolvable in `default` (recursive-inherit name-reuse deferral, `LOCAL_NS_PREFERED`) | Same host-callback publication as branch 1 — the NOLOAD check then resolves to the published handle. **Do NOT "去 NOLOAD" by itself here**: the N2 compat shim's NOLOAD-only, no-fresh-fallback discipline (`n10-bridge-owner`: resolver `0x1971b0` NOW\|NOLOAD, source `b94f69e4`/commit `42b5f71b8`, runtime `216b68fb`) is what keeps a single copy — dropping NOLOAD without the callback would fresh-load a 2nd copy. "去 NOLOAD" is only safe **combined with** the callback's dedupe (it returns the resident handle regardless of flag). | host callback returns resident handle (as branch 1). If keeping an explicit publish step, drop `RTLD_NOLOAD` on the owner open **only** once the callback guarantees identity; otherwise keep NOLOAD and let the callback satisfy it. | oracle = 1 each; NOLOAD check resolves to the published handle, no 2nd map |
| **3 OWNER_MISMATCH** (`:358`) | `shared != jni_owner_handles[owner]` — the `default` handle differs from the sealed handle = **two copies** (the exact U7 double-load: two bridge + two runtime bases, `n10-bridge-owner`) | `default` got its own fresh map of the owner instead of sharing the sealed one | host-callback intercept returns the **same** sealed handle for `default` too (`n11-single-owner` "return their resident sealed-owner handles"); musl `dynlink.c:2572` reuses by inode before a new map, so identity holds | `WLSCPL_OpenPreparedNamespace` returns `jni_owner_handles[owner]` for the 2 canonical names/paths; delete the loader-side `:357-358` verify (identity is now guaranteed by construction) | oracle bridge/runtime=1 each **and** `shared == jni_owner_handles[owner]` by construction |
| **4 EMIT_RESOLVE** (`:373`) | `dlsym(jni_owner_handles[1],"HiLogPrint")==NULL` aborts the load | the diagnostic smoke-marker resolution was wired as a **load gate** — it logs nothing in the sealed ns and must not block load | **Delete the gate** (this is the one row whose success path is removal, not a donor): remove `:373-378`. (N11e deliberately kept it to *observe* whether it is the R3 branch; once observed, N11f removes it.) | remove the `emit`/`if(emit==NULL) return NULL` block (`:373-378`); keep nothing in its place | no behavioural dependency on HiLogPrint; load proceeds; `abi_diff`/DT_NEEDED unchanged |
| **5 ARTIFACT_DLOPEN** (`:318`/`:327`/`:532`) | a manifest artifact (or route-a ART at `:318`, or an owner's initial closure load at `:327`) failed its own `dlopen`; `detail` carries the `dlerror`, `index` the artifact | sub-case by `dlerror`: (a) a missing `NEEDED` not in `shared_sonames`; (b) a private-namespace search-path gap; (c) route-a ART not preloaded by host | (a) **U10 shared_sonames add** (verified: policy `621caec4`, libstdc++ `504b66cea`): add the missing soname to `kBridgeSharedSonames`; (b) extend the runtime-CL namespace search path (`[B8-NATIVE]` path `/system/android/lib64:/system/lib64/platformsdk:/system/lib64/chipset-sdk:/system/lib64/chipset-sdk-sp`); (c) host preloads ART before the sealed child (`n10b` sealed-owner preload + host callback permissions) | read `detail`/`index` → (a) one line in the policy `kBridgeSharedSonames` table (re-run the U10 policy gate + `abi_diff --calls`); (b) one entry in the ns search-path list; (c) host-side preload order | the specific gate for the chosen sub-fix: **(a)** U10 POLICY GATE PASS + closure proves a single resident provider for the added soname (the libjnigraphics lesson: do not add a name whose unique resident owner is unproven); **(b)/(c)** oracle = 1 each, controls lit |

## Decision logic (how to read the probe → pick the row)
1. `branch 4` → delete the emit gate (`:373-378`); nothing else. Trivial, always correct.
2. `branch 1` or `2` or `3` → **all three collapse to the same fix**: move owner publication into `WLSCPL_OpenPreparedNamespace` (host callback returns the resident sealed handle for the 2 canonical names) and drop the loader's `dlns_inherit`+NOLOAD-verify dance. Branch 1/2/3 only tell you *where* the inline Candidate-B flow broke; the single-owner callback removes all three failure points at once. This is the primary N11f landing.
3. `branch 5` → sub-case on `detail`: missing-NEEDED → `shared_sonames` add (U10 recipe); search-path → ns path entry; ART → host preload order. `index` names the artifact.

## Note on the dispatch's examples
- "**N3b 去 NOLOAD**" maps to branch 2 — but the verified lesson (N2 shim NOLOAD-only, `n10-bridge-owner`) is that
  removing NOLOAD is only safe **with** the host-callback dedupe; alone it reintroduces the double-load (branch-3
  symptom). So the table folds it into the single-owner callback fix rather than a bare flag deletion.
- "**U4 NAMESPACE-WALL**" — there is no `u4-sweep` namespace-wall artifact on this Mac (`2026-09-30-u4-sweep/` is a
  J6N4 predictions/scoring dir). The verified namespace donors used above are `n11-single-owner` (host-callback
  resident handle, oracle `c2508ebdd`) and `n10-bridge-owner` Candidate B (`B-owner-inherit.diff`, real-work
  `be16148da` `WLSCPL_InheritAndroidRuntimeV1`). If the outer ring means a different "U4 NAMESPACE-WALL" artifact, point
  me at it and I will swap the branch-1/3 donor citation.

## Hand-off
- N11f is **only** scheduled after an N11e window actually prints a `branch=`. Until then this table is the plan, not a
  change. The dominant outcome (branch 1/2/3) is one host-callback edit in `WLSCPL_OpenPreparedNamespace` +
  loader-block deletion — a single-file-replace-with-rollback, co-built host+loader, single-owner oracle at the gate.
- Evidence: loader `benchmark/2026-10-01-n11e-result-channel/src/sealed_child_provider_loader.c` (branch lines);
  `n11-single-owner/README.md` (master `c2508ebdd`, musl `dynlink.c:2408-2448/:2572`); `n10-bridge-owner/README.md` +
  `drafts/B-owner-inherit.diff` (Candidate B, N2 shim `0x1971b0`/`b94f69e4`/`42b5f71b8`, runtime `216b68fb`);
  U10 policy `621caec4` / libstdc++ `504b66cea`; host callback `sealed_child_provider_loader.h:102`
  (`WLSCPL_OpenPreparedNamespace`, `child_services.open_sealed_exact`).
