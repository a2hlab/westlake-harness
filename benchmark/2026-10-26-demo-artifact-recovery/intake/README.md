# T152 — worktree-independent demo artifact intake

**Declared runtime bytes complete; recorded native build inputs archived.** The independent HOME stage contains **10,510 files / 2,936,040,222 logical bytes (2.734 GiB)**, representing 8,573 unique SHA256 values. Every copied file was rehashed; no source inode is shared. This is neither a full current-device fingerprint verification nor a whole-board restore/rebuild claim.

## Ingest handoff

- Release ID: `61b-t150-3291-intake-20261026-02`.
- Stage: `$HOME/.local/share/westlake/artifact-recovery-intake-20261026/stage`.
- Manifest: the same root's `manifest.json`, schema `westlake-artifact-release/v1`, SHA256 `830301145f834557077f958d51eb7ca8d554cb69407b1037702cdd5c0d2a3402`. The public [manifest.json](manifest.json) is byte-identical and contains relative path/SHA256/size/integer mode/role only.
- Private source map, locator and relocation map: `private/source-map.json`, `private/intake-locator.json`, `private/build-relocation.json`. Original symlink relationships are in `private/materialized-links.json`; stage files are regular, materialized byte copies. Archive-file modes are not a claim of current deployment ownership/labels; historical deployment metadata is separately retained.
- Commercial APKs, raw build logs and historical absolute paths stay in private stage/storage. No application user-data directory was copied. The outer lane alone publishes remote CAS and tests empty-directory recovery; this lane performed neither.

## Independent required set and exact difference

[required-runtime.json](required-runtime.json) derives **711 required members** independently of collected files: the accepted 61b seal realization's own-host runtime and `/system/android/*` rows, its host HAP and two native namespace helpers, the T80 actual 40+1 file measurements, the T150 actual candidate mapping, and explicit b0e rollback. The 811-row seal's excluded targets are listed, not silently counted as recovered. This conservative historical subset is not a fresh exhaustive installation scan or a complete launcher/control configuration.

**711/711 members (1,191,395,337 bytes) are collected by exact SHA; required-minus-collected is empty.** The earlier missing `runtime/run.sh` was located by the outer lane in the original T59 capture, `$HOME/.local/share/westlake/61b-saved-wifi-feed-20261023/raw/07-runsh/run.sh.current`: 3038 bytes, SHA256 `47afe0b98df4f9bb261406cc04ca08b984ab0bd1b0850e7b7e8b1e6558ec511d`. Its independent provenance is `benchmark/2026-10-23-61b-saved-wifi-feed/t59-run-sh-exact-diff.json` (anchor SHA in results). The original bytes were copied and rehashed; no same-name substitute, regeneration or script execution occurred. Manifest revision 01 is retained privately; revision 02 adds this exact member.

Local CAS/worktree/HOME sources were searched first; bounded Orb and hw248 location checks followed. A single fresh boot query returned transport rc0 with body `[Fail][E001005] Device not found or connected`; collection stopped before any device fingerprint/file transfer. Raw error and command receipts are preserved under `logs/`. No device write occurred. The latest T150 pin establishes candidate3291, not every inherited historical dependency's present identity.

## Native build closure and relocation

The stage preserves snapshot02's five translation units, all five compiled objects, and actual five Linux compile rc0 plus Mac link rc0 argv/stdout/stderr/receipts. Candidate SHA is `3291f76db0945f90b402ea61b14c3a912efbeecec9e0422af1a92fec95b8a819`; rollback is `b0e5602a97133ebb1dca12972a8931a86528322685a211bb1a7a0a2185fefbd4`. Source and byte restoration are separate in [build-status.json](build-status.json).

Independent staged-byte comparisons matched **8,042 SDK entries, 792 libcxx headers, 658 non-system dependencies, 452 Input/stage closure entries, 113 explicit link files and seven required tool/runtime-library pins**. The often abbreviated “103 reused objects” are actually **46 `.o`, 56 `.so`, one `.a`**. They are preserved inputs, not 103 newly rebuilt translation units. The original baseline build receipts and T18 source archive are also copied. No new compilation/link was performed.

Relocation is explicit:

| Recorded alias | Restored stage-relative prefix |
|---|---|
| `$STAGE` | `build/staged-03` |
| `$SNAPSHOT02` | `build/snapshot-02` |
| Original build01 recipe and build02 delta/index | `build/indexes/candidate-build-01/`, `build/indexes/candidate-build-02/` |
| HAP source, compiler, original compile/release evidence | `build/hap/` |

The six exact argv arrays remain under `build/snapshot-02/<unit>/argv.json`; original absolute paths are historical evidence, not portable commands to execute unchanged. Use the private prefix map for input paths/cwd and put outputs in a fresh build directory. Preserve the semantics of file/debug/macro prefix mappings: Input's `__builtin_FILE` affects bytes. Linux compile and macOS link host requirements remain distinct. A relocated rebuild has not been executed or certified by this intake.

## Recovery versus source rebuild gaps

1. **Identity/restore validation:** no fresh complete current-board fingerprint, remote CAS publication, empty-directory restore or different-Mac test was performed here.
2. **Source reconstruction:** five-unit native compilation plus relink inputs are closed; whole-bridge regeneration of reused inputs, legacy runtime/JAR/boot baking and complete HAP signing/host dependencies are not established. HAP b189 exact JS/ABC, compiler and original build evidence are archived; signed-byte recovery does not require a new signing operation. Third-party APK source is not supplied.

Only files in [landing-paths.txt](landing-paths.txt) belong to this report. Copied specs/requirements and unrelated BMS changes are not included.

Verification limit: agent-spec lifecycle passed the explicit path boundary but skipped three scenarios because no verifier covered their steps. It is not reported as lifecycle acceptance. Byte/inventory checks are reported separately.
