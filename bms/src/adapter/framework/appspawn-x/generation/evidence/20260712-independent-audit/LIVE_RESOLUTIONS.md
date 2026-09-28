# Live-source resolutions after the immutable audit

The immutable audit report and its frozen-generation facts are not rewritten.
This file records fixes made in the current source tree that require a new
intentional `import_inputs.sh --refresh` generation before they become target
artifact evidence.

## `adler32_combine`

- Audit finding: frozen `libart.so` directly imports the old simplified
  implementation, which ignored `len2` and was not zlib-compatible.
- Live fix: `bionic_compat/src/sync_builtins.c` now implements the exact zlib
  combine algebra, including negative-length rejection and modulus handling.
- Frozen references: project-local AOSP and OH zlib `adler32.c` copies plus
  SHA provenance under `adapter/frozen/references/zlib-adler32/`.
- Regression:
  `adapter/framework/appspawn-x/bionic_compat/tests/run_adler32_regression.sh`
  passes known vectors, concatenation equivalence, negative length and modulus
  boundary cases.
- Evidence level: `host_test_pass / live_source`; the old generation remains
  failed for this item until rebuilt and rescanned.

## Same-generation production config

- Live canonical config now uses ARM64 cache/library paths and disables
  FAST_DEV, CheckJNI and unconditional startup verbosity.
- The producer now freezes, emits, hashes and verifies `appspawn_x.cfg` as a
  same-generation deployable artifact.
- Regression:
  `python3 adapter/framework/appspawn-x/tests/test_production_config.py` passes.
- Evidence level: `host_test_pass / live_source`; the old generation has no
  config artifact and is intentionally stale.

## `android_set_abort_message`

- Audit finding: exact `libunity.so` and `libil2cpp.so` directly import the old
  truncated process buffer/stderr implementation.
- Live fix: a separate `abort_message_compat.cpp` now preserves AOSP's
  first-message-wins behavior, null-message normalization, 128-bit magic and
  mmap layout. It does not expose a Bionic/C++ object across the Musl boundary.
- Frozen references and SHA provenance are under
  `adapter/frozen/references/aosp-bionic-abort-message/`.
- Regression:
  `adapter/framework/appspawn-x/bionic_compat/tests/run_abort_message_regression.sh`
  passes first-wins, null and exact magic/layout checks.
- Evidence level: `host_test_pass / live_source`; target producer refresh and
  recursive crash-tool integration remain pending.

## `_Z15ErrorCodeStringi` (`ErrorCodeString`)

- Audit finding: the old live tree had two competing C++ ABI owners: the real
  AOSP `libziparchive.so` and a handwritten `misc_compat.cpp` fallback with
  incompatible `-2..-14` strings. `art_runtime_stubs.cpp` also exported an
  accidental plain-C `ErrorCodeString`, while the deprecated `minizip.cpp`
  carried a third incompatible source definition.
- Live fix: all three compat/stub definitions are removed. The sole product
  owner is the full AOSP `system/libziparchive/zip_error.cpp` translation unit.
  ARM32 now builds that provider before `libartbase`; both ARM32 and ARM64 keep
  an explicit direct `libartbase.so -> libziparchive.so` edge and artifact
  smoke gates enforce one mangled owner, zero compat/stub owners.
- Producer policy: `minizip.cpp` is marked deprecated/not-a-provider and is
  denied by the generation importer, container producer and verifier. The
  verifier also rejects both `_Z15ErrorCodeStringi` and plain
  `ErrorCodeString` in `libbionic_compat.so`.
- Frozen reference: the byte-locked AOSP `zip_error.cpp` / `zip_error.h` under
  `adapter/frozen/references/aosp-libziparchive-error/` is the semantic oracle.
- Regression:
  `adapter/framework/appspawn-x/bionic_compat/tests/run_error_code_string_regression.sh`
  passes all 15 canonical codes plus three unknown-code cases, static ARM32 /
  ARM64 producer-order and denylist gates, and two deterministic AArch64 target
  builds proving the direct `DT_NEEDED` edge and unique symbol owner.
- Evidence level: `host_semantics_pass / target_elf_pass / live_source`. The
  currently frozen generation and pre-existing `adapter/out/aosp_lib{,64}`
  binaries predate this source correction and remain stale; product activation
  is not claimed until a complete recursive provider generation is rebuilt and
  rescanned.
