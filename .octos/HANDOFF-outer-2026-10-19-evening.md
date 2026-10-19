# #91 outer continuation — 2026-10-19 evening

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
