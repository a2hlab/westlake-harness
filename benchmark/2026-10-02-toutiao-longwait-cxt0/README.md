# Toutiao long-wait capture on unchanged U10.1T8

Earlier short captures ended while Toutiao was binding its application. That was insufficient to call the failure interpreter slowness. Two clean 95-second captures on 61b now show a subsequent native crash in both runs. Neither run changed the native generation, runtime JAR, boot images, JIT flags, or installer.

The approved invocation used the master batch tool, the original apps manifest and input root, `--reinstall --wait 95 --hilog 95 --shots 20,45,90`. Existing batch settings preflight remained in force. The initial read already showed 16M log buffers and private off; clock skew was within tolerance, so no date correction occurred. Board ownership was locked to cx-t0, then released after exact final readback.

Both runs reached `handleBindApplication returned OK`, then died with `SIGSEGV(SEGV_MAPERR)` at PC zero. The next frame was `/data/app/.../libtttext_lite.so`, `ttoffice::tttext::ICUWrapper::ICUWrapper()+100`, relative PC `0x1beb4`. DFX reported the crash and appspawn reported signal11 exit. These are raw log facts, not a visual signoff or a determination of the missing callee. The exact excerpts are in `evidence/trial-{1,2}/fatal-excerpt.txt`.

Each facts block is preserved verbatim. Both records have three captured screenshots, at scheduled t20/t45/t90; actual offsets are in `results.json`. There was no scheduled t5 observation; the facts row correctly says `alive t5=?`, despite its aggregate counting zero. Foreground-unconfirmed is retained without treating it as an image verdict. Outer review owns screenshot classification. Only t20 maps were captured, as authorized.

The batch diagnostics reported no standalone faultlog files. That empty list does not negate the original DFX stack in each complete hilog. The raw run directories, screenshots, maps and command logs remain intact and are also copied to the versioned evidence-backup location in `results.json`.

Final readback: 318 assertions, diff empty, absent empty; runtime `d6848fa2c989` (123 files), boot `e3806b65a079` (36 files), boot_id unchanged. The entire board window was approximately 17 minutes. There was no deployment or rollback, and the lock is empty. VM health before/after is recorded in evidence.

Rule established: longer capture falsifies the pure-slow explanation for these two runs; it does not establish that JIT/AOT removes the ICUWrapper crash. No fix is implemented here.
