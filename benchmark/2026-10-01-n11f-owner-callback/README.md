# N11f resident-owner callback candidate over U9

The earlier N11e child stopped at branch 3: a default-namespace handle differed from the sealed owner. This build applies cc-wiki's approved `daa880505` patch with **zero fuzz**, using plan `3933e2cee` but replacing its obsolete U10 base with signed **U9**. It does not claim that returning the resident handle has been verified on a board.

## Evidence and approved offline gate

- Exactly reproduced N11e child **3f1e703c** before applying the change; two N11f builds both produce **f1b43386**. See `build-receipt.json` and `patch-receipt.json`.
- Only `sealed_child_provider_loader.o` and `westlake_android_child_plugin.o` change. The generated manifest object and other ten seed objects are unchanged.
- Manifest **774d5c4e050c**, bundle **a6dc2b277111**; only `/system/lib64/appspawn/libwestlake_android_child.z.so` differs from U9. ART, JVM, bridge, runtime, installer, Java and images stay byte-identical.
- N1: **52 excepted, 0 rejected**; N2: **103 excepted, 0 rejected**, **PASS** (`approved-native-gate.json`). The 154 unchanged findings are in `auto-registration-rows.json`; outer approved the sole ART NOLOAD binding at **00:15:10**. `outer-approved-row.json` contains the exact supplied row. This approval applies only to the proposed N11f 61b observation; unified-state promotion needs fresh review.
- Initial production dry-run correctly rejected the then-unapproved row (`production-dry-run-r1.json`); it remains immutable evidence. Approved native dry-run passes (`approved-native-dry-run.json`). Approved production dry-run now passes **G1/G2, native and frozen gates**, `gates_passed=true`, `device_io=false` (`approved-production-dry-run.json`). `deployable=false` reflects the unapproved rollout, not a gate failure. Its complete immutable plan is retained in the durable handoff; the public summary binds its SHA. The bundle remains `rollout_ready=false`; no lock, deployment, app run or screenshot has been made for N11f.
- Frozen check: **8 entries, 32 checks, 0 violations** (`frozen-full.txt`). Known-answer suite: **82 tests, 3 skipped, PASS**. C result-channel test passes; it exercises real C layout/bounds/error handling, not OH namespace behavior.
- ABI against deployed U9 child `dc73a28d` with its actual host consumer: no export removal/addition/drift, no consumer break, unchanged SONAME/NEEDED. Four call-set changes include the N11e diagnostic lineage. Against exactly reproduced N11e: three changed call sets, all from the approved patch (`abi-calls.json`).
- `deployed_strings_diff` is recorded against **deployed U9**, separately against N11e. `strings-review.json` classifies every difference and directly checks that every baked `/system/…` path and the ENTRY_RESULT marker remain present. Rendered binary scalars are not a removed library list; raw reports remain available. No broad allow list was applied.

## Intended behavior and falsification

The callback returns the two previously published sealed owner handles instead of opening another copy by name. The default inherit/NOLOAD comparison is removed. If called before publication, it records **branch 6** and falls through to the original open; this is a measurable failure, not a silently accepted second owner. HiLog lookup failure remains nonfatal (branch 4). The host prints an unconditional `[N11e-PROBE] done stage=… branch=… index=…`; errors use the failing call's captured dlerror instead of stale process state.

The proposed 61b window is **<=30 minutes**, no new keys after minute 20, with continuous hilog/proc-fault capture before replacing the child. Smoke requires the candidate SHA, `done … branch=0`, and exactly one ART/JVM/bridge/runtime loading instance. HelloWorld is a hard live control, ZigZag an advisory observation per the supplied flaky-key rule. The 18-key prediction comes from cc-wiki's pre-window CSV (four sessions-miss candidates, ten other-cause observations, Wikipedia and three canaries). Missing time-budget samples are unknown. Before unlock, rollback removes the child overlay, verifies **318 assertions / 316 paths**, collects U9 HW/ZZ recovery smoke and verifies identities again.

`plan-validation.json` checks the existing-evidence/expect fields and silent-marker rule without invoking board_run. `plan-61b.json` remains **not authorized to execute** until outer approves the window plan. The gate binding is now approved.

## Identity and durable reproduction

Durable candidate: `$WORKSPACES/westlake-inputs/generations/n11f-u9-owner-callback-v1/` (`build/`, `bundle/`, `source/`, `frozen-build-inputs/`). Its **4,328 archived files / 18 input roots** were individually re-hashed; `archive-receipt.json` records the inventory and mapping digests. `input-map.json` maps original paths to exact archived SDK/sysroot/headers/seed objects; source includes the N11e baseline and complete stock-child-plugin tree. No SDK or ELF is committed to the public repository.

`build.py` replays N11e's recorded commands and checks all 13 seed-object SHAs before building three variants. Frozen compiler SHA, each command and object SHA are in `build-receipt.json`. Restore archived input roots according to `input-map.json` if original `.work` inputs disappear; the archived bytes are authoritative. Never reuse a partial output directory.

The legacy bundle reference fingerprint excludes the installation-chain overlay and is **a8cb9a5a45a6**; it is not the expected board fingerprint. `expected-run.json` expands the installation-chain identities and is the device oracle: **5ea/5cd 565fc6fdc116**, **61b a2919b793eb6**, **BOOT 4db882a81732**. Child is outside FINGERPRINT_PATHS, so the explicit child SHA and 318 assertions are essential.

No board verdict yet: namespace sharing, copy count, rendered UI and prediction outcomes are **unverified**, screenshot/alive counts **unknown**. Do not treat an offline gate or compilation as lighting evidence.
