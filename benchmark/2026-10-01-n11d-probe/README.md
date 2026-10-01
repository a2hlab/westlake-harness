# N11d diagnostic child

N11b R3 returned LOAD_ERROR:10 without identifying the rejecting guard. The absent optional host-debug probe `libartbased.so` is not a sealed member and is also observed in successful U8 controls; this build does not treat that warning as the cause. N11d only names the two existing fatal early-owner branches and every per-library open result. It preserves all returns, cleanup and admission decisions.

## Source and reproducible build

The starting source is the accepted N11c logging source, plus cc-wiki's `n11d-probe-early-owner.patch` from `benchmark/2026-10-01-n11b-r3-loaderror-analysis/`. Branch diagnostics also use the already resident weak HiLog entry because stderr may be closed; no additional DT_NEEDED is introduced. N11c's library-index, path and NULL/dlerror logs are retained. No tolerance change or provider reorder is included.

`build.py` reuses the exact N11b compiler/linker commands and recorded frozen objects. It reproduces baseline `163da805`, builds candidate `69598037a0dbb79b82ddee0f7415784643510c6583c6dff736b655a8401e0f4f`, and independently rebuilds identical bytes. The build receipt records source/object hashes and portable commands. Build outputs stay at `$WORKSPACES/westlake-n11d-probe-build/`.

`abi_diff --calls` reports **two** functions, with no removed call targets: `RealOpenLocalNow` adds HiLogPrint for the fatal branches; `WLSCPL_LoadSealedProvider` adds HiLogPrint/dlerror for the open loop. Exports remain 2/2, removed/added exports and signature drift are zero. DT_NEEDED remains libc.so. The outer loop accepted both function differences; the earlier draft's one-function expectation was incorrect.

## Package and admission

The package is `$WORKSPACES/westlake-generation-n11d-child-u9-69598037`. It changes only `/system/lib64/appspawn/libwestlake_android_child.z.so` from U9 `dc73a28d` to the diagnostic child. All other native members, J10g, T7e images and installer bytes remain unchanged.

The first production gate correctly rejects unregistered findings. Exact semantic comparison auto-approved 154 findings; the two remaining N1 findings cite the new `n11d-child.c` source and are listed in `needs-outer-review.json` for independent review. They are the existing sealed-ART NOLOAD and dynamic owner-path lookup sites. No gate is weakened, and no board lock is taken before admission passes.

## Planned window

Use the outer-selected idle 5ea, at most 30 minutes, via detached board_run. Update the draft to the new installation-chain fingerprint schema (5ea base runtime `565fc6fdc116`, boot `4db882a81732`). A guarded continuous collector must start before the child replacement and span the failed launch through t20. Preserve raw hilog, maps/fault evidence and exact facts; logs alone do not establish a lit verdict.

HelloWorld is the hard non-flaky control; ZigZag is advisory. A smoke failure stops the diagnostic shard, but its captured loader logs still answer the probe question. Roll back the child to U9 `dc73a28d`, verify the full current installation/core identity and both fingerprints, then unlock. The window classifies (1) verified single owner with controls, (2) observed degraded/partial initialization, or (3) still fatal with the named branch/library; it never promotes a fatal probe into a unified state.
