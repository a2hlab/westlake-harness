# U10.1: SoundPool-preserving policy and caller-owned compat publication

The rejected U10 used a reconstructed policy that omitted `libsoundpool.so`; it was not the deployed U9 baseline. The resident-compat r2 helper also repeated a parent namespace inheritance operation, replacing the caller's existing private-library whitelist. U10.1 uses the byte-reproduced U9 policy baseline and host r3. Final ELF checks precede any board window. Passing these checks does not establish runtime namespace visibility or screen rendering.

## Candidate and provenance

The durable bundle is `$WORKSPACES/westlake-inputs/generations/u10.1-j5ae3dd29-c015aa3a6-p0718f01e-r3-v1/bundle`. Its SHA256 is `f10b44f735a4276f9383243354e1adbf99912f017061b096fc0c407eea8741fb`; the native manifest is `325cd0a65d57407f8d41615501d2379c7afd4b446ff7458c736eb48ae05e0ddb`.

| Member | SHA prefix | Source / baseline |
| --- | --- | --- |
| appspawn-x | `65cc3535` | cx-bms host r3, `benchmark/2026-10-01-u10-native-shims/host-r3/`; actual bundle generation and child are rebound before compilation |
| libnativeloader policy | `0718f01e` | `westlake-inputs/generations/u10.1-policy-repro/native-loader-u10.1/`; baseline `fb9dc937` reproduces deployed U9, retains all five system libraries including SoundPool, adds only libstdc++ to the seven shared libraries |
| bionic compat | `015aa3a6` | cx-bms approved compat candidate, unchanged from the reviewed candidate; compared against deployed U9 `aa7e77f9` |
| runtime JAR | `5ae3dd29` | cc-t3 U11i build receipt, 197 classes; includes the provider-install marker even for zero providers |
| child | `dc73a28d` | U9 bytes retained; generation `74d1d6d48210ec5bf66ae43598655c3486b8873513821f13c2ffe15f0de552ac` |

Only six board paths change: the host, runtime JAR, and the Android/route aliases of policy and compat. ART, runtime/bridge, provider, child, 27 images, stubs and installation services remain U9 bytes. `composition.json` records each full SHA. OpenSLES and libjnigraphics work remain outside this candidate.

Two host rebuilds reproduce the donor r3 SHA. An earlier build differed only in `DW_AT_comp_dir`; using the recorded donor build directory restores exact bytes. Strict linking uses the recorded SDK compiler and 16 hashed reused objects. `host-resolved-inputs.json` accounts for 107 resolved inputs. Sources, compiler/linker, receipts and a 5,180-file inventory are persisted in the versioned generation directory; policy inputs retain their independent SHA ledger.

## Final-artifact gates

`final-gates/results.json` is generated from assembled ELF files, not inferred from source tests. It scans 102 payload copies / 86 unique ELFs and covers four policy consumers, nine payload compat consumers and 12 pinned application DSO members. Those members are SHA-verified; this does not claim that every current APK equals the historical pinned APK. There are zero export removals, signature changes or consumer breakages. Calls, dynamic sections and read-only data are recorded alongside the result.

Raw string-diff exit codes are **1 for host, policy and compat**, retained in evidence. Reviewed differences are restricted to the verified host helper/source/log strings, the policy's libstdc++ entry, and compat's new exports/log. Host `.data.rel.ro` is equal after resolving all 35 pointer slots over 352 bytes; `.rodata` differences match an exact allowance. Reviewed checks return zero. Raw exit 1 is not reported as raw success.

The approved registry contains 154 byte-identical automatic entries plus the two verbatim outer-approved compat lookup entries in `outer-approved-rows.json`. Candidate N1: **53 EXCEPTED, 0 REJECT**; N2: **103 EXCEPTED, 0 REJECT**. No stale entries or warnings apply. Baseline tickets also pass. Production G1/G2 pass, and frozen validation checks eight entries / 36 members with zero violations. `approved-production-dry-run.json` summarizes the master executor's real dry-run; full output remains in the durable directory. The four gate implementations used from the lane are byte-identical to master, with the newly approved registry supplied from this worktree pending landing.

