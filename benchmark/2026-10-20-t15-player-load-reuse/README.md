# T15 proves the previously covered player load wall on 5cd

**Static reuse plan only. No device calls, builds, deployment admission or video seal.** T14's first 64 KiB prefix omitted the relevant interaction. T15 recovered all 30,863,473 selected bytes, SHA `87be9dffb8d5d9a2607308be2a8b053459161e4369938a6393cde99263d5ee8d`. The five public excerpts retain exact original bytes, byte offsets, lengths and SHA; no settings JSON, URLs or user content is copied.

| Original source offset | Actual evidence | Interpretation limit |
|---:|---|---|
| 26606466 | libttmplayer namespace=0 relocation fails: SL_IID_ANDROIDSIMPLEBUFFERQUEUE missing | First matching player load failure in this recovered interval; not an exhaustive entire-process first-fatal claim |
| 26606831 | 08:01:36 TTPlayer rejects re-init; _setSupprotSampleRates JNI implementation unavailable | Consistent with failed player library loading; do not build a fake JNI stub |
| 26615989 | 08:01:36 MediaPlayer.native_init unavailable | Fallback path also fails; not evidence that fixing fallback is required before player reuse |
| 47989537 | 08:02:58 TTPlayer rejects re-init again | Later play-phase error in the same child; fresh candidate child required |
| 47998389 | 08:02:58 MediaPlayer rejects re-init again | Retains actual error instead of assuming a successful alternative |

The exact source file is `$BASE20/t15-5cd-range-window-02/range/selected.raw`; the original source range starts at 26377929. It was retrieved later under identity/inode/size guards. Those checks do not exclude in-place modification or truncate-regrow. The observed display remained a cover; nothing here establishes dynamic or audible playback.

## Selected reuse and narrow scope

The conditional [reuse card](../2026-10-20-t14-load-chain-reuse/README.md) now has its actual matching trigger. Recommend the complete archived **R8 observation set**: R3 routing/OpenSL compatibility and media init safeguard, R4 player proc-cache fix, plus the existing R8 bounded log mirror. It still changes four artifacts. R4's minimal alternative uses compat `9f558aaf` and player `5fba8050`; do not mix that pair into an R8 executor/admission. R8 uses compat `6e83e924`, media `d2882303`, player `0b4d95c5` and the reviewed run routing. Existing source, build recipes, raw build logs and remote archive hashes are in the reuse card and pinned original sources; no binary transformation or recompile is performed here.

The exact current5cd media/player inputs equal the old recipes' originals (`fecf91e1`, `b427614d`). The run before reference derived from the exact old source using only UID20011300 and WID29 hashes to the observed5cd `5a3aef63`. The after reference applies those same two substitutions to the known `79275cf9` routing template. **WID29 is historical, not future admission.** A fresh differing WID requires explicit new before/postimage review, not silent acceptance of arbitrary run bytes.

## Smallest executor derivation, after independent review

`parameters.json` carries exact5cd fields and the fresh-read checklist. Derive the existing candidate-r8/deployment/video_guarded_window_r8.py into this new directory; retain its `pathguard`, `fg`, backup-before-first-swap, staged hashes, metadata/label checks and CAS `swap` behavior. Change only the board-specific inputs and the following necessary safety gates:

1. Pin5cd serial, UID20011300, cfg19d0201b, current source pins, exact profile/holder/deadline and new admission. Replace old literal61b APPROVED with default preview/disabled execution. Freshly verify exact original run/media/player/private inodes and source provider compatibility. Compat must actually be absent for this absent-only route; pre-existing objects require a different reviewed plan.
2. Persist this5cd original apply-plan and all three backups before the first replacement. Preserve their actual original bytes/modes/UID/GID/labels. Replace media/player/compat before run. Reject foreign or partially unexpected state. Reserve at least10 minutes of a30-minute window for restore/reboot/verification; rehearse partial-apply rollback offline before execution.
3. Placement requires a fresh boot, then fresh parent/child and normal icon/feed/video action under the outer operator. Compare candidate files, original APK and runtime ownership. Existing oldchild1601 cannot prove a newly placed candidate. Use actual player logs; R8 mirror attribution additionally requires the existing two-hop binding checks.
4. On failure or deadline, restore **this5cd** apply-plan preimages, including partially applied states; remove compat only if it equals the exact new hash and was absent before. Restore original init parameter/control/power state, fresh-boot, repeat exactly the same before/restored snapshot plan and inspect normal icon/feed. Do not generate rollback from a later WID or use61b's64-target snapshot as an unexamined5cd plan.

