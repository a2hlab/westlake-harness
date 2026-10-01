# U10 native symbol shims: verified partial delivery

## What was wrong

The three requested symbols are not three absent implementations. Deployed
`libbionic_compat.so` (`aa7e77f943ab4edd791590ca6b739120249b1ad6eb40e1ece7710ba206742a08`)
already exports the real first-message-wins `android_set_abort_message`. Meet's
private namespace cannot see that owner; creating another owner would duplicate
abort state without repairing visibility. The absent entries are
`__gnu_strerror_r` and `android_dlopen_ext`.

PPSSPP does **not** pass null extension info. Its two calls at `0x10b3ef8` and
`0x10b405c` pass `0x200` and `0x210`. Correction to the earlier interpretation:
the pinned NDK header defines `USE_LIBRARY_FD=0x10`, `FORCE_LOAD=0x40`, and
`USE_NAMESPACE=0x200`; `0x210` therefore means namespace plus library-FD loading,
not force loading. Ordinary `dlopen` cannot truthfully implement those requests.

## Source and binary identity

- Thirty historical compat inputs match the ROUTE_A_INPUTS receipt **30/30**.
  Their exact snapshot is `baseline/`; identity is recorded in
  `baseline-inputs.json`. Source: `$WORKSPACES/_cc-wiki-b1-src`, not the nearby
  23-match/2-different/5-missing trees. The receipt records the source closure.
- Existing abort owner is retained byte-for-byte as source. Its real-work donor
  last change is `d29f52fe75fb353f33f1a6e0b7162de19fc7e49e`; the AOSP14 comparison
  is `bionic/libc/bionic/android_set_abort_message.cpp:71`.
- GNU buffer-return and errno-preservation semantics are copied from
  AOSP14 `bionic/libc/bionic/strerror.cpp:205`. The local POSIX implementation
  supplies messages; identical Bionic message text is not claimed. Frozen OH6.1
  libc disassembly independently shows truncation, NUL termination and no write
  for capacity zero; it is a reference, not a fresh U8 board identity check.
- Transparent loader dispatch and original caller forwarding come from AOSP14
  `bionic/libdl/libdl.cpp:135`. No real namespace loader backend was found in the
  supplied local trees. The added fail-closed fallback is our code, not a copied
  linker implementation. LP64 layout comes from the separately pinned NDK23
  header, not an invented AOSP14 header copy. All source hashes and evidence
  hashes are in `provenance.json` and `evidence/sources.json`.
- Docker was unavailable under the sandbox. The pinned native OHOS clang15 SDK
  rebuild uses SDK headers rather than the historical forced `libcxx_compat.h`.
  Compiler/toolchain/link-input hashes and portable commands are in
  `evidence/build-receipt.json`. This is **not byte-identical** to deployed AA7.
  The required ABI and common-function call-set equivalence gates pass; those
  are not assertions of instruction-by-instruction semantic equivalence.

| Binary | SHA256 |
| --- | --- |
| Rebuilt baseline | `96da765adaf75839269e42720346196d149c66ffc315f911deb618357ad9e236` |
| Candidate | `015aa3a632eabe057bd8d6ce0e0ff181209da7dcab8de22409a79addc0a56d58` |

The local binaries are retained under this directory's ignored `.artifacts/`.
The delivery contains all thirty baseline sources, overlay sources, pinned
build inputs, build script and replay script. Before a board window, cx-t0 must
copy the exact candidate to persistent U10 staging and record its destination
and SHA. Do not strip it after gating: stripping hidden function boundaries
caused `abi_diff --calls` to attribute a hidden `__errno` tail call to the
preceding exported fdsan function. The delivered **unstripped** ELF passes
without changing the ABI tool or filtering any differences.

## Implemented behavior and limits

| Entry | Behavior | Repair claim |
| --- | --- | --- |
| `android_set_abort_message` | Original mutex/mmap/magic/atomic owner; first message wins, null becomes `(null)` | Preserved, **Meet visibility not repaired** |
| `__gnu_strerror_r` | Calls POSIX `strerror_r`, returns caller buffer, restores errno, including truncation/unknown/zero capacity | Missing GNU ABI implemented; Mozilla SIGKILL sender still unknown |
| `android_dlopen_ext` | Passes filename/flags/extinfo/original caller to a real weak backend if present | Backend dispatch implemented, **PPSSPP not repaired** |
| Backend absent | Null/zero extinfo uses real `dlopen`; nonzero flags log `[U10-DLEXT]`, return NULL and ENOTSUP without loading anything | Explicit unsupported result; no fabricated success or namespace conversion |

