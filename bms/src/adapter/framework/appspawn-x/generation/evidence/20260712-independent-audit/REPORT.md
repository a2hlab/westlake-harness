# Frozen same-generation producer — independent audit (2026-07-12)

## Verdict

The producer's narrow `build_pass` claim is proven: two independent rebuilds
from the same frozen closure emitted byte-identical appspawn-x / compat /
wrapper artifacts, and an independent ELF parser confirmed their identities,
dynamic tags, dependency order and main-ELF PT_TLS shape.

This generation is **not deployable** for the CardWords first-frame goal.  The
address reservation is not a Bionic slot-5 semantic implementation; the six
compat sources contain existing stub/fake/default behavior whose absence from
the first-frame call closure is not proven; and the compiled appspawn still has
fail-open sandbox/AccessToken/security behavior.  No device claim is made.

Status label: `build_pass`, not `real_impl`, not `device_verified`.

## Boundary and scope

- Boundaries reviewed: appspawn-x, Permission/Security, Bionic/Musl.
- App: frozen unmodified CardWords APK and four frozen ARM64 Unity DSOs.
- Host-only audit; 5EAB5 was not read or written.
- This audit did not modify the producer or target artifacts.  It added only
  independent audit/scanner evidence under this directory.

## Principal findings

### P1 — Frozen target producer and two-build determinism are proven

- The frozen closure contains exactly 2,638 regular files; every file is in
  `frozen.sha256` and `provenance.tsv`, and every local hash equals its recorded
  copied-origin hash.
- `frozen.sha256` SHA256:
  `b3dc1bff5afcf7d564f5df30feac1832a010fc59cc9ee37df197bebe810906ac`.
- Two independent executions of
  `adapter/framework/appspawn-x/generation/build_generation.sh` produced
  identical `artifacts.sha256`, `build-result.env`, compile/link command trace,
  verifier stdout and empty verifier stderr.  The captured evidence is in
  `rebuild-1/` and `rebuild-2/`.
- Final compile/link commands contain no `/opt`, `16.12`, HanBing origin or
  parent-relative path.  The container was read-only, network-disabled and
  mounted only project-local frozen inputs, work and artifact directories.
- Qualification limit: the linux/amd64 tool-runtime image is identity-pinned
  (`sha256:76236b...6797`) but its OCI bytes are not archived under this
  project.  Origin-tree non-consumption is proven; reconstruction from the
  project tree on a fresh host alone is not.

### P2 — Exact artifact identities and ELF contracts are proven

| Artifact | SHA256 | sha1 Build-ID | Independently proven contract |
|---|---|---|---|
| `appspawn-x` | `417f3f38d4ee24e32f6322e04b07a197285c7271c7e19005369740507916754a` | `66e4ea35bd2e3923b59775ac5eb46305e8bc1b17` | AArch64 ET_DYN PIE; interpreter `/lib/ld-musl-aarch64.so.1`; no RPATH/RUNPATH/TEXTREL; exactly one PT_TLS with `filesz=0`, `memsz=48`, `align=16`; same-ID sidecar has one 48-byte STT_TLS reservation at module offset zero. |
| `libwestlake_hap_domain_wrapper.so` | `f5ce5d50972e7a293ad4d0c5b31120dee227913b96a7d7ddc95ed94b860551a7` | `007c6462ffdf5c01a9906d46b8a2492a9ca2f6c1` | SONAME exact; NEEDED exactly `libhap_restorecon.z.so`, `libc++.so`; no RPATH/RUNPATH/TEXTREL; C export exists; linked undefined stock `HapContext::HapDomainSetcontext`; wrapper source returns that stock call and contains no procattr bypass. |
| `libbionic_compat.so` | `6c4e41b22d412c1487f73ca2d1d3d0725426e5b60c870849cd5cca8d210d11e5` | `c2208a6221e6e0325ca96316502ab078ec6912c2` | Exactly six admitted source files; no `bionic_tls_abi`, Unity pthread/signal box, `pthread_create` import/definition, or executable `MRS TPIDR_EL0`; no RPATH/RUNPATH/TEXTREL. |

The appspawn child contains the exact wrapper path
`/system/lib64/libwestlake_hap_domain_wrapper.so`, exact Build-ID pin and
fail-closed `dlopen` / Build-ID / `dlsym` checks.  A Build-ID is a generation
identity pin, not an authenticated package signature.

The PT_TLS facts prove an ELF reservation, not the effective runtime TP
addresses.  Loader allocator provenance, recursive initial closure and
prepare-before-slot-use remain separate gates.

### F1 — The six-source compat artifact contains 37 stub/fake/default/partial symbols

The current README has now withdrawn the earlier inaccurate “none
participates” wording.  The following is the complete source-level inventory
used by this audit.  Line numbers refer to the exact frozen source bytes (which
match the project source used to create this generation).

