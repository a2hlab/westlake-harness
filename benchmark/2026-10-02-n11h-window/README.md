# N11h: executable host-only observation on U10.1T8

The accepted audit package was not deployable: its host payload was `65ac5089`, but `live_hashes[/system/bin/appspawn-x]` still asserted baseline `65cc3535`. Both production alias validators rejected this inconsistency. The binary was not rebuilt. The persistent production copy repairs that declaration and the corresponding manifest bindings in `native-gates.json` and each N1 scan profile. Original audit evidence remains unchanged.

## Exact objects

- Signed base: **U10.1T8**, bundle `190afedd3ddb250752e67b83d19669b6a952eb04cd69db5edf0b06eafe119736`.
- Only effective change: `/system/bin/appspawn-x`, `65cc3535` → `65ac5089`.
- Production native manifest: `4897f0cb80c5ceb3bfda3eff4805bbd5b7d61263b16b7a8997ebd2cf64dd0dc8`.
- Input binding: `44efccd285671bcc0c5a37fbb0ccb87246e902a9a39a2dfac246c3414516cf8c`.
- Persistent package: `$WORKSPACES/westlake-inputs/generations/n11h-u101t8-host65ac5089-v1/native`.
- 61b runtime: base `d6848fa2c989`, candidate `5b620859a5f6`; boot stays `e3806b65a079`.
- 318 assertions / 316 unique paths. All effective JARs, 27 images and installation-service aliases remain signed base bytes.

`audit-registry-delta.json` regenerates the requested 156 auto-identical findings for audit manifest `37c48e2b`. `registry-delta.json` rebinds those same 53 N1 + 103 N2 findings to the corrected production declaration. `outer-binding-proposal.json` requests the exact new binding for the separately approved resident-query site (ACK(80), 2026-10-02 14:41:32). No production registry was changed. The proposal has **157 total findings**, including the one new site; it is not an invented 156-total count.

`proposed-native-gate.json` and `vm-proposed-native-gate.json` both show N1=54 excepted, N2=103 excepted, zero rejected. They use an explicit temporary proposed registry, so **production admission remains pending outer adoption**. Frozen check: 2 declared FZ-002 paths checked, zero violations. The approved build's ABI/calls/consumer/readonly/open/19 exact string evidence remains at `benchmark/2026-10-02-n11h-host-owner/` and `benchmark/2026-10-02-n11h-admission/`; the binaries and source files are unchanged.

## Transaction and rollback

`window_hook.py` uses the production `u7_executor.Transaction` journal and `DeviceIO` stop/start/stage/bind/verify/rollback primitives with exactly one operation. Its scoped ticket validator checks both production native tickets, exact composition and identity hashes, and the sole host operation. It does not manufacture a full-generation upgrade or rebind unchanged boot/JAR overlays. Those signed members are included in full snapshots and parent/child view checks.

Before any experiment lock, `dispatch.py` requires the enabled approved plan, registered production gates, VM tool execution, OrbStack, HDC serial, and shared package SHA. The residual Toutiao cleanup must also respect the board lock: it takes a **separate guarded recovery lock**, verifies the signed 318 base, calls the existing BMS UID/PPID cold-stop guard, verifies the base again and unlocks, then lets `board_run --detach` acquire the experiment lock. It never signals the root parent. Unknown ownership or cleanup failure retains the recovery lock and stops dispatch. Cleanup is not attempted during this offline preparation.

`finish` always restores the same promoted `U10.1T8` host, checks 318 + both fingerprints, runs HW/ZZ recovery smoke and rechecks identities. Failed cleanup, rollback, smoke or final assertion retains the lock. **There is no U9 fallback.** The U7 production rollback still provides the OrganicMaps guarded cleanup fallback.

## Smoke and observation budget

Two actual activation markers are hard gates: resident-check rc=0 and sealed-owner inherit rc=0. ART/JVM/bridge/runtime must each have one load-base, using the production smoke counter. The conditional HOST-OPEN marker is advisory; the current smoke evaluator has no conditional-marker implementation. A `reject` action is not successful relocation. Recovery instead asserts the signed base's accepted bridge/runtime count of two.

The plan contains 26 distinct keys, including the seven AssetManager→GetLongField abort keys and the required Fennec compat canary. There are 40 planned launches with explicitly separate repeat shards. **The 30/20-minute budget overrides that list**: stop starting keys at minute 20, retain all evidence and report unmeasured keys/repeats as unknown. Completing all launches is not promised. White-lottery improvement requires the signed prior's minimum streaks: fd-noice 4/4, fd-uhabits 3/3, noice 5/5, Wikipedia 6/6, with its thin-prior caveat. Incomplete streaks give no statistical gain claim. Outer t20 review is required; this lane supplies no lit count.

The seven added abort keys are conditional observations: a single runtime owner might remove the cache/object mismatch, but could leave a separate missing initialization. Their first fatal must be measured, not assumed cured by fewer mappings.

## Review and execution

`plan-61b.json` is fully filled but `execution_enabled=false` pending outer review and exact registry adoption. Before LOCK, rerun the real production dry-run with the adopted registry. After approval:

```sh
export N11H_RUN_ID=n11h-61b-<fresh-id>
python3 "$WORKSPACES/westlake-harness-u7-executor/benchmark/2026-10-02-n11h-window/dispatch.py" \
  "$WORKSPACES/westlake-harness-u7-executor/benchmark/2026-10-02-n11h-window/plan-61b.json" --detach
```

No device commands, lock acquisition or deployment were performed for this delivery. `tests.txt`: 12 tests pass, including the real journal's one-host operation, lost-bind-response restoration, dirty-base refusal, disabled dispatch, failed cleanup retaining its lock and strict single-member alias validation.