The AArch64 ordinary path restores caller LR and **tail-branches** to `dlopen`;
the backend path forwards that caller in x3. `evidence/candidate-dlext.asm`
records both. The backend is WEAK/UND, not a new required loader dependency.
Unsupported extension requests do not synthesize a `dlerror` string; ENOTSUP
plus the explicit marker is the partial contract, not full Bionic linker error
semantics. The original ordinary loader retains its real `dlerror` behavior.
New symbols are unversioned, like this compat's existing exports; consumer
`@LIBC` lookup/version acceptance still requires target integration validation.
No namespace bypass or opaque Android-to-OH namespace cast is implemented.

## Offline gates

| Comparison | Exports old/new | Removed | Added | Drift | Consumer breaks | Common call differences |
| --- | --- | --- | --- | --- | --- | --- |
| AA7 vs rebuilt baseline | 48/48 | 0 | 0 | 0 | 0 | 0 |
| AA7 vs candidate | 48/50 | 0 | 2 exact entries | 0 | 0 across 12 DSOs | 0 |

The twelve DSOs are SHA-bound to four original APKs in `consumers.json`, not
renamed generic fixtures. Consumer break zero means **no regression of existing
exports**, not resolution of all imports, namespace visibility, UI or audio.
`gate.py` checks JSON fields explicitly because ABI tool exit zero alone does
not reject every call difference or removed export.

Final focused replay: Python **10/10**, Rust **3/3**, contract **4 scenarios +
boundary passed**, land preflight **exit 0**. An extra archived-master overlay
check at `db31fbb5ec435356d5756f64fc5ed096389b7a2e` has 82 known-answer tests
(3 skips), zero path violations, but **spec_checks exit 1**: 197 passing tests,
9 approved exceptions and one unrelated `native_landing_registry` failure.
That HEAD does not contain its required
`benchmark/2026-10-01-u9-native/rollout/approved-j10g/production-dry-run.json`;
the selector independently fails before any U10 evidence is considered. It was
reported to outer, not waived or repaired here. `validation.json` separates
these historical results. After outer repaired the missing receipt at
`441e41ca3`, an archive of master `28589ef4912f9387c7817db8bc98c4cc56ce54fa`
with the first delivery overlaid passed: **spec_checks exit 0**, 198 passing,
9 approved exceptions, zero unexpected failures; path gate exit 0. The raw
Cargo exit remains 101 because approved exceptions are not successful tests.

Host behavior fixtures execute on Darwin with its POSIX `strerror_r`, separately
from cross-compiling the target ELF. They cover known/unknown errors, all buffer
capacities 0..64 with canaries and concurrent errno; real abort ownership/magic,
null and concurrent later writes; no-backend refusal without `dlopen`; real
ordinary shared-library loading and real loader errors; exact backend args and
return-address provenance. Non-Darwin host fixtures explicitly skip, never
claim target execution. The evidence checks and gate mutation tests still run.

```bash
export PATH="$(brew --prefix llvm)/bin:$PATH"
DIR=benchmark/2026-10-01-u10-native-shims
OLD="$WORKSPACES/westlake-generation-u8-j9-t7e/native/payload/android/lib64/libbionic_compat.so"
python3 "$DIR/build.py" --old "$OLD" \
  --link-inputs "$WORKSPACES/westlake-inputs/oh61-link-inputs/system-lib64" \
  --out "$DIR/.artifacts"
python3 "$DIR/verify.py" --old "$OLD" --build-dir "$DIR/.artifacts" \
  --abi-tool "$WORKSPACES/westlake-harness/scripts/lab/abi_diff.py" --out /tmp/u10-replay
python3 "$DIR/gate.py" "$DIR/evidence/baseline-abi.json" "$DIR/evidence/candidate-abi.json"
python3 "$DIR/test_shims.py"
cargo test --manifest-path tools/spec-checks/Cargo.toml --test u10_native_shims
python3 "$WORKSPACES/westlake-harness/scripts/lab/land.py" "$PWD" \
  "$DIR/landing-paths.txt" -m x --preflight
```

## Integration, not board authorization

This replaces only the existing compat owner, not libc or the linker. cx-t0
must preserve one abort owner, expose that owner to Meet's exact private closure
without broad namespace inheritance, and prove target consumer lookup. Those
configuration changes are **not** part of this delivered binary. PPSSPP remains
unsupported unless an actual compatible backend is supplied and separately
validated; never pass its namespace object to ordinary `dlopen`.

`offline-precheck.json` includes independent confirm/refute criteria and requires
artifact identity plus both native gates on the **assembled** U10 package. It is
a handoff fragment, not a runnable plan or authorization. No board was touched.

## Expanded U10 policy and resident visibility

The final outer scope authorizes three independently gated components:
compat, policy and host. OpenSLES is deferred to U11 and does not block U10.
`composition.json` is the handoff authority: **complete authorized offline
handoff, not an assembled rollout-ready package**.

