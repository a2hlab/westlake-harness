# 61b r17p versus accepted 5ea v2: descriptive evidence

**Machine evidence complete; outer screenshot review pending.** The sweep completed at about 06:28 CST: **66 terminal records, 63 comparable clicked APKs, 126 captured=true screenshots (126 hash-verified), 26 apps alive at t5 and 24 at t20**. Three prelaunch failures have no process sample: Seal, Toutiao and Subway Surfers. Process counts are not lighting counts. [Per-key table](final/per-key.csv), [installer comparison](final/installer-comparison.csv), [outer review page](final/review.html), [machine summary](results.json). The source's own [facts](final/run-identity/facts.txt) agree: line 1 pins the fingerprint and line 68 states the 66/126/26/24 totals.

Interpreting `StartAbility returned 0` as successful secondary-window activation would have hidden the installer wall. **14 keys have an app-requested target linked through an AMS trace to a WMS background denial, despite return 0.** All 63 comparable 61b bundles lack the background permission that their accepted 5ea counterparts have. The 14 trace-linked denial keys are Wikipedia, Aegis, AppManager, fd-noice, Markor, Thunderbird (fd-android), FileManager, Gallery, K9, Shattered Pixel Dungeon, Tusky, BinaryEye, VLC and noice. No corresponding trace-linked denial was extracted from their accepted 5ea v2 logs; missing matches do not prove no denial occurred. [Exact PID/target/trace excerpts](final/log-evidence.json); per-key grant and return-code evidence is in [installer-comparison.csv](final/installer-comparison.csv).

Anki alone changes measured desktop entry: 5ea `com.ichi2.anki.IntentHandler` versus 61b `leakcanary.internal.activity.LeakLauncherActivity` ([installer-comparison.csv](final/installer-comparison.csv), line 15). This is a different entry point, not an observed intended Anki page. INTERNET metadata is unchanged: **50 granted→granted, 13 absent→absent, 3 unknown→unknown**; no measured INTERNET grant was lost.

### Actual profile, not the frozen 5ea profile

Run fingerprint **f2421c7197f7**, **117 paths**, board **61b0657200000000000000000324012c**, boot **6fd44228-d33e-4f0e-9bf9-9a34842c72bf**. Actual JAR is r17p `a0ed5c4f`, hwui `be59260f`, installer `6f94d4f4/eb6824b4`. The companion audit returns **known_jar_profile_drift**: hwui differs from the frozen a578b949, the installer pair differs, and the board is outside the frozen 5ea profile. **v3 same-profile denominator = 0; accuracy = null.** All 104 frozen files remain unchanged. [Profile audit](final/profile-strata.json), [run facts](final/run-identity/facts.txt), line 1.

Against the accepted 5ea v2 continuation's 117 measured paths, **114 are identical; only the JAR and two installer libraries differ**. The first 5ea segment measured 115 paths: 114 identical and JAR changed; installer hashes were captured separately and first appeared in the continuation fingerprint. Native hwui be59260f is therefore identical between these two actual sweeps, though different from the v3 frozen override. [Full measured-path delta](final/runtime-comparison.json).

The 61b evidence lacks an independent same-boot shell/foundation-root installer readback, and run-start fingerprints are not resident maps. The old installer is observed in the run fingerprint and its effects are described through measured bundle metadata/entry points; no unmeasured foundation mapping is asserted. Board, JAR, installer, batch protocol and app state prevent an installer-only causal estimate of lighting.

### Trace-linked background refusals

Each line below is in `<run>/<key>/hilog.txt`, with `<run>` equal to `/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-30-r17p-61b-sweep/runs/r17p-all-61b/61b0657200000000000000000324012c`. The copied excerpts retain full source path, log hash, target request, trace and original line numbers.

| Key | WMS refusal line |
| --- | ---: |
| wikipedia | 51702 |
| aegis | 36286 |
| fd-AppManager | 41296 |
| fd-noice | 43991 |
| markor | 38066 |
| fd-android | 60691 |
| fd-filemanager | 38890 |
| fd-gallery | 36180 |
| fd-k9 | 54330 |
| fd-shatteredpixeldungeon | 29510 |
| fd-tusky | 60195 |
| fd-binaryeye | 40154 |
| vlc | 43685 |
| noice | 42279 |

