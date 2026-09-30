# Native post-build / predeploy gates N1 and N2

## What was wrong; evidence first

The accepted scanner replay did not gate a newly built native package. N4's JNI
cache ordering therefore reached hardware before rejection. A second blind spot
was treating a globally present or inherited SONAME as satisfying a private
domain's transitive DT_NEEDED.

The new rule is **candidate-bound static checks before device access**. The
scanner and its historical predictions are unchanged. No approved native
exceptions have been added, and this work does not claim deploy integration or
runtime success: cx-t0 owns the deploy_generation hook (see `HANDOFF.md`).

| Actual offline package replay | N1 result | N2 result | Exit |
| --- | --- | --- | ---: |
| N4, package manifest `1617080a6a42651016937816ee3c9900554c5326379e5cf635b08227a00744d8` | One real JNI-order finding plus 28 unresolved/unknown items | Not requested in this comparison | 1 |
| N4-order, package manifest `7bc02de79f989d48cedb1e5020df1be3b5cd58f6d2229df8f1a3f08cc4f5ffbe` | No known order/NOLOAD finding; **28 unknown/unresolved items still reject** | **26 blockers**: 15 missing edges, six unresolved effective-path inputs, five uncovered library directories | 1 |

The decisive N2 edge is:

```text
domain: westlake_flutter
requester: /system/android/lib64/westlake_flutter/libandroid.so
requester SHA256: ee2fb82c6351b1b8461ce214e8ef39c9b33731523f154f92137991afa0e26c45
DT_NEEDED: liboh_android_runtime.so
searched: /system/android/lib64/westlake_flutter/liboh_android_runtime.so
outside-domain candidate: /system/android/lib64/liboh_android_runtime.so
outside candidate SHA256: 216b68fbb3a40b5ac7a90b726f6d8184fa7cdba848ccde56c809abd400a660df
resolution: missing; inherit_used=false
```

`inputs/flutter_domain.inc:22` selects Flutter/native private roots; lines 30–32
construct search/permitted from the private root and runtime app paths. The
shared-name list contains the runtime, but is **not a search path** and is not
traversed. The owner loader's sealed SHA is
`eebd62f2e9107e7915745280d4de85d44e4106a589508d25fa5f867007b2473c`.

`current-gate.json`, `n4-gate.json`, `needed-replay.json`, `candidate-package.json`
and five SHA-named `readelf/*.txt` files retain the actual reader outputs and
input identities. The two declared private domains contain nine library paths,
deduplicated to five ELF byte identities; their 15 needed edges are all unresolved
in those domains. The other five packaged library directories are **reported
uncovered**, not silently counted as checked.

## Interface and outcomes

```bash
python3 scripts/lab/native_predeploy.py --package "$PACKAGE" \
  --inputs "$BUILD_INPUTS" --gate N1
python3 scripts/lab/native_predeploy.py --package "$PACKAGE" \
  --inputs "$BUILD_INPUTS" --gate all --readelf "$READELF"
```

- `--gate N1`: post-build source/DEX initialization check.
- `--gate N2`: private namespace dependency closure only.
- `--gate all` (default): both, before deployment's device interaction.
- **0 / PASS**: no unexcepted findings within the declared scope; not a device
  acceptance. **1 / REJECT**: at least one unexcepted wall or unknown coverage.
  **3 / INVALID**: missing/malformed/drifting input or tool failure. JSON is on
  stdout; the matching numeric status is `exit_code`.
- Missing inputs must not fall back to SHA-only checking. A nonzero result from
  either gate must stop promotion. Capture stdout directly, without piping away
  the checker's exit status.
- `native_predeploy.check_package(package_path, inputs_path, gate="all",
  exceptions=..., readelf=...)` returns the same JSON-compatible object for a
  repository-controlled caller. It never imports package-supplied code.

Python 3.10+ and an AArch64-capable `llvm-readelf` (or `--readelf readelf`) are
required for N2. N1 uses the existing B10 scanner and pre-extracted DEX evidence;
it does not need readelf or access a device. B10 must land first.

## Build-input sidecar contract

`inputs/native-gates.json` is a concrete current-package example. A producer
emits a **new sidecar after final package.json is sealed**, outside directories
that will be mounted on the device. Do not put the sidecar's own package SHA into
`package.json.files`: that would create a hash cycle. Keep source/config snapshots
with the sidecar in durable storage, and retain both package and sidecar SHA in
the build receipt.

The top-level fields are `schema_version: 1`, `package_manifest_sha256`,
`initialization` and `namespaces`. File references use `{path, sha256}`, with
relative paths contained in the input directory; symlinks/escapes are invalid.

### N1 inputs

`initialization.manifest` points to a schema-1 `scan_native_initialization`
manifest; `initialization.dex_artifact` points to the sealed package JAR.
Require at least one namespace profile and one JNI-order profile. Each profile
identity names the **current** package manifest SHA and native artifact path/SHA.
The native artifacts must be AArch64 ELF files; the DEX evidence's `jar_sha256`
must equal the packaged JAR's hash. Sources, DEX input and the scanner manifest
are hash-checked; an empty namespace source is invalid.

Both scanner `findings` and `unknown` rows reject, as do `unresolved_calls`.
Thus N4-order fixing one known ordering wall does not convert its bounded source
slice into complete native-init coverage. Producers must supply the missing
closure or obtain precise reviewed exceptions, not omit profile classes.