| Source | Symbol and source line | Classification | Observed direct undefined consumer |
|---|---|---|---|
| `system_properties.cpp` | `__system_property_foreach` :104 | success without enumeration | current non-final app candidate `libcutils.so` |
|  | `add_sysprop_change_callback` :117 | registration stored but never dispatched | none observed; non-use not proven |
| `malloc_compat.cpp` | `android_mallopt` :9 | selected operations return success without effect; others unsupported | none observed; non-use not proven |
|  | `android_mallopt_get_caller_info` :28 | empty result stub | none observed; non-use not proven |
| `fdsan_stubs.cpp` | `android_fdsan_get_error_level` :8 | fixed disabled default | none observed; non-use not proven |
|  | `android_fdsan_set_error_level` :12 | no-op + disabled default | none observed; non-use not proven |
|  | `android_fdsan_exchange_owner_tag` :18 | no-op | none observed; non-use not proven |
|  | `android_fdsan_get_owner_tag` :24 | fixed zero default | none observed; non-use not proven |
|  | `android_fdsan_close_with_tag` :29 | closes FD but ignores tag | none observed; non-use not proven |
| `misc_compat.cpp` | `android_reset_stack_guards` :16 | entropy read, but fixed canary on failure | none observed directly; dynamic/call use not proven |
|  | `android_set_abort_message` :35 | process-global buffer + child stderr, not Android abort-message plumbing | exact guest roots `libil2cpp.so`, `libunity.so` |
|  | `android_get_abort_message` :43 | process-global buffer partial | none observed; non-use not proven |
|  | `_Z15ErrorCodeStringi` (`ErrorCodeString`) :49 | handwritten default mapping | current non-final app candidates `libandroidfw.so`, `libartbase.so` |
|  | `android_dlwarning` :73 | no-op | none observed; non-use not proven |
| `liblog_android_supplement.cpp` | `__android_log_security` :33 | fixed zero | none observed; non-use not proven |
|  | `android_logger_list_alloc` :49; `android_logger_list_alloc_time` :58; `android_logger_open` :74 | fake handles with no logd source | none observed; non-use not proven |
|  | `android_logger_list_read` :82 | fixed EOF | none observed; non-use not proven |
|  | `android_logger_get_log_size` :87; `android_logger_get_log_readable_size` :89 | fixed zero | none observed; non-use not proven |
|  | `android_logger_set_log_size` :88; `android_logger_clear` :92 | fake success | none observed; non-use not proven |
|  | `android_logger_get_log_version` :90 | fixed version 4 | none observed; non-use not proven |
|  | `create_android_logger` :104; `android_log_destroy` :111 | fake event context lifecycle | none observed; non-use not proven |
|  | `android_log_write_int32` :121; `android_log_write_int64` :122; `android_log_write_float32` :123; `android_log_write_string8` :124; `android_log_write_string8_len` :125; `android_log_write_list_begin` :126; `android_log_write_list_end` :127; `android_log_write_list` :128 | success while dropping the event | none observed; non-use not proven |
|  | `android_log_read_next` :131; `android_log_parser_read_next` :132 | fixed end-of-list | none observed; non-use not proven |
| `sync_builtins.c` | `adler32_combine` :68 | knowingly simplified, ignores `len2`, not zlib semantics | final frozen initial snapshot `libart.so`; also current app candidate `libart.so` |

This table does not classify the other exported functions in the six sources
as stubs.  In particular, the system-property get/set path maps to OH
parameters, fdsan close really closes the FD (while skipping ownership), and
the CAS/fence/memcmp16/adler32 functions have concrete implementations.

### F2 — Static consumer closure already disproves “no stub participates”

The project-local consumer scanner produced these facts:

- Immutable initial snapshot currently frozen by the closure task: 15 ELFs,
  not yet certified as a complete recursive closure. `libart.so` directly
  imports the incorrect `adler32_combine` provider. Seven initial modules also
  import `dlopen` and/or `dlsym` (12 resolver imports counted by symbol), so
  dynamic symbol use is `NOT_PROVEN`.
- Exact four CardWords guest roots: `libil2cpp.so` and `libunity.so` directly
  import the partial `android_set_abort_message`. `libmain.so`, `libil2cpp.so`
  and `libunity.so` import both `dlopen` and `dlsym`; their recursive runtime
  dependency closure is not frozen, so every other compat stub remains
  `NOT_PROVEN`, not “unused”.
- There is no immutable final ARM64 app-runtime closure in this generation.
  A broad current-output candidate scan observed direct imports of
  `__system_property_foreach`, `ErrorCodeString` and `adler32_combine`, plus
  dynamic resolvers. It is evidence of risk only, not a final closure proof.
  The current `adapter/out/adapter/liboh_android_runtime.so` candidate is ARM32
  and therefore cannot be admitted to an ARM64 CardWords product closure.

Absence of a direct undefined reference is never promoted to first-frame
non-use. The only acceptable exemption is a complete frozen recursive closure
plus direct/indirect/dynamic call evidence proving the symbol unreachable
before the first-frame receipt.

### F3 — Production security gate fails independently of TLS layout

- `ChildMain::applySandbox()` returns success while performing no sandbox
  operation (`child_main.cpp`:319-358).
