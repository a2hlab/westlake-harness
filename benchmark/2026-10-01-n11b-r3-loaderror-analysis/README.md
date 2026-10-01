# N11b R3 (61b) LOAD_ERROR:10 — offline pin from the capture hilog: `libartbased.so` unresolved in `westlake.sealed.child`

Assisting #80 while the N11c-probe window is still queued (after U9 sign-off). cx-t0's R3 window
(`westlake-harness-u7-executor/benchmark/2026-10-01-n11b-early-owner/window-r3/board61b/capture/hilog.txt`, 18 MB)
recorded `WLCGATE:LSP:LOAD_ERROR:10` + `VALIDATED_COUNT:26` for child PID **6203** but, per cx-t0, N11b's loader has
no per-library logging so the failing lib was `unknown`. The MUSL dynamic linker, however, logged the failing
library on its own channel in the same capture. This pins the probable cause offline; the N11c-probe
(`open_local_now` index/path/`null`/`dlerror`) remains the authoritative confirmation.

## Timeline for PID 6203 (sole sealed-namespace load failure)
```
18:04:53.322  WLCGATE:LSP:ENTER → PASS_PRECONDITION → PASS_MANIFEST → PASS_PID
18:04:53.320  MUSL-LDSO: load libsecurity_component_client_enhance.z.so failed, namespace=default / ndk, errno=2   <- BEFORE LSP:ENTER, ndk ns = SecCompEnhanceAdapter optional init, non-fatal
18:04:53.341  MUSL-LDSO: load libartbased.so failed, namespace=default no inherits, errno=2
18:04:53.341  MUSL-LDSO: load libartbased.so failed, namespace=westlake.sealed.child, errno=2   <- the SEALED loader's namespace
18:04:53.341  MUSL-LDSO: dlopen_impl load library header failed for libartbased.so
18:04:53.720  OH_JNI_Bridge: preload libmali.so.0 -> RTLD_GLOBAL OK                               (loader got far; many libs loaded)
18:04:53.740  WLCGATE:LSP:LOAD_ERROR:10 → RESULT_ERROR:10 → VALIDATED_COUNT:26 → FAIL_LOAD_RESULT → RAC:FAIL_SEALED_PROVIDER
```
PID 6203 has exactly **two** MUSL-LDSO hard failures in its whole life: the SecComp one (ndk ns, before the gate,
optional) and **`libartbased.so`** — and `libartbased.so` is the only one that fails in the
**`westlake.sealed.child`** namespace, i.e. the namespace the sealed provider loader uses. `errno=2` = ENOENT.

## Why this is the LOAD_ERROR:10
- `LOAD_ERROR:10` = the sealed loader's `open_local_now` callback returned NULL for an order entry
  (`sealed_child_provider_loader.c`; `LoadWithOps` inlined). `VALIDATED_COUNT:26` is the total order count, not a
  success count (per cx-t0).
- `libartbased.so` fails to resolve in both `default` and `westlake.sealed.child` namespaces → a `dlopen` of the
  artifact that DT_NEEDs it returns NULL → `LOAD_ERROR:10`. The loader had already loaded other libs successfully
  (bridge `libmali.so.0` preload OK at .720), consistent with one NEEDED failing mid-pass and the error being
  reported at the end of the pass (.740).
- `libartbased.so` is **absent from 61b** (`find /system -name libartbased.so` → empty;
  `/system/android/lib64/libartbased.so` → No such file) and from the U8 payload. So it is an unprovisioned /
  unresolvable DT_NEEDED in the sealed-child namespace, not a shipped artifact.

## Caveats / what the N11c-probe must confirm
- This is a correlation from the MUSL-LDSO channel, not the loader's own per-index log. The probe will confirm
  **which `order[]` index / absolute path** returned NULL and that its `dlerror()` names `libartbased.so`
  (expected text: `Error loading shared library libartbased.so: No such file or directory`).
- Open question for the fix: is `libartbased.so` a DT_NEEDED of a sealed artifact that U8 resolves but N11b does
  not (namespace search-path / provisioning regression in the early-owner path), or newly required by N11b? U8
  passes `WLCGATE:LSP` (board 6557), so U8 either does not need `libartbased.so` in the sealed child or resolves it
  — the delta to chase. (The SecComp `ndk`-ns failure is present on U8 too and is a red herring, like the SIGILL
  sigchain noise the outer ring already flagged, board 6571.)

## REGRESSION vs provisioning — answered: REGRESSION in N11b's sealed loader
`libartbased.so` is a **host AOSP build artifact**, not a device library:
`t7d-reproduction/before.json` records it as
`/home/alvin/aosp-14.0.0_r1-art/out/host/linux-x86/lib64/libartbased.so` (a linux-x86 host ART variant). It can
never load on the aarch64 device, so its `open_local_now` NULL has **always** happened on 61b — and was always
benign:
- **Working** controls2 helloworld run (61b, PID 22272, 07:25:52.850): identical
  `MUSL-LDSO: load libartbased.so failed … namespace=default / westlake.sealed.child, errno=2 … dlopen_impl header
  failed`, then `WLCGATE:LSP:PASS_LOAD_RESULT`. The U7/U8 sealed loader **tolerates** the unresolvable host NEEDED.
