# N10: one native batch on the signed U7 Java/image baseline

The old inference was that a source-shaped namespace change alone proved one bridge owner. It did not: the signed child must be identified and its retained recipe reproduced first. The other wrong shortcut was treating a library-presence donor as a complete API provider. Exact Unity imports reject that shortcut. This report ships an offline candidate, not a lighting verdict.

## Evidence and artifacts

`artifact_identity.py --expected evidence/u7-complete-expected.json` identifies the retained and packaged child as **DEPLOYED d240f8d2**. `sealed_child_provider_loader.c` is linked into **libwestlake_android_child.z.so**, not the runtime provider. Replaying its original compile/link commands reproduces the deployed child byte for byte. Replacing only `sealed_child_provider_loader.o` produces **63b6f8d4**, identical across two builds. See `child-inputs.json`, `child-build-receipt.json` and `evidence/child-artifact-identity.txt`.

| Member | Candidate SHA prefix | Change / preservation |
|---|---|---|
| child | 63b6f8d4 | Preload the bridge and runtime in the current owner before `CREATE_INHERIT_CURRENT` creates sealed.child; keep both handles for child lifetime |
| appspawn-x | 70c17f83 | N8 owner routing plus exact Jitsi package selection and resident Bionic publication |
| ANL | 8a807895 | N8 selection plus `org.jitsi.meet`; other app paths retain their prior behavior |
| Bionic compatibility | 2f03c576 | Real-work LIBC version node, including `android_set_abort_message`; Same N8 source bodies and .text, restored LIBC version node |
| runtime / ART / bridge | 216b68fb / 59e1bb45 / 84695d62 | Original bytes preserved |
| provider | 0509fe23 | Frozen original bytes preserved |

Host/ANL outputs repeat identically. After OrbStack was restarted, the Bionic build was rerun in **two new Docker output directories** (`bionic-resumed-3/4`), with identical output **2f03c576**. Its **.text bytes match N8 exactly**. The only changed allocated section apart from build-id is `.gnu.version`; nonallocated debug/symbol sections also differ. Nine copied C/C++ bodies retain their recorded N7 hashes. The temporary Mac relink prototype (653e4a75) is retained in separate `.mac.json` receipts and is not the final package. See `bionic-link-receipt.json` and `bionic-section-audit.json`.

Initial resumed attempts stopped before compilation because the container lacked the shared Git-object mount. Once the main checkout was mounted, the supported frozen `--git` check verified **30/30 pinned sources** inside the container. A direct source-root check of this worktree has **24 exact sources and 6 absent cross-branch inputs**, not zero violations; these missing files are not compiled here. `freeze-source-availability.json` records them, and no frozen source is edited.

## Donor decisions and predictions

Raw consumer ELF dumps are losslessly compressed in `evidence/*-elf.txt.gz`; their original hashes are in `evidence/elf-dump-index.json`.

The donor inventory is pinned to the U8 batch table in `donor-decisions.json`. Source paths/commits and SHA values are recorded there; byte identity is not promoted to a successful board repair.

* **N8 members:** reuse the signed N8 candidate artifacts and routes from `benchmark/2026-10-01-n7-native/` and `westlake-generation-n8-private-zlib` (manifest 3dd48299). This includes the six Flutter domains, browser domains, private zlib and route-owned EGL facade. Root `/system/android/lib64/libz.so` is absent. These are wall-movement candidates, not predictions of rendered UI.
* **Jitsi:** exact APK 72a89e53 / libc++_shared 3e852764 imports `android_set_abort_message@LIBC`. Copy real-work `src/adapter/framework/appspawn-x/bionic_compat/{src/abort_message_compat.cpp,bionic_compat.map}` at **be16148da9ae7bb89c62e81e144ed0bceb5c4669**. The function snapshot SHA is **15ad2e1c…**, unchanged in N10. Restore its version node and make the resident owner global only in the selected Jitsi domain. Predict this relocation wall moves; later imports and UI remain unknown.
* **OpenSLES:** retain N8's real platform `/system/lib64/libOpenSLES.so` owner route for Mindustry. It opens the original OH implementation and checks `slCreateEngine` plus four standard IIDs; the private Westlake ABI supplies Android extension IIDs. Westlake IID donor commit **532633da63b770d3d459c74683db6d7a1f82a022** and real-work historical owner-forwarding commit **be16148da…** are recorded. No renamed second engine is shipped. U7 already attempted a related publication and still failed: no claim of a solved engine wall before a device relocation check.
* **Bitmap:** exclude the 00.Workspace fixed-offset registration table at **f7373f9da9a978d436289f164c97587801a551f9**. U7 musicplayer logs already bind ColorSpace Rgb natives and Bitmap.nativeComputeColorSpace to libhwui; the old table does not repair this observed failure. Westlake's ImageDecoder null fallback is also not a Bitmap fix. The actual null color-space cause remains unknown; no unconditional sRGB substitute is added.
* **Unity:** exclude real-work mediandk-presence at **be16148da…**. The exact libunity 7290845f strongly imports AMediaCodec/AMediaExtractor/AMediaFormat APIs; the donor only exports provenance. A library-name shell cannot satisfy these imports. No error/null media stubs are added. The arm64 split actually audited is **68920637…**, recorded from app-input.json, not the stale manifest base-APK field.
* **Toutiao:** the original deployed ART 59e1bb45 emits nonzero `[IFACE-RAW]` pre-override BitVector diagnostics. A class-linker correction belongs in libart, outside this preserved-ART batch. The diagnostic is evidence of nonzero bits, not proof of the precise source cause. `bitvector-assessment.json` records the excluded repair; no toutiao wall movement is predicted.