These show a denied activation mechanism, not that all 14 would light after a repair. In particular, earlier 5ea screenshots already include own content for Aegis, Thunderbird, FileManager and K9, while the new images await outer review. A controlled follow-up would hold board/JAR/native components and reinstall protocol fixed, replace the installer pair, then re-read grants/entry points and adjudicate captures. This task performed no such intervention.

`source-records/` is copied at final publication. Earlier `snapshots/` remain explicitly partial and may include a record still being updated; they are not the final statistics.

## Reproduce to a fresh output directory

```sh
python3 benchmark/2026-09-30-r17p-61b-comparison/compare.py \
  --out /ABSOLUTE/NEW-OUTPUT-DIRECTORY
```

The default input is the outer loop's `benchmark/2026-09-30-r17p-61b-sweep/runs/r17p-all-61b/61b0657200000000000000000324012c` under the main worktree. It is read-only. Pass `--installer-readback` if a same-boot shell/foundation-root readback is supplied; its absence is recorded, not waived. `--partial` and a fresh output path create explicitly partial diagnostics. Existing output directories are never overwritten.

Outputs:

- `profile-strata.json`: unchanged companion auditor, actual component differences and frozen-profile exclusion.
- `per-key.csv` / `results.json`: 66 rows, actual APK identity, launcher, click, captures, t5/t20 app-process samples, observed log clues and prior accepted 5ea outcome.
- `installer-comparison.csv`: installed background/INTERNET permission states, launcher changes, StartAbility return values and trace-linked WMS denials.
- `log-evidence.json`: original log paths, SHA-256, exact PIDs, target requests, trace IDs and line-numbered excerpts.
- `review.html` / `outer-review-template.json`: linked captures for outer adjudication. No automatic lighting verdict.
- `source-records/` and `run-identity/`: small copied evidence; large original logs/captures remain at hashed source paths.

## Mechanism, outcome and attribution

The archived installer [handoff](installer-source/HANDOFF.md) and [manifest](installer-source/manifest.json) name the old `6f94d4f4/eb6824b4` and new `6aadb8b4/7048c7c5` pairs. [Source receipt](installer-source/receipt.json) pins their supplied source archive. `apk_network_permissions.h:29–61` documents the unconditional background permission; `launcher_activity.h:31–56` prefers an own-package launcher. Network permissions remain Android-manifest-dependent: an app with no INTERNET request is not automatically a networking regression. Supplementary process gids and per-app network reachability are not measured here; identical INTERNET metadata does not prove identical network capability.

For each app, bundle `reqPermissions` plus `reqPermissionStates` distinguish **granted / absent / not_granted / unknown**. Missing evidence never means absent. Selected launcher comes from the measured record. A changed launcher is direct evidence of a changed entry point, not proof that a later page became visible.

**StartAbility returned 0 can precede an asynchronous WMS rejection.** An app-PID `nativeStartAbility` target is linked to the AMS `NotifySCBPendingActivation` target, then the same hexadecimal trace ID is used to attribute WMS background denials. Unrelated system-process messages are excluded. No matched call means unobserved, not proof that the path never ran. Absence of a matched denial is not proof of permission success; nonzero return codes alone are not labeled permission errors.

App log clues require a `nativeOnScheduleLaunchApplication ENTRY bundle=<exact package>` PID anchor. Chronological first clues can be tolerated errors; they are not adjudicated first blocking walls. Missing anchors or evidence stay unknown. Screenshot counts use `captured=true` with independent file-hash checks; process counts use exact BMS UID and appspawn-x/package NAME, excluding same-UID shell helpers. Neither survival nor return codes imply UI.

The accepted 5ea v2 baseline consists of first terminal attempts across the original and cold-stop continuation runs. APK mismatches are not treated as comparable. Board, JAR, installer, protocol and app state differ, so this is not an installer-only intervention. Permission denial can be attributed to a traced gate; the effect of changing installer on lighting requires a controlled follow-up. All new visual verdicts remain pending outer review.

## Checks

```sh
python3 benchmark/2026-09-30-r17p-61b-comparison/test_compare.py Rules Rejection
# After final publication:
agent-spec lifecycle specs/bms-background-start/t5-r17p-61b-description.spec.md \
  --code tools/spec-checks --review-mode strict
```

Eight Python checks pass through the contract: two scenarios pass and the screenshot scenario remains pending_review under strict mode (0 failures, lint 100%).

R2: offline extraction rules verified; execution and installed metadata described from source records; lighting pending outer review. No device operations, locks or Git metadata writes.