- **Failing** N11b R3 run (61b, PID 6203, 18:04:53.341): the same NULL → `WLCGATE:LSP:LOAD_ERROR:10 /
  FAIL_LOAD_RESULT`.

So the difference is **not** the library (same NULL in both; libartbased.so is never on-device by design) and
**not** provisioning (it is a host artifact, must not be shipped to the device). It is a **regression in N11b's
early-owner sealed-loader logic**: it now treats the long-tolerated `libartbased.so` NULL as fatal
(`LOAD_ERROR:10`), where U8 reaches `PASS_LOAD_RESULT`. `VALIDATED_COUNT:26` is the order total, unchanged; the
delta is the fatal/tolerate decision for an optional/unresolvable NEEDED.

**Fix direction:** restore U8's tolerance — the N11b sealed loader must not fatalize a NULL for a NEEDED that U8
treated as optional (e.g. host-only `libartbased.so`); or drop host-path artifacts from the fatal order. Do **not**
provision `libartbased.so` to the device (it is a linux-x86 host lib). N11c-probe will confirm by showing the NULL
is `libartbased.so` and that the loader's error path (not the library) changed; compare its per-index log against
a U8 `PASS_LOAD_RESULT` run.

## The exact fatal lines (U8 child loader vs N11b early-owner.patch) + the N11d minimal patch
`early-owner.patch` adds one block to `sealed_child_provider_loader.c`, inside the provider-load callback *after*
the valid provider `handle` is obtained (`dlopen_ns(&closure_namespace, absolute_path, flags)`, loader :271) and
after the pre-existing N10b sealed-owner preload (:280–305). U8/N10b then simply `return handle` (:343). N11b
inserts an **early-owner publish to the `default` namespace** and makes any failure **fatal**:
```
:313  if (dlns_inherit(&default_namespace, &closure_namespace,
                        "liboh_adapter_bridge.so:liboh_android_runtime.so") != 0) {
:315      (void)dlclose(handle);
:316      return NULL;                 <-- FATAL 1  -> open_local_now NULL -> WLCGATE:LSP:LOAD_ERROR:10
      }
:318  for (owner = 0U; owner < 2U; ++owner) {
:319      void *shared = dlopen_ns(&default_namespace, owner_paths[owner], RTLD_NOW|RTLD_LOCAL|RTLD_NOLOAD);
:321      if (shared == NULL || shared != jni_owner_handles[owner]) {
:322          if (shared != NULL) (void)dlclose(shared);
:323          (void)dlclose(handle);
:324          return NULL;             <-- FATAL 2  -> LOAD_ERROR:10
          }
      }
```
When the sealed closure cannot be fully re-resolved/verified in `default` — the `libartbased.so` host edge fails
`namespace=default no inherits` (seen in the R3 hilog) — `dlns_inherit` or the `RTLD_NOLOAD` owner check fails and
these two lines `dlclose(handle); return NULL;`. The caller records that NULL as `LOAD_ERROR:10`. U8 never ran
this block, so the same unresolved edge was harmless (`PASS_LOAD_RESULT`).

**N11d = log-only diagnostic probe** (`n11d-probe-early-owner.patch`, for cx-t0 to build). We do **not** yet know
whether R3 failed at `:315` (`dlns_inherit`) or `:321`/`:324` (`dlopen_ns` NOLOAD / handle-mismatch), so the patch
**does not change the judgment** — both branches still `dlclose(handle); return NULL;` (still fatal, still
`LOAD_ERROR:10`). It only adds a distinct `fprintf(stderr, …)` before each fatal return:
- branch 1: `[N11d-PROBE] branch=dlns_inherit names=… dlerror=<dlerror()|<none>>`
- branch 2: `[N11d-PROBE] branch=owner-verify owner=<owner_paths[owner]> shared=<%p> expected=<%p> dlerror=<…>`

`dlerror()` on branch 2 with `shared==NULL` should name the unresolved lib (expected: `libartbased.so`);
`shared!=expected` with no dlerror means a handle mismatch instead. The N11d window log then tells us which branch
fires, and only **then** do we write the success-path diff. Gate for cx-t0's build: `abi_diff --calls` vs the N11b
baseline shows only `WLSCPL_LoadSealedProvider` changing (adds `fprintf`), exports 2/2, drift 0, DT_NEEDED still
`libc.so` only.

**Success-path (DEFERRED — do not diff until the N11d probe log identifies the branch):** the direction below is
analysis only; the concrete owner-verify change waits on the branch evidence.

