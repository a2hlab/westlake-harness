# #91 outer continuation — 2026-10-19 evening

## Current checkpoint — 19:57 (supersedes older board/next-step details below)

- User still requires continuous work. P0 and materials are complete within their stated scopes; video remains incomplete. No push in this continuation.
- r2 run-only was rejected statically. r3 three-file candidate actually ran: run template79275cf9 + compat9f558aaf + exact mffmpeg derivative d2882303 (fecf91e1, only DT_INIT_ARRAYSZ byte at0x48aca8:8→0). Derive source2165a64f and actual rc0 raw logs are committed/mirrored. Sources integrated master3eb8643e5a/3ba41c508d; review/probe2f5cce8aa; earlier reviewc7b23462b.
- Actual window19:35–19:46: boot8a1f0e6f-ddef-4600-90c6-fa7fdff35ac0 parent4814/birth6088 child6662/birth7540, real feedc11cb99d. Video tap then child exits; t5/t20/t25 are IMEhost. No GOT read, no playback acceptance. cppcrash identifies OH6.1.0.31, async_video_pla, SIGSEGV(SEGV_ACCERR). Reported frame+0x21a6714 differs from absolute-PC/ELF mapping; CC confirms actual ELF vaddr0xde714, Ghidra base0x100000 →1de714. Mechanism still being analyzed; do not call it anti-virtualization or a proven regression.
- Rollback COMPLETE/unlocked: boot0dd753ea-94f7-444b-9d46-9966a999bf28, parent4929/birth6723 child6817/birth8323, run d3518cef/mediafecf91e1/cfg91e31b95, compat file+parent mapping absent. Actual restored feed SHA2d42383d3a7f4708da879845f3b87abd17c9963cda007e0e78f67d80175e9002. Recheck before any new write; no lock held now.
- cc-video w9:pD is doing actual REA/Ghidra analysis of the player GLES proc-loader function. Token video-1919-r3-readout; no new repair admitted. cx-seal w9:p3 is finalizing the independent live+rollback evidence packet (currently compacting, do not interrupt): benchmark/2026-10-19-toutiao-rea-methods/video-1919-r3-live-review, exact landing/SHA lists pending final freeze. Copy only its listed paths, never unrelated worktree changes.
- Private base remains $HOME/.local/share/westlake/toutiao-resume-20261019. Actual scripts video_guarded_window_r5.py(89b054e1), video_probe_r2.py(92d162e0). Earlier r4 executor rejected, old probe lacks rc guard. r3 raw dirs video-r3-{preflight,apply,reboot,boot-ready,live,play1,exit-evidence,rollback,rollback-reboot,rollback-ready,rollback-live}. Preserve all.
- Durable hw248 mirror: source/input/output/actual derive logs in operator-configured $HW248_ARTIFACT_ROOT/toutiao-video-r3-20261019T192945; this variable is a NEW placeholder, not an existing env.md setting. Exact remote root in private video-r3-persistent-mirror/receipt.json. Complete raw window archive SHAa2f430e0e51f1fed0cb4fe86f376cd0e7f714924256be9bb14d6aa11a8fe5a93,3,580,863 bytes; public window-archive.json currently uncommitted, exact receipt in video-r3-window-archive/receipt.json.
- Completed: r3 live review60files and API3observations/32SHArefs independently accepted, integrated masterd60b191ac. Next: cc-video is narrowing a candidate-r4 player-only derivative for105 GLES/EGL cache GLOB_DAT→RELATIVE entries; prior HIDDEN idea rejected by actual musl source (only STB_LOCAL direct-self). No final r4 bytes or admission yet. cx-seal concurrently preparing fail-closed four-file r6 executor draft under video-r4-executor-draft; no device calls. Positive watcher96343, negative58106. EVO0148 collected. Do not stop after this checkpoint. Watchers: positive exec69905(readout),33333(live-review); negative21233(pD+p3),95904(p3) may have exited when a lane completed, rearm when needed. Resident evolution sentinels unchanged.

## Earlier checkpoint (historical)

User direction: keep other work running. Outer stays outside Herdr; inner work uses Herdr. At most two CC panes; currently one. Do not fix Toutiao random crashes/security mechanisms or clear app data. Local integration is authorized; this continuation has not pushed.

## Accepted and integrated