Source-to-ELF correspondence is a **build-producer attestation**, not something
hashing alone proves. The producer must emit these bindings from its actual
compile/link inputs. The gate proves identity consistency and analyzes the
provided source/DEX; it is not a C++ compiler, binary equivalence checker or
complete call-graph verifier.

### N2 inputs

`namespaces.manifest` references the effective-domain JSON. Its `config_sources`
list pins the actual configuration source snapshots. `namespaces.owner_artifact`
pins the native loader/host whose build used them. Each domain supplies:

- `name`: unique domain/application-profile identity.
- `library_dirs`: directories whose directly contained `.so` / `.so.*` libraries
  must be scanned, after package mounts take effect.
- `search_paths`: ordered effective absolute lookup directories.
- `permitted_paths`: absolute allowed prefixes, compared by path components.
- `unresolved_paths`: any unevaluated runtime expressions; each is a blocker.

These are **effective build/deployment inputs**, not automatic parsing of arbitrary
C/C++ configuration. Do not invent global search paths to make a replay pass.
The archived current manifest explicitly leaves app-path expressions unresolved.
For app-specific domains, the producer emits each intended effective profile or
retains an unknown; no static claim covers unrepresented runtime-generated domains.

The virtual filesystem follows the package's ordered mounts, including later
single-file overrides. All sealed file hashes are checked. Extra unsealed files
under a directory mount reject. Every packaged library directory must occur in
at least one domain; omissions reject rather than silently reducing scope.
`namespaces.system_files` may add SHA-pinned, relative-path platform snapshots
with an absolute `target`; they cannot shadow a packaged target.

For each declared root, N2 runs `readelf -d --wide`, requires ELF64 little-endian
AArch64, follows dependencies recursively **within the originating domain**, and
handles cycles without dropping edges. A basename resolves only through search
directories and permitted paths; a permitted directory alone does not become a
search directory. Absolute NEEDED entries must be permitted. Global filename
matches are reported only as outside-domain evidence. `inherit` is never used.
RPATH/RUNPATH and relative-path NEEDED forms currently reject as unsupported,
rather than silently changing lookup semantics. Symbol versions, exports and
runtime already-loaded object selection remain separate gates.

## Exceptions

The repository-owned `knowledge/gates/native-predeploy-exceptions.json` is empty.
Each future entry must contain `gate`, exact `issue_id`, `package_manifest_sha256`,
`inputs_sha256`, `reason`, repository-relative `evidence`, `removal_condition`,
`approved_by` and `approved_at`. An issue ID hashes the complete finding and those
input identities. Wildcards, duplicate exceptions and incomplete approval fields
reject. A changed package or sidecar does not inherit the old waiver.

An excepted row remains visible as `EXCEPTED`; unexcepted rows remain `REJECT`.
Matching exceptions whose findings disappear emit `warnings[].status: STALE`
and require review/removal. Malformed inputs and tool errors are **not waivable**.
The default exception path is repository-owned; deploy must not accept an
arbitrary package-supplied checker or exception registry.

## Reproduction and verification

```bash
python3 scripts/lab/native_predeploy_tests.py
CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER=/usr/bin/cc \
  cargo test --manifest-path tools/spec-checks/Cargo.toml --test native_predeploy
python3 scripts/lab/native_predeploy.py \
  --package "$WORKSPACES/westlake-generation-n4-order-216b68fb" \
  --inputs benchmark/2026-10-01-native-predeploy-gates/inputs/native-gates.json
# Expected: exit 1, including the Flutter edge and all remaining unknowns.
python3 scripts/lab/native_predeploy.py \
  --package "$WORKSPACES/westlake-generation-n4-1617080a" \
  --inputs benchmark/2026-10-01-native-predeploy-gates/inputs/n4-native-gates.json \
  --gate N1
# Expected: exit 1, including the real cache-before-registration finding.
```

`collect.py --package ... --inputs ... --out NEW_DIRECTORY` captures a fresh
offline report and reader evidence; it requires a new output directory outside
the input tree. **Collector success is not gate PASS**: its stdout includes the
actual `gate_exit`. `capture.json` records reader/code hashes. Unit tests replay
the archived outputs without needing the real packages, and also run the real
ELF reader on constructed AArch64 ELF filesystem fixtures.

Verification: **19 Python tests pass**, six Rust integration selectors pass,
both contracts have three passing lifecycle/explain scenarios with zero skips.
Tests include bad/corrected ordering, package/source/DEX drift, exact exceptions,
STALE, missing domains, nested dependencies, cycles, outside-domain decoys,
permitted-prefix boundaries, mount replacement, unsealed additions, wrong ELF
architecture, malformed reader output and missing readelf. Detailed receipts are
in `results.json` and `validation/`. No runtime build, device command or push.

The pinned master export used for B10 landing, plus this gate delivery, also
passes the **regression wrapper**: 60 passed / nine failed / nine excepted /
zero unexpected, wrapper exit 0. Those exceptions are the seven old master
entries and **two pending B10 proposals**, not native waivers. The real native
candidate gate still correctly returns 1. Do not confuse the regression suite's
expected-negative tests with approval of the current package.
