# Toutiao video r3: failed playback, verified rollback

The candidate reached player code, but did not pass video playback. A feed screen, READY, four compatibility-library mapping segments, or zero matching LOAD-FAIL lines must not be counted as playback or a completed provider check. This packet closes the actual r3 window; later mechanism investigations are separate.

## Observed outcome

- Candidate boot `8a1f0e6f-ddef-4600-90c6-fa7fdff35ac0`: parent `4814/6088`, child `6662/7540`, UID `20011206`. The [candidate feed](candidate-feed/screen.jpeg) was visually reviewed before the video-tab click.
- The click at `(360,1858)` was followed by [t5](play1/t5.jpeg), [t20](play1/t20.jpeg), and [t25](play1/t25.jpeg), all visually reviewed as IMEhost, without a video frame. Actual screenshot completion times were about 6.60/21.76/26.84 seconds after click-command return; labels are scheduled targets, not exact exposure times.
- Original crash evidence identifies `async_video_pla`, PID `6662`, UID `20011206`, `SIGSEGV(SEGV_ACCERR)`, and platform `OpenHarmony 6.1.0.31`. The absolute PC lies inside a `libttmplayer.so` executable mapping. Thus player code executed. Full loading, selected GOT providers, decoding, audio, and video presentation were **not verified**. No `got.json` was obtained after the child exited.
- The original crash reports frame `libttmplayer+0x21a6714`; subtracting its offset-zero mapping start from the absolute PC gives `0xde714`. This discrepancy remains unresolved. Both original observations are retained; no symbolization or causal patch claim is made.
- Complete stderr contains both mffmpeg and ttmplayer load-attempt lines. The earlier `media-selected.txt` filter omitted ttmplayer. Zero selected LOAD-FAIL lines is not proof of successful loading. An earlier `sigaction(signal=11)` line was registration, not the delivered crash; the original cppcrash is the signal evidence.

## Rollback closure

The exact original-apply-bound rollback completed with host/explicit remote rc `0/0`, then a fresh boot produced `0dd753ea-94f7-444b-9d46-9966a999bf28`. The final [identity output](rollback-final/identity.stdout.txt), [original command receipt](rollback-final/command-00007.json), empty stderr, and [feed screenshot](rollback-final/screen.jpeg) were independently read.

Final parent `4929/6723`, child `6817/8323`, sequence `1`; restored run `d3518cef…`, media `fecf91e1…`, unchanged P0 cfg `91e31b95…`; compat file and parent mapping absent. Full hashes are in [results.json](results.json). The screenshot SHA is `2d42383d3a7f4708da879845f3b87abd17c9963cda007e0e78f67d80175e9002`. This is recovery-feed acceptance, not video acceptance. The outer reported unlock at 19:46; no independent unlock receipt is fabricated.

The final identity shell is a composite command. Its rc is not a separate rc for every subcommand. The expected three hashes, explicit file-absence rc0, absence output, process identities, and empty stderr support this specific observation; its grep else-branch is not proposed as a generic read-error-safe checker.

## Preserved execution and evidence

[historical-recipes](historical-recipes/README.md) preserves the four actual supplied Python sources byte-for-byte, plus generated apply swap; [rollback](rollback/) preserves the actual rollback swap/plan/result. These are historical one-off execution recipes, not permission or a portable tool to rerun against a live board. Their original dependencies, lock, process/boot and private inputs still apply. r5/probe-r2 bytes match pre-execution reviews; the two supporting helpers are exact supplied snapshots, without invented per-invocation source timestamps.

- [source-pins.json](source-pins.json): original records, images, source, big logs and crash SHA/size with portable private locations.
- [raw-command-pins.json](raw-command-pins.json): exact original command JSON/stdout/stderr hashes, including nonzero remote observations. Host rc0 is not silently converted into remote success.
- [facts.txt](facts.txt): actual `run_facts.py` on this package parent. Standard alive tables are absent, so alive fields remain unknown; the numerical zeros are not death claims. Process evidence is reported separately above.
- [Build/derivation archive receipt](archive/build-artifacts-receipt.json): previously verified exact mffmpeg input/output, derivation source, rc0 and original stdout/stderr; this is an input to the live review, not a new build.
- [window archive receipt](archive/window-archive.json): existing outer remote SHA verification, 3,580,863 bytes, SHA `a2f430e0e51f1fed0cb4fe86f376cd0e7f714924256be9bb14d6aa11a8fe5a93`. No archive/SSH verification was rerun here. `HW248_ARTIFACT_ROOT` is operator-configured; the exact location is in the SHA-bound private receipt.
- [SHA256SUMS](SHA256SUMS), [freeze.json](freeze.json), [landing-paths.txt](landing-paths.txt): exact handoff. The checksum list excludes itself and freeze.json; freeze binds it, avoiding a hash cycle.

Screenshots and small technical excerpts are public copies; large stderr/hilog and the entire original cppcrash remain unchanged in persistent private storage and the archived window. Normalized record copies change only local image paths and add review fields/original-record hashes; original pending_review fields remain as producer history. No APK, commercial DSO, full decompilation, personal home path, or large raw log is included.

## Scope

Applicable existing scope: `specs/toutiao-video-playback/t2-minimal-repair.spec.md` and the bounded r3 load experiment. Verdict: **R3 PLAYBACK NOT PASSED; ROLLBACK VERIFIED**. API publication may add this candidate failure observation, without changing historical 315 grades or claiming a new API success. No device calls, builds, new tests, runtime edits, git staging retries, or push were performed for this evidence closure. Root README/DIGEST are not edited; the proposed Layout and knowledge lines are supplied separately.
