# Bridge 84695d62: artifact recovered, exact build provenance still missing

The retained bridge is **not proved to be built from real-work HEAD**. Rebuilding that tree and calling it a one-function change would repeat the B9 bridge regression. The exact binary exists and is safe to recover; its complete source/object/link chain remains a known gap.

## Verified identity and history

Full SHA: `84695d62f515cfec6bb317c959ec55b1d5085bf82303f792a764cf549a22267a`.
The existing persistent archive was rehashed over SSH:
`hw248:/home/alvin/westlake-oh6.1-lab-state-20260930/vm-copies/bridge-84695d62/liboh_adapter_bridge.so`.
No binary was uploaded or changed. `remote-artifact-sha256.txt` records the readback.

The 2026-08-10 reference capture already identifies this binary. The later 2026-08-20 `m3-stage-ack-only` experiment uses it as a candidate and fails provider admission before lifecycle code. Thus the directory name does **not** date its build or establish a stage-ack patch. R155's 2026-08-27 identities then record the same binary. The 2026-08-20 workspace HEAD `0095fb7f` is explicitly **not** an artifact build claim in `IDENTITY.md`.

Small original receipts and source witnesses are archived in `evidence/`; `source-identities.json` records their source paths and hashes. Original real-work repository HEAD: `be16148da9ae7bb89c62e81e144ed0bceb5c4669`.

## Useful partial source, not an exact reconstruction

`real-work/src/adapter/sources/oh61-v7-b2133b5b/framework/window/jni/oh_anativewindow_shim.cpp` has the old `oh_anw_wrap_for_activity`, `ohTokenAddr`, per-producer `frameId` and `fn03_on_app_content_present` path seen in the retained binary. The current top-level window source instead uses a newer DirectSurfacePathTracker cohort. This frozen directory is the better starting point for future source recovery.

However its own provenance names historical HanBing/Yue paths, and the 2026-08-03 build record identifies **bc878f4f**, not 84695d62. The historical `/opt/10.Project/...` and `/opt/build-trees/adapter/...` roots are absent on the current hw248. Its recipe also takes package-manager sources outside the frozen directory. No complete object cohort, ordered link receipt, toolchain identity or patch set tied to 846 was found. The source excerpt and recipe are archived as **partial evidence**, not a deployable replacement.

Search covered the original Mac 00.Workspace, workspaces/00.Workspace and real-work receipts/history/snapshots; then VM westlake and historical bridge build directories; then hw248 `/home/alvin` artifact/source archives and bounded historical directory searches. This is not a claim to have exhaustively unpacked every remote tarball. The broad remote source lookup was stopped without results. We did not run a build, change a board, or patch the binary.

## Native gates ready for outer review

Use **commit `8829b1ad886de60361d5a5c905560796a3607e2f`** on branch `analysis/native-gate-master-landing`, worktree `westlake-harness-native-gate-landing`, based on master `7bd0060b5`. Exact paths: `native-gate-landing-paths.txt`. Cherry-pick that commit alone, not this lane's entire branch.

It wires deployment N1/N2 and freeze checks and imports the approved 257 A exceptions plus their U5 evidence. No N8 permanent exceptions, candidate binaries or temporary grants are included. Actual U5 dry-run accepts 131 baseline findings; N8 without its temporary grant rejects 185. Hook tests 10, artifact-freeze tests 6, exception table test 1, known-answer suite 82 (3 skips), source freeze 8 entries/30 checks/zero violations, lifecycle 3 pass. Full receipts are under `benchmark/2026-10-01-native-gate-landing/` in that commit. No push performed.