- Material ZIP delivered earlier, SHA `8201ab730a37a007561ef5c88b445d4e1a44237bac73f957cb3ec2a282c2aabf`; originals/source in master `39e26df6b1`. No unfinished material lane.
- P0 manual recovery code `3c14ab982b`; evidence `337405175`: natural and controlled child exit → real desktop icon → actual feed; another boot recovered feed. Scope is limited, with random exits/network dependence/startup delays. See `benchmark/2026-10-19-icon-reentry-live-r2/`.
- P1 compat candidate/build sources merged `85a1c978b`; static next-wall table `2980c9feb9`. Actual candidate failed loading libttmplayer through libvcbasekit missing `_ZNSt6__ndk18ios_baseD2Ev`; static t20/t25 cover, no playback. Exact execution recipes, logs manifest and verified rollback in `48b82b0f0`, `benchmark/2026-10-19-toutiao-rea-methods/video-1919-live-review/`.
- API additive view `207edc4c2`, latency wording refined `7ad1241af`: `benchmark/2026-10-19-api-progress-update/`. Two observations, twenty SHA-bound references, historical315 unchanged. Current source/build atlas README links this view. Remote publication not claimed.

## Board after rollback

61b exact serial `61b0657200000000000000000324012c`, boot `da213fc2-9010-4906-8578-ea242e8394ab`. Last observed parent `5279/birth11376`, child `7230/birth13029`, seq1. P0 cfg `91e31b959995772d305d5b034c9a5ebdbf3f8371495e3964185ada928db4ee2e`; original WID33 run `d3518cefb37a81be01f386ac7ac54193ab47da3475bdb00d16803853c80077d4`; compat file absent and absent from sampled parent/child maps. Real feed SHA `814261e0e19280cb6c81b794dc5c188e02a3fd8ad14ccf59fdb5ebfa247d46e1`. These are observations, not live identities to reuse without rechecking.

Video window ended and lock released 19:04; a later read-only provider acquisition ended/unlocked 19:07:49. No current board mutation is in progress. Retain exact lock, boot, metadata, parent birth and rollback guards before new writes.

## Active inner work

- Herdr default `w9:pD` / `cc-video`, worktree `../westlake-harness-video`, branch `analysis/toutiao-video-20261019`. Investigating actual recursive loader closure and preparing next minimal candidate. Its provisional r2 commit `07861c84d2`/run SHA `79275cf9...` is **not admitted** and has never been deployed.
- `w9:p3` / `cx-seal`, worktree `../westlake-harness-t4`, independent r2 reviewer. Token `video-1919-r2-final`; earlier provisional review integrated `80f3a42b4`. It may be unable to stage due to sandbox; outer copies exact landing lists and verifies SHA. Never copy unrelated modified files from this tree.
- Finished `w9:pC` and `w9:pE` panes closed; worktrees and delivered files retained.

The new confirmed source path: deployed libart `78e34445...` contains `link_stubs_arm64.cc`; snapshot/binding now under video worktree `static/evidence/r2-review/`. TARGETS is matched against original basename **before** SanitizeInitArray, not after. Java explicit load creates a new temporary inode and unlinks it after dlopen. The actual mffmpeg original `fecf91e1...` has one zero init-array slot with no relocation; libttmplayer DT_NEEDED loads by name through musl and can bypass that Java adaptation. Both lanes are reviewing reuse/recursive lookup. Do not claim this predicted path is an observed new crash. Preserve existing bionic null-slot semantics; no new security/constructor-filter policy.

## Durable private originals and recipes

Base `$HOME/.local/share/westlake/toutiao-resume-20261019/`:

- `icon-manual-live-r3/`, `icon-manual-live-r4/`: P0 raw observations.
- `video-p1-apply-r2/`, `video-p1-live-r2/`, `video-p1-rollback-r2/`, `video-p1-rollback-live-r2/`: failed P1 candidate and verified rollback.
- `deployed-cpp-provider/`: actual board libc++_shared `1cdf4eaecdb990769edce8f35d72034affb76ce47e6d7a946d15b62f18969725`, loader `/system/lib/ld-musl-aarch64.so.1` `fd3c4701acf719738fbd14cf1d419e4dd222c06a6df41f53d973354d648af7e2` plus raw transfer receipts. Initial wrong lib64 loader path failure retained.
- `video_guarded_window_r3.py`: only prepared, never invoked. Reviewer accepted delta `cae915e6596b76267d8c8130292471f52a8ade562da210d0d12dac74cbd29c21` versus prior executor, **not candidate admission**. It assumes original before plus absent DSO and a specific r2 after template; do not use for a changed candidate.

## Sentinels and evolution

Positive board watchers and negative `scripts/lab/lane_watch.sh` track live lanes. Consume/rearm on completion; a watcher existing alone is not proof work continues. Resident portable evolution watchers PIDs25030/25031 collected EVO-0146/0147. Use `$HOME/.octos/outer/evo/runtime-20261013-portable/` and GNU coreutils PATH per RUNBOOK; upstream manual harvest on Mac failed Bash Unicode/stat compatibility. Portable retro dry-run read four new cards. No upstream harvest success is claimed.

Next: reject known-bad r2 on precise source evidence, finish the minimal loader/reuse candidate, independent review, then a new bounded board window with rollback. Update the current observations only from actual results. Do not end work after this handoff.