## Packages and gates

Native package: `$WORKSPACES/westlake-generation-n10-63b6f8d4`, manifest **310376a18c6fc1952702d78366a7333644cbe11e3482901ff09ece4739d0bc71**.

Complete U7-preserving bundle: `$WORKSPACES/westlake-generation-n10-u7-310376a1`, bundle **bd6d402d6684fcad79fef456af623b75124bb73f0825914185c2e5b1b9c7856a**. Its **314 identities** comprise U7's 312 plus two private native files. All 27 images, stubs and J7b runtime JAR retain U7 bytes. Baseline fingerprints are **68b7fb016253 / 8fe2e5fd7d65**; candidate fingerprints are **0f54a443dbec / 8fe2e5fd7d65**. Do not directly use the old native directory-overlay deployer on U7: the bundle executor preserves Java/image layers.

Structural dry-run and fresh real image gates pass: G1 passes and G2 String.hashCode matches 36/36 instructions. Package checks have zero frozen violations; source Git checks and checkout availability are reported separately above. Production native preflight and dry-run **refuse**: **N1 31, N2 154, 0 excepted, 0 input errors**. Removing only recorded source-line offsets, their finding objects match N8's 185 findings exactly (no new bounded finding). This does not prove them harmless. `exception-proposal.json` binds all 185 to the new manifest and inputs SHA; it has **no approved_by**, cannot authorize deployment, and inherits no expired N8 grant. `rollout_ready=false`. The real production executor dry-run passes its image gates, then refuses at the native gate (exit2, device_io=false). After approval, fresh complete preflight remains required before apply.

## Executor recovery

`DeviceIO.verify` now allocates a fresh `verification-<uuid>` evidence directory for each call. Apply failure, automatic rollback and resumed verification retain separate captures/maps; no old evidence is removed. The stale settle-0.json regression passes (1/1), original executor tests pass (24/24), N10 checks pass (6/6), the repository known-answer suite passes (79 passed, 3 skipped), and lifecycle selects the real Rust crate with `--code tools/spec-checks` (4/4 pass). The initial `--code .` attempt skipped four scenarios and is not passing evidence.

Unrelated fake-Cargo fixture tests fail 3/3 on branch and have identical production/test source SHA to master; they were not changed. The whole-tree user-path scan reports one old untracked U7 landing patch containing a recorded hw248 path; this patch is not in N10 landing. A final landing-only path scan is recorded in user-paths.txt; build outputs are data receipts, not executable source. The broader static suite also has 50/52 passes: its installer inventory compares absolute worktree paths and its silent-skip fake-Cargo fixture returns0 unexpectedly. Those sources are unchanged. These failures are retained, not hidden as N10 passes.

## Review and proposed device window

Review the exact 185-entry proposal, then authorize one **<=30 minute** single-batch N10 window. After exact native approval, mark only the composed bundle `rollout_ready=true`, record its new bundle hash, and rerun the complete executor dry-run. The native manifest must retain the SHA approved by the table. Preserve U7 JAR/images; collect same-board U7 owner maps first. Apply the composed bundle using the trusted repository executor; verify all 314 hashes, parent/child views, one ART, one runtime and bridge owner each, and no unknown sessionId. Run HW/ZZ, then Wikipedia/fd-app/fd-shatteredpixeldungeon with t20 screenshots. Any control regression or new duplicate owner fails and restores the full U7 receipt. Jitsi/Mindustry are optional within remaining authorized time. Counts/screenshots are **unknown until record.json/facts and outer image review exist**. No board commands or locks were used in this offline delivery.
