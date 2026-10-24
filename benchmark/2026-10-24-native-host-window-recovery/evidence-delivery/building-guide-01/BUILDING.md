# Building the native host-recovery bridge candidate (`3291f76d…`): what was actually done

This page is documentation of **recorded** build commands. It is not a build script, and nothing here was executed for this page (no compiler, linker, network or device). Facts are taken only from six inputs whose SHA-256 are listed in [results.json](results.json):
- the t5 spec;
- `evidence-delivery/inventory-01/{README.md,results.json}`;
- `candidate-build-02/{README.md,recipe-delta.json}`;
- `candidate-build-01/recipe.sanitized.json`.

**Scope: five translation units were compiled from source and linked with reused baseline objects. This is not a whole-bridge source rebuild.**

## Output
`liboh_adapter_bridge.so`, SHA-256 `3291f76db0945f90b402ea61b14c3a912efbeecec9e0422af1a92fec95b8a819`, 2,154,616 bytes. The recorded receipts span 2026-10-24 13:50:36–13:50:58 +08:00, and all six report rc0. Snapshot01 `158c1740…` predates the C1 fix and is historical.

## Path aliases (literal substitutions)
| Alias | Meaning |
|---|---|
| `$MAIN` | `$WORKSPACES/westlake-harness` (main checkout) |
| `$T4` | `$WORKSPACES/westlake-harness-t4` |
| `$STAGE` | `$T4/benchmark/2026-10-24-wmc-build-preparation/staging-01/.private/staged-03` (staged toolchain, SDK, headers, baseline objects; **local private**) |
| `$SNAPSHOT02` | `$HOME/.local/share/westlake/native-host-recovery-build-20261024/snapshot-02` (sources, raw argv, receipts, objects, output; **local private**) |
| `$VM_HOME` | home directory of the Linux VM user (personal path redacted in the records) |

## Required inputs
1. **Candidate sources (in git).** There are 13 candidate and reader source/licence files; they match the snapshot02 pins and main HEAD bytes, against review02 manifest `f156d990…`. The five compiled units are:
   - `oh_window_manager_client.cpp` (wmc)
   - `oh_input_bridge.cpp` (input)
   - `session_stage_adapter.cpp` (stage)
   - `session_recovery.cpp` (core)
   - `host_window_record_reader.cpp` (reader-build)
2. **OH SDK and toolchain (local private, under `$STAGE`).**
   - Linux `clang-15`/`lld` live in `$STAGE/inputs/ORB_WS/toolchains/ohos-sdk/native/llvm/bin/`.
   - The SDK manifest has 8042 entries, all checked (`$T4/.../staging-01/.private/sdk-files.json`, `8912158b…`).
3. **System headers (local private).** 792 restored system headers, manifest `$HOME/.local/share/westlake/wmc-baseline-build-20261024/linux-original-compile-02/system-headers-source.json` (`00049b63…`). Input/stage source closure: 452 entries (`$MAIN/benchmark/2026-10-24-wmc-build-preparation/source-binding-02/file-closure.json`, `2fd97b81…`).
4. **Reused link inputs (local private).** The link command names 113 explicit files, including the compiler driver. Of these, 103 are unchanged staged baseline inputs that match the baseline pins; they are reused as-is, and this chain does not rebuild them from source. Index: `$MAIN/benchmark/2026-10-24-wmc-build-preparation/link-inputs.json` (`233f90e2…`).
5. **Mac link tools (local private).**
   - `$STAGE/mac-tools/clang++` (`6a5ec844…`) and `$STAGE/mac-tools/ld.lld` (`489c6d66…`).
   - Three copied dylibs: `$STAGE/lib/libc++.1.dylib`, `libc++abi.1.dylib`, `libxml2.2.14.0.dylib`.

## Recorded commands and where they live
**Compile (×5), Linux.**
- Executed through `orbctl run -m a2hlab` (the OrbStack Linux VM).
- A small Python launcher reads `argv.json` and runs it with `cwd=$SNAPSHOT02/<unit>`, environment `PATH=/usr/bin:/bin HOME=$VM_HOME LANG=C LC_ALL=C`, and a 120 s timeout. The transport argv is recorded in `recipe-delta.json`.
- The compiler is `$STAGE/inputs/ORB_WS/toolchains/ohos-sdk/native/llvm/bin/clang++` with `--target=aarch64-linux-ohos`, the SDK sysroot, `-std=c++17`, `-fPIC -O2`, `-MMD/-MF`, `-c <unit>.cpp -o <unit>.o`.
- Argument counts: wmc 388, input 391, stage 388, core 388, reader-build 388.

**Link (×1), Mac.**
- `$STAGE/mac-tools/clang++ --target=aarch64-linux-ohos -fuse-ld=lld -nostdlib -shared …`
- `cwd=$SNAPSHOT02/link-01`, environment `PATH=/usr/bin:/bin HOME=$HOME LANG=C LC_ALL=C`, 126 arguments.
- The five new objects each appear exactly once in the link command.

**Where the exact argv is:**
- **Private originals:** `$SNAPSHOT02/{wmc,input,stage,core,reader-build,link-01}/argv.json` together with `receipt.json`, `stdout`, `stderr`. Each raw argv SHA is in `recipe-delta.json`.
- **Public reconstruction:**
  - `$MAIN/benchmark/2026-10-24-native-host-window-recovery/candidate-build-01/recipe.sanitized.json` (`1269c57a…`) holds the snapshot01 argv arrays;
  - `candidate-build-02/recipe-delta.json` (`689e2faa…`) holds indexed edits that reproduce the snapshot02 argv exactly (`exact_delta_reconstruction_pass: true` for all six), applied in reverse index order.
  - Both are receipts, **not executors**. The recipe notes require a new output tree for any future replay.

## Is the public repository alone sufficient?
**No.** The repository contains the candidate sources, the recipe and delta, and manifests/indexes with SHAs. It does not contain the bytes of the staged SDK and toolchain, the 792 system headers, the 103 reused baseline objects and libraries, the Mac link tools and dylibs, or the snapshot02 raw argv and receipts. Verified available copies are local private persistent copies under `$STAGE`, `$HOME/.local/share/westlake/...` and `$T4`; off-host replication has not been checked.

## Preconditions and known gaps for reproduction
- **Private bytes:** a reproducer needs the private `$STAGE` closure and the `$SNAPSHOT02` tree. Off-host replication of snapshot02 is **unknown**; it was not checked.
- **Host requirements:** compiles require a Linux environment equivalent to the recorded OrbStack VM `a2hlab`; the link requires a macOS host that can run the staged `clang++`/`ld.lld` with the three dylibs. Full host-OS provenance was not audited.
- **Reused objects:** the 103 reused objects cannot be regenerated from this chain. A whole-bridge source rebuild is a separate, unrecorded procedure.
- **Dependency coverage:** `-MMD` dependency files are not a complete system-header inventory. The SDK and system-header manifests are separate checks.
- **Archive fallback:** a local archive is available at `$MAIN-t4/benchmark/2026-10-20-t18-build-evidence/source-closure/.private/archive-02/window.tar.gz` (`922e0291…`, 84,089,815 bytes). It was not extracted, and its sufficiency for a rebuild is not established here.
- **Optional tool:** `$STAGE/mac-tools/llvm-readelf` is not staged. No recorded command uses it, so it is not a build gap.
- **Missing inputs:** none. All six inputs for this page were present and matched their SHAs.

Nothing here claims device loading, a white-screen fix, an API freeze, a seal or remote publication. t5 final remains pending.