`gates_passed=true`, `device_io=false`, **`rollout_ready=false` and `deployable=false`**. The last two remain false until the outer reviewer approves the window and promotion. Artifact identity checks used the offline expected map; their tool label is not evidence that this candidate is already deployed.

The existing harness suite ran 82 tests successfully, with three skips. Five delivery tests pass: rollback ordering, failed-rollback fencing, no second rollback after automatic recovery, production plan prechecks/166-key coverage, and same-inode/different-base loaded-instance counting.

`landing-paths.txt` contains the evidence and smoke spec and passes `land.py --preflight`. The approved full registry is already appended in this branch and is separately listed in `gate-landing-paths.txt`. It exceeds 1 MiB; the current preflight ignores `--allow-large` even though actual landing honors it. `native-exceptions-append.json` therefore also supplies the exact 156-row append delta and both registry hashes, preserving every master row. Outer landing must append that delta or separately land the reviewed registry with `--allow-gates --allow-large`; recheck concurrent master entries before copying a whole registry.

## Proposed windows — approval required before LOCK

| Board | Expected candidate RUNTIME | BOOTIMAGE | Keys | Plan |
| --- | --- | --- | --- | --- |
| 5ea | `f3b604c94df4` | `4db882a81732` | 55 | `window/plan-5ea.json` |
| 5cd | `f3b604c94df4` | `4db882a81732` | 55 | `window/plan-5cd.json` |
| 61b | `d6848fa2c989` | `4db882a81732` | 56 | `window/plan-61b.json` |

The 166 unique keys exactly cover the frozen `predictions-v5.csv`. Fingerprints above are offline predictions, not measurements. The differing 61b installation-chain bytes explain its runtime fingerprint. All windows are at most 45 minutes, stop starting keys at minute 35, use master `board_run --detach`, and require a fresh `U101_RUN_ID`. Unrun keys remain unknown. Planned commands, only after approval:

```sh
source "$WORKSPACES/westlake-inputs/env-mac.sh"
export U101_RUN_ID="u101-$(date +%Y%m%dT%H%M%S)"
python3 "$WORKSPACES/westlake-harness/scripts/lab/board_run.py" "$WORKSPACES/westlake-harness-u7-executor/benchmark/2026-10-02-u10-1-bundle/window/plan-5ea.json" --detach
# Use plan-5cd.json and plan-61b.json for their respective approved windows.
```

The smoke gate requires candidate fingerprints, host/policy/compat alias SHAs, three Java markers and the live host `owner_verified ... inheritance=caller_owned` marker. This host marker proves the address check ran; beneficiary app runs must establish actual relocation behavior. Maps count **loaded base addresses, not paths/inodes**: ART/JVM each one, bridge/runtime each two as in signed U9. Both are explicitly included in the probe's scanned library list.

After outer screenshot review, compare its signed per-key result using master `predict_vs_actual.py compare --predictions predictions-v5.csv --actual <outer-signoff.json> --json <comparison.json>`. The per-board CSVs allow partial-window comparisons; absent keys remain missing. Facts and process counts do not substitute for signed screenshot verdicts. Multiple changed members make any single-cause attribution a hypothesis until a discriminating window, as specified by `compare_runs.py`.

`window_hook.py --apply` verifies U9's 318 assertions before applying. `--finish` unconditionally rolls back U9, verifies identities, runs recovery smoke, and verifies again before unlock. Recovery failure keeps the lock. U9 targets are `565fc6fdc116` on 5ea/5cd, `a2919b793eb6` on 61b, boot `4db882a81732`. Smoke failure or confirmed U9-lit/FZ regression refutes the candidate; missing predicted benefit is recorded separately. No board was locked or written during this delivery. No N11g build was started.
