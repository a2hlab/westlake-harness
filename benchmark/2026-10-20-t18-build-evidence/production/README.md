# T18 frozen production inputs and execution archive

The earlier source-only evidence did not provide a whole-bridge production link. This packet preserves that earlier state and separately binds the newly frozen production work. It never presents newly executed logs as historical producing logs.

The unified archive contains:

- 60 exact source/review/spec/recipe files from MAIN source-only `4bfd621299`, peer `7c0423ddcc`, and producer production `9b3cd6cbc` commits.
- All 82 earlier indexed raw records, the owner first build, all named T18 peer directories and host-check records, including failures.
- The complete baseline-mac-01, audio-baseline-mac-01, production-01 and production-02 attempts, peer instruction/disassembly review receipts and other frozen production records.
- **720 actual pinned input files**, 212,209,670 bytes, stored under relative `input-bundle/INPUTS/` and `input-bundle/SDK/` roots. These include original objects/libraries, owner source/headers and exact clang++, ld.lld, llvm-readelf and llvm-objdump bytes. Symlinked tool inputs are stored as regular exact files with source modes preserved.
- All **607 actual includes**: 605 original pinned inputs plus the two generated production-02 source/include files. No dependency is represented only by a filename without its bytes.
- The existing original `out-touch21/fd/bridge15/artifacts.json` and `out-ability38/native-stack/artifacts.json`, stored separately from the new executions.

Both production attempts contain baseline SHA `d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b` and candidate SHA `dca530eb4b1b53e5dd0ecc41c36953f7463609c5b70bbdf67a49dc3cae17f9d9`. Actual frozen/compile/link/readelf stage receipts are rc 0. The unchanged owner recompile differs from the old object in 38 non-ALLOC .comment bytes; the original object is retained, not replaced in the baseline claim. Static exports/needed comparison and the reviewed A53 thunk exception remain the producer's scoped evidence, not runtime validation.

This closes the incremental relink input archive, **not** source rebuilding of every historical bridge object. Runtime registration, audio output and video playback are unverified by this package. No device operation, build or test rerun was performed by the archive lane.

The archive extraction note maps INPUTS and SDK to the relative roots. The original `build.py --inputs "$INPUTS" --sdk "$SDK" --out "$NEW_OUT" --execute` entry remains the recipe, used with the frozen source in the repository checkout. The compiler binaries require their compatible host OS/system libraries; this archive does not claim cross-host portability. `check_frozen.py --git` still needs the original repository git history. The archive contains gate/registry snapshots as context, not a replacement git object store. Relocated extraction was not rebuilt by this lane.

The local tar has 1,057 members, 89,989,108 bytes, SHA256 `c6d4f34f8af201d12bb8e53000fe58eec6043d5f6197e36bfe608691e943305b`. Each member's bytes and SHA were read back, and sources were rechecked for changes during packaging. The tar, full member index and the three prepared remote argv are in `.private/archive-01/`; large raw and binaries are excluded from the public whitelist. Outer performs remote upload and verification, then a separate success sidecar can be appended. The pending receipt is not rewritten.

`packet/execution-receipts-index.json` binds actual command/log/rc originals without publishing their user paths or large output. `api-public-refs.json` provides stable public links. The initial preparation packet remains unchanged. `package.py` is explicit-write, local-only; it neither invokes build commands nor uploads.