The old executor uses61b UID/cfg/template metadata and its old admission is61b-only. It is a source donor, not an executable5cd deployment. The separately derived5cd executor is described below; its independent admission remains required.

## Acceptance stays narrow

Expected key: **toutiao only**, with the observed IID player-load wall moved. R8 history reached setDataSource/prepare with256 mirrored records; it showed a static cover and unknown audio. ANW provider/lock, networking and audio can remain later blockers. This plan does not include R9 network or R10 ANW changes. Do not promise playback or seal, and do not re-investigate the already evidenced IID mechanism.

The real Rust selector calls `verify_plan.py` for public excerpt integrity and static5cd parameter consistency only. Spec scenarios requiring live admission, loading progress and restoration stay human pending review. The original full rawrange remains private/persistent; `evidence-index.json` is sufficient to verify every public excerpt against it.

## Executor delivery update: explicit reviewed execution only

`derive_executor.py --repo "$REPO"` mechanically derives `executor.py` from the exact pinned R8 donor. The derived executor keeps the old physical CAS helpers; independent review must cover the added5cd admissions and recovery branch. `readonly-inputs.json` references the actual 08:20 reads and startup-script receipt. Actual runtime liblog is `d8ad176b` at `$RT/liblog.so`, not `/system/lib64/liblog.so`; system OpenSLES is `05d8ac90`. Original compatibility DSO is absent. The actual init trigger key is `sys.westlake.demo.u13.ready`; the earlier guessed readiness keys were absent. A later guarded exact-key read confirms its original value is `true` (receipt pinned in readonly-inputs.json); preserve/restore that value.

The actual5cd startup script rewrites the unique WL_PARENT_ID line on boot. This previously authorized parameter derivation is handled by saving current run bytes, verifying remote SHA before/after receipt, and normalizing **only one whole numeric WL_PARENT_ID line** to29. A rollback current file must then exactly match the known before/after bytes. Live-parent recovery additionally requires raw WID = fresh WMS = parent environment. Foreign UID, any other byte, duplicate/malformed WID and missing backups for changed files are refused. Rollback always restores the exact original5a3 bytes; the next boot's known WID rewrite remains a separate observed runtime fact.

`--recovery-no-parent` is accepted only with `rollback`, a newly signed current-boot admission and the original apply-plan SHA/source/holder/start. It skips WMS/proc/private-inode dependence and restores only the four physical files through the same CAS. Its completion is explicitly `PHYSICAL_FILES_RESTORED_REQUIRES_FRESH_BOOT`; the outer operator must then fresh-boot and verify actual private inodes, original control/parameter/power state and visible feed. It neither launches a process nor signals one. A backup absent before any swap is tolerated only when its target is still the exact original; changed targets require verified original backups. An uncertain transport is retained and never automatically retried as an apply.

Review/prepare `admission.template.json` in a private persistent output directory, fill exact holder/start/current boot and fresh parent/host identity, and have outer independently sign it. For rollback additionally bind `origin_apply_plan_sha256` to **this window's apply/plan.json**; `--start` and `--holder` stay the same original window. Do not extend beyond30 minutes. Start recovery within the reserved10 minutes.

```sh
# This is always a zero-device preview.
python3 benchmark/2026-10-20-t15-player-load-reuse/executor.py preflight

# Outer executes only after independent admission; INPUTS holds exact archived3DSOs.
python3 benchmark/2026-10-20-t15-player-load-reuse/executor.py preflight \
  --execute --repo "$REPO" --inputs "$INPUTS" --hdc "$HDC" \
  --holder "$EXACT_HOLDER" --start "$WINDOW_START" --boot "$CURRENT_BOOT" \
  --parent "$PARENT" --birth "$PARENT_BIRTH" --admission "$ADMISSION" --out "$PREFLIGHT_OUT"
# apply uses the same reviewed inputs/admission with mode apply and a new output path.
# rollback adds --apply-plan "$APPLY_OUT/plan.json" and a rollback admission/currentboot.
# Physical-only fallback additionally uses --recovery-no-parent; parent/birth may be omitted.
```

The executor does not reboot, unlock, operate UI or set logging parameters. The outer window owns those existing operations and their restore receipts. New7host tests run actual shell CAS byte replacement/refusal and real preview processes, plus numeric-WID byte equivalence checks. Only macOS metadata/SELinux command seams are mocked; those tests do not verify device SELinux or physical board behavior. A successful preflight is not a runtime validation and does not approve video playback.
