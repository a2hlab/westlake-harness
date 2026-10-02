# U14 reject-item adversarial pre-review (cc-wiki audits cc-t3's items; outer signs)

#90, offline, no board. Pre-review of `master 579e0bc072 benchmark/2026-10-03-u14-final-assembly/needs-outer-review.json`
— 45 findings (N1×44 + N2×1, all gate-disposition **REJECT**) + 4 native static deltas. Per-item approve/reject
**recommendation** with evidence; the outer signs. (`review-table.json` is the machine-readable table;
`evidence/proofs.txt` the concrete proofs. native_abi will swap to v2 (+`_ctype_`) and the issue IDs will re-hash —
reviewed by content, not hash.)

## The one principle
Every REJECT here is a **static-scanner false-positive**: `dlns_inherit` shared-soname edges and `RTLD_NOLOAD`
handles are invisible to a static NEEDED/dlopen resolver, so it conservatively rejects. At runtime the inherit edge
(single parent copy) and NOLOAD (handle to an already-mapped lib) are both safe and single-copy. The reviewer's job is
to supply the dynamic edge the checker can't see. Net: **0 genuinely-new unreviewed namespace/target**.

## ① N1 dlopen findings [0], [39]–[43] → APPROVE (RTLD_NOLOAD singletons)
All primaries are `RTLD_NOW|RTLD_NOLOAD` — a handle **only if the lib is already mapped** in the caller's namespace;
it cannot create a fresh namespace or load a new copy. Targets are always-resident route-A singletons:
`liboh_android_runtime.so` (appspawn-x/OHEnvironment init), `liboh_adapter_bridge.so` (OHEnvironment static-init,
before hwui RenderThread), `libEGL.so` (hwui RenderThread). The two `RTLD_NOW` fallbacks ([0] runtime, [42] libEGL)
are **idempotent** (dlopen of an already-mapped lib returns the same handle, refcount++ — no second copy); [41] is
explicitly "never load a second bridge copy; reach the one the shared runtime depends on". Every failure path is
graceful (`LOGE`/stderr/no-op), never a crash. These are new U14 source (input-channel reg; Flutter EGL interposer)
but the dlopen-a-resident-singleton-via-NOLOAD idiom is the established route-A pattern — so: **source-coverage
new-addition, behavior safe**; namespace = caller-default, target = resident singleton, failure = graceful
(per-item in `review-table.json`).

## ① N1 m6-jni-cache [1]–[38] → APPROVE (bridge-own JNI + ordinary calls)
- **[1]–[4]** `GetStaticMethodID`/`GetMethodID` resolve against the bridge's **own** cached `jclass`
  (`bridgeClass_` / `adapter_bridge_load_class`, `adapter.activity.*`) — standard JNI identical to deployed
  `84695d62`, not a namespace/library target. The scanner marked them "unknown" only because it can't statically
  trace a runtime `jclass` variable.
- **[5]–[38]** (34 "unresolved_calls") are a flat list of ordinary symbols — `ALOG*`/`__android_log_print`,
  `Call*Method`/`Get*Field`/`DeleteLocalRef`/`Exception*`/`NewStringUTF` (JNI), `c_str`/`lock` (std),
  `va_start`/`va_end`, `clock_gettime`/`getenv`/`strtoll` (libc), and bridge helpers
  (`GetBundleName`/`GetElement`/`SetRequestedOrientation`/`UpdateSessionPropertyByAction`/…). **None is a dlopen or
  namespace crossing.** They are the expected call set of the reviewed M6 JNI-cache (orientation/ability); the kinds
  already exist in deployed `84695d62` → behavior unchanged.

## ② N2 Flutter libandroid `fff9` NEEDED `libc++.so` → APPROVE (gate false-positive)
Deployed `ee2fb82c` NEEDED = `{liboh_android_runtime, libsurface.z, libc}` (no libc++ — static); candidate `fff9`
**adds `libc++.so`** because the EGL interposer uses `std::mutex` + `std::unordered_map` (dynamic libc++ replacing
the former static link). **Who provides it:** the `flutter_private` domain `dlns_inherit`s `libc++.so` from **both**
`default` (system_owner) and `westlake.sealed.child` (runtime_owner) — `westlake_stock_host_main.c:267` & `:270`. So
the NEEDED resolves to the **single** platform/runtime libc++ via the inherit edge. **Double copy: no** — no libc++
in `westlake_flutter/` and no local dlopen; it reuses the one resident instance (same pattern as
`liboh_android_runtime`/`libbionic_compat`). The gate's `inherit_used:false`+REJECT is the static resolver not
modelling `dlns_inherit` edges (same class as the ICU `errno=2` ns-invisibility). **Condition:** holds iff the U14
host (`f19b4a49`) keeps `libc++.so` in those inherit lists — cross-checked below (host delta = 0 call-set change →
lists intact).

## ③ Four native static deltas → all EXPECTED (promote to allowance)
| artifact | delta | verdict | why |
|---|---|---|---|
| bridge `liboh_adapter_bridge.so` | `87ed7281` (7daa5435 vs 84695d62) | EXPECTED | the **same** `preload_libmali_global` dlopen (NOW\|GLOBAL, caller-default); only its path-string `adr` immediate shifted `-135412→-135984` (Δ-572) from the M5/M6 `.rodata` reorder. Zero behavior change — reviewed M5/M6. |
| host appspawn-x | `f19b4a49` | EXPECTED | README: 8→8 dlopen, 17→17 edges, 0 INHERIT-REPEAT, 0 call-set change = the reviewed Wall-1 app-ns public-libs inherit; retains the flutter libc++ inherit (N2 condition holds). |
| Flutter `libandroid.so` | `592491ea` (fff9 vs ee2fb82c) | EXPECTED | the +7 EGL-interposer dlopens (= [39]–[43]); reviewed cc-t3 `822dbf198f`. Paired with N2 (same interposer's STL use adds the libc++ NEEDED). |
| Gecko native ABI | `05ff6c8b` | EXPECTED | README: 0→2 dlopen, +10 exports, one `__emutls_unregister_key` = the reviewed native_abi patch. **Note:** native_abi → v2 (+`_ctype_`) re-hashes this delta + issue_id; re-review by shape, not hash. |

## Recommendation
Promote the whole reject-set to the static allowance / new-native-admissions table (outer signs): 45/45 findings are
static false-positives (NOLOAD singletons, bridge-own JNI, ordinary libc/JNI symbols, inherit-provided libc++), and
4/4 static deltas are expected consequences of already-reviewed patches. The only standing **condition** is N2's:
the U14 host must carry `libc++.so` in the `flutter_private` `dlns_inherit` lists (verified present; host delta is a
no-op on call-sets).

## Files
- `review-table.json` — per-item approve/reject + evidence (machine-readable).
- `evidence/proofs.txt` — NEEDED diffs (ee2fb82c vs fff9), the host libc++ inherit lines, the bridge adr-shift delta,
  the NOLOAD-singleton analysis.
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; no board; no push. Recommendation only — the outer signs approve/reject and edits the registries.
Sources read read-only: `westlake-harness/benchmark/2026-10-03-u14-final-assembly` (findings + static deltas + host
source), the deployed/candidate Flutter libandroid (`westlake-harness-bms`, `westlake-inputs/generations`).