- `SpawnServer::initSecurity()` logs SELinux and AccessToken “stub initialized”
  and returns success (`spawn_server.cpp`:85-129).
- Missing/zero AccessToken returns success, and a failed `SetSelfTokenID()` also
  returns success (`child_main.cpp`:587-602).
- Missing APL silently becomes `normal` (`child_main.cpp`:473-477).
- `android_reset_stack_guards()` installs a fixed canary if entropy cannot be
  read (`misc_compat.cpp`:16-28), violating the fail-closed security rule.

These facts do not invalidate the build determinism proof. They do invalidate
production-init + SELinux-Enforcing deployment eligibility and cannot be
accepted as “first-frame-unused” behavior without separate proof.

### N1 — Current live verifier has moved after the frozen generation

The artifact generation used frozen verifier SHA256
`2c0106017873cae5350e02b1cccf34e1fe6616ca4d69289a3f761c461715a269`.
The current live verifier now has SHA256
`93e20ababdb8cbd7abe4bb577601e5ed583ddb773469b722624b616bf38b8ff0`
because it adds `NOT_PROVEN first_frame_stub_call_closure`. This is a correct
fail-closed clarification and does not change the target ELFs, but the current
worktree producer and the already frozen generation are no longer byte-identical.
The next intentional generation must import/refresh this verifier before its
evidence can claim current-source reproduction.

## Proven / Not Proven / Failed / Next Evidence

| Proven | Not Proven | Failed | Next Evidence |
|---|---|---|---|
| 2,638-file frozen closure; two byte-identical rebuild manifests; exact SHA/Build-ID/NEEDED/SONAME/no-RPATH contracts; 48-byte PT_TLS reservation; exact wrapper stock call and pin; admitted six sources; no old TLS/pthread/signal boxes or TPIDR_EL0 in compat; no external origin-tree paths consumed by final target commands. | Effective runtime TP addresses; complete recursive initial/app/guest closure; dynamic `dlsym` targets; first-frame non-use of any of the 37 partial symbols; slot-5 semantic writer; wrapper authentication; fresh-host reproduction without the pinned Docker image; init+Enforcing; ActivityThread, Unity load, Surface/RS and visible frame. | Incorrect `adler32_combine` directly imported by final frozen `libart.so`; fixed-canary entropy fallback; fail-open appspawn sandbox/security/AccessToken; current live verifier differs from frozen verifier; no final immutable ARM64 app-runtime closure. | 1) Finish and bind the initial-closure report to this immutable snapshot. 2) Replace `adler32_combine` with real zlib semantics or prove it unreachable before first frame and explicitly stub it (real implementation is preferred because it is already an initial consumer). 3) Freeze the complete ARM64 app/runtime closure and resolve its architecture. 4) Run a dynamic-call-aware first-frame closure proof; keep every unclosed symbol NOT_PROVEN. 5) Implement the reviewed slot-5 READY publisher and fail-closed security path, then create a new frozen generation before any device deployment. |

## Reproduction

```sh
# Producer was run twice; evidence was copied after each completed build.
adapter/framework/appspawn-x/generation/build_generation.sh

# Independent ELF/provenance/determinism audit (does not import producer verifier).
python3 adapter/framework/appspawn-x/generation/evidence/20260712-independent-audit/independent_audit.py

# Static consumers. The current initial snapshot is intentionally not marked
# complete; app output is explicitly a non-final candidate; guest roots are
# exact but not a recursive runtime closure.
python3 adapter/framework/appspawn-x/generation/evidence/20260712-independent-audit/scan_compat_stub_consumers.py --summary \
  --initial-root adapter/research/atoms/L03/A15/evidence/runs/20260712-initial-closure-cert-r1/frozen/rootfs \
  --app-candidate-root adapter/out/aosp_lib64 \
  --app-candidate-root adapter/out/adapter/libapp_native_loader.so \
  --app-candidate-root adapter/out/adapter/liboh_adapter_bridge.so \
  --app-candidate-root adapter/out/adapter/liboh_android_runtime.so \
  --app-candidate-root adapter/out/adapter/liboh_hwui_shim.so \
  --guest-root adapter/frozen/product_inputs/cardwords-current/canonical/lib/arm64-v8a/libmain.so \
  --guest-root adapter/frozen/product_inputs/cardwords-current/canonical/lib/arm64-v8a/libil2cpp.so \
  --guest-root adapter/frozen/product_inputs/cardwords-current/canonical/lib/arm64-v8a/libunity.so \
  --guest-root adapter/frozen/product_inputs/cardwords-current/canonical/lib/arm64-v8a/lib_burst_generated.so
```

## Design consistency gate

- ART/class_linker/vtable changed: no.
- Android Framework/BCP/ActivityThread semantics changed: no.
- Fix location: adapter-owned appspawn/Bionic-Musl boundary, consistent.
- Boot 27-segment continuity required by this change: no libart/BCP bytes were
  rebuilt here; the frozen libart is a link/runtime dependency only.
- Truly cold device verification: absent, explicitly not proven.
- Stub gate: failed for deployment until the first-frame call closure is closed
  or real implementations replace the participating stubs.