## Success-path: where libartbased.so comes from, and the gate (corrects the "it's in the sealed order" premise)
Traced it — **`libartbased.so` is NOT in the sealed order/manifest**, so there is no order entry to delete:
- `westlake-generation-n11b-child-u8-163da805/native/native-checks/scan-manifest.json`: `libartbased` absent
  (`has libartbased: False`). `package-manifest.json` / `native-gates.json` reference only the correct aarch64
  **`libartbase.so`** (e.g. `/system/lib64/westlake/route-a/<sha>/libartbase.so`).
- No payload/device ELF DT_NEEDs it: `libart.so` (route + android/lib64, all three N11b gens) NEEDs
  `libartbase.so` + `libartpalette.so` — never `libartbased.so`.
- It is the host **debug** ART variant (`libartbase` + `d`), present only in the AOSP `out/host/linux-x86/`
  build (before.json, alongside `libartd.so`/`libdexfiled.so` — the `*d` debug family). It is referenced by a
  device **/system** ART ELF (the `native-checks/system-elf/<sha>` blobs match the string) and probed at runtime
  (`libnativehelper.so` strings `libart.so` / `libartd.so` / `/apex/com.android.art/lib64/libartd.so` — AOSP's
  debug-variant selection). On the aarch64 device the debug variant is absent, so the probe fails `errno=2` on
  **every** 61b run and is benign on U8 (`PASS_LOAD_RESULT`). It is **not** a registered NOLOAD exception (the
  N10b/N11 NOLOAD rows in `native-predeploy-exceptions.json` are about the bridge/runtime owner `RTLD_NOLOAD`, not
  libartbased.so).

So the success-path fix is **not** "remove an order artifact". Two layers:
1. **Make the early-owner publish succeed instead of degrading** (so #80's single-owner is actually achieved, not
   just the N11d crash-avoidance): the owner-verify (`dlns_inherit` + `dlopen_ns(default, owner, RTLD_NOLOAD)` vs
   `jni_owner_handles[owner]`) must confirm the **owner handle identity** without requiring the owner's whole
   transitive closure to re-resolve in `default` — i.e. the benign unresolvable host-debug probe on the owner's
   closure must not make the `RTLD_NOLOAD` lookup return NULL. (Verify via handle equality of the already-loaded
   sealed owner; do not let a system-side debug-ART probe decide owner admission.) This keeps the early-owner
   optimization working on the normal path, so N11d's U8 fallback is a safety net, not the steady state.
2. **Register the known benign probe** so tolerance is deterministic (what U8 did implicitly): add
   `libartbased.so` (and the host `*d` debug ART variants) as an explicit NOLOAD/optional entry for the sealed
   child, so both the loader and the gate treat its NULL as allowed rather than incidental.

### Proposed gate (generalises the outer-ring ask)
The native gate already enforces **artifacts** are aarch64 (`native_needed_gate.py:51` / `native_gate_common.py:95`:
`e_machine != 183 → reject`). The gap that let a host-only NEEDED survive is that **DT_NEEDED sonames are only
recorded, never required to resolve to an aarch64 artifact in the sealed+system set**. Add, at generation:
> For every artifact in the sealed closure, every `DT_NEEDED` soname must resolve to an **aarch64 ELF
> (`EI_CLASS=ELFCLASS64`, `e_machine==EM_AARCH64 183`, == `manifest->elf_machine`)** present in the sealed+system
> artifact set, **or** be an explicitly-registered NOLOAD exception. Reject the generation if any NEEDED resolves
> only to a host (`out/host/`, linux-x86) path or is unresolvable and unregistered.

This catches the whole class (a host/x86 lib leaking in as a NEEDED), where the current artifact-only arch check
cannot, and forces host-debug probes like `libartbased.so` to be consciously registered rather than silently
unresolvable. Handoff: cx-t0/outer own the generation harness (`scripts/lab/generation_bundle.py`,
`native_needed_gate.py`); this writeup pins the hook (`ElfReader` already has the 183 check; extend it over the
NEEDED-resolution step).

## Source
Working-run evidence: `westlake-harness-u7-executor/benchmark/2026-10-01-u7-executor/board61b/runs/controls2/.../helloworld/hilog.txt`
line ~9373–9390 (`libartbased.so` fail → `PASS_LOAD_RESULT`); host-lib provenance:
`.../benchmark/2026-10-01-u7-executor/t7d-reproduction/before.json`.
Capture (not committed, 18 MB): `westlake-harness-u7-executor/benchmark/2026-10-01-n11b-early-owner/window-r3/board61b/capture/hilog.txt`
lines ~48499–48818 (PID 6203 LSP window). Loader: `westlake-harness/benchmark/2026-10-01-n11c-probe/src/sealed_child_provider_loader.c`.