| Component | Old / new exports | Baseline calls | Candidate calls |
| --- | --- | --- | --- |
| Compat | 48 / 50; two exact new entries | 0 | 0 common functions; 12 consumer breaks 0 |
| `libnativeloader.so` | 7 / 7; no additions/removals/drift | 0 | Only `CreateClassLoaderNamespace` and `OpenNativeLibrary`: `OwnPolicy<6>` becomes `<7>` |
| `appspawn-x` | 15 / 15; no additions/removals/drift | 0 | Only `StockCreateConfiguredNamespaces` adds `U10ShareResidentCompat`; no removed callees |

The policy JSON adds **only `libstdc++.so`**; its baked header mirrors that edge.
The unchanged ANL backend is not the baked policy consumer. Both payload copies
of `libstdc++.so` are `7e06cd8b…`, but bridge search roots select only
`/system/android/lib64/libstdc++.so`, not the nested `westlake_native` copy.
166/166 SHA-matched APKs contain zero bundled arm64 `libstdc++.so` members.
That count excludes external/split sidecars and does not prove runtime lookup.
`inventory_std.py` and `evidence/std-inventory.json` retain every key, not just
the aggregate. The root provider and old components are identified against
the signed expected map and strict no-diff U9 summary; the first use of the
summary alone produced UNKNOWN and was immediately corrected on the board.

Stock-host source identity required a second correction: the supplied 450-input
receipt still names R8's main, which omits the current package routing. Its first
baseline replay removed six callees. The actual retained main is
`westlake-harness-bms-deploy/benchmark/2026-09-30-n4-native/src/westlake_stock_host_main.c`
SHA `7fe4369d…`; the N11 baseline receipt reproduces current host `1d3b0881…`.
`build_host.py` pins that receipt and every reused host object, changes only the
main object, and obtains zero baseline call differences. This is a controlled
relink, **not** a fresh rebuild of every host object. It preserves historical
generation macros only for comparison; cx-t0 must regenerate final U10 identities.

`visibility/stock-host.patch` and `visibility/resident-compat.h` inherit just the
resident compat into app domains. All handle probes use `RTLD_NOLOAD`, and
setter/getter/GNU addresses must agree between resident and app views. If an
already-mapped default view has the same three addresses, prefer its direct
edge over a potentially two-hop sealed-view edge; a distinct default state is
rejected, never loaded or selected. Missing
namespace, missing object, inheritance failure, wrong view or missing GNU entry
refuses without any loading fallback. The AArch64 compiled helper uses mode 6
(`RTLD_NOW|RTLD_NOLOAD`), captured in `evidence/resident-target.asm`.
The sealed namespace is a **lookup view**, not proof of the underlying physical
mapping owner. Final target lookup/maps must show one abort state. **Meet and
fd-plus** are candidate beneficiaries; neither is declared repaired offline.

The available local comparison binaries are SHA-bound in `composition.json`.
Do not install the comparison host with historical generation macros. Apply the
source patch and header, regenerate closure/plugin identities, then repeat all
ABI/call and native predeploy gates on cx-t0's assembled candidate.

## OpenSLES is deferred to U11, not stubbed

The exact OH ELF has 140 exports but only 46 public OpenSL entries. Its IID
layout is 24 bytes and GetState writes eight bytes (`0x13a88: str x8,[x1]`),
whereas Android's caller supplies sixteen-byte IIDs/four-byte scalar outputs.
Direct forwarding by function-pointer cast is rejected even if slCreateEngine
itself ignores option arrays. `opensles/README.md` records the decision, full
inventory and typed conversion work required. Outer supplied nearest 6.0-Release
and master sources as structural references only, not matching OH 6.1 sources.
Pending task t3 preserves future U11 engine-forwarding/canary acceptance criteria;
it is not an implemented U10 gate. No facade or failure stub is delivered, and Mindustry is
**not** counted repaired.

```bash
export PATH="$(brew --prefix llvm)/bin:$PATH"
DIR=benchmark/2026-10-01-u10-native-shims
python3 "$DIR/build_loader.py" \
  --native-payload "$WORKSPACES/westlake-generation-u9-j10g-238ffc14/native/payload/android/lib64" \
  --link-inputs "$WORKSPACES/westlake-inputs/oh61-link-inputs/system-lib64" \
  --out "$PWD/$DIR/.artifacts/loader"
python3 "$DIR/build_host.py" --out "$PWD/$DIR/.artifacts/host"
python3 "$DIR/policy_gate.py" "$DIR/evidence/policy-baseline-abi.json" "$DIR/evidence/policy-candidate-abi.json"
python3 "$DIR/host_gate.py" "$DIR/evidence/host-baseline-abi.json" "$DIR/evidence/host-candidate-abi.json"
python3 "$DIR/test_visibility_policy.py"
```

The JSON gates above replay checked-in evidence. After rebuilding, rerun the
canonical `abi_diff.py --calls --json` against the signed U9 components (plus
`--consumer` libart for NativeLoader), then gate those fresh reports. Passing old
reports does not certify a changed artifact. `validation.json` separates first
delivery, expanded component tests, contract checks and full archived-master runs.
