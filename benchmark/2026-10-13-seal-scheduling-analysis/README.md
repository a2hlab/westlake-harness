# Seal scheduling analysis: current f28 first four windows

The wrong optimization target is the mandated screenshot delay or the window identity gate. The evidence points first to desktop search and repeated transport setup. Do not treat command counts as command CPU time: successful numbered receipts retain `finished` but overwrite `started`.

The current f28 round is `benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-full128-execution/round`, boot `b7116cfc-14c0-43cb-b46b-c233ce5f13a6`. Windows01-04 contain **72 primary apps, 26264 numbered command receipts, 56.94 minutes inside primary command sequences**, mean **47.45s/app**, median **46.95s**. Smoke is separate: **6.70min**. Eight identity bookends span **41.46s** by persisted file mtimes, approximately **1.06%** of the four window envelopes. Their process startup and first read are not timed. These are the current5ea337-path bookends; the future61b954-object/507-metadata gate is larger, so this is not a61b identity-time prediction. No device/VM/remote command was issued.

| Interval attribution | Four windows seconds | Seconds/app | Primary share |
|---|---:|---:|---:|
| launcher_ui | 1390.37 | 19.31 | 40.7% |
| screenshot_schedule_wait_estimate | 485.05 | 6.74 | 14.2% |
| boot_guard | 477.55 | 6.63 | 14.0% |
| other | 241.96 | 3.36 | 7.1% |
| hdc_list_targets | 159.85 | 2.22 | 4.7% |
| process_maps | 130.90 | 1.82 | 3.8% |
| screenshot_capture_hash_transfer | 124.53 | 1.73 | 3.6% |
| hilog | 120.82 | 1.68 | 3.5% |
| non_screenshot_hash | 82.75 | 1.15 | 2.4% |
| ps_query | 80.24 | 1.11 | 2.3% |
| lock_held | 61.01 | 0.85 | 1.8% |
| window_query | 33.83 | 0.47 | 1.0% |
| bms_query | 17.23 | 0.24 | 0.5% |
| other_host_gap_estimate | 10.48 | 0.15 | 0.3% |

These are finish-to-finish attribution intervals, not independent command execution measurements. HDC startup is included and cannot be isolated. Screenshot waits are estimated from the exact numbered gaps before scheduled screenshot guards minus10ms; original gaps and conditional bounds are retained per app in results.json. The requested t5/t10/t20 times are not proposed for reduction. CLI/source basis: `benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py:398` overwrites `started`; `:760` waits against the original click clock. Raw evidence is pinned by per-directory receipt-manifest SHA and record SHA in results.json.

Desktop work includes **345 swipes / 751.28s**, **487 layout dumps / 479.90s**, and **142 Home inputs / 60.43s**. Removing all swipes is not a valid optimization; the scaled **22.26min** is an unattainable category ceiling. There are **0** consecutive equal nonempty icon-page signatures; no assumption that every equal signature is a safe early-edge decision is made.

Prioritized next-run changes, preserving current evidence criteria:

1. Prepare local sources, manifests, disabled plans, source mapping, and downstream argv while the current5ea full128 and5cd restore run. Keep only actual61b UID/boot/WMS/admission fields pending. This is critical-path scheduling, with no invented extra validation phase.
2. Reuse the settled launcher layout as the first exact icon lookup: current code immediately dumps the same page again with no intervening UI action. Keep the actual fresh tree, exact package/activity match, focus guard, and durable click intent. The direct duplicated three-operation cost scales to **2.20min/128** before guard overhead; it is not a promised saving for apps needing additional settle/retry.
3. Batch transport without dropping predicates: preserve host-held verification; test expected boot in the same remote shell before each actual operation; preserve explicit serial, every subcommand status/output and no write retries. The standalone list+boot intervals scale to **18.89min/128**. Recovering50-80% would give **9.4-15.1min**, an assumption-based next-run scenario, not measured61b performance. A transport/interface change must be reviewed before the next frozen run; no current script was changed.
4. Use page/direction hints only to choose the next search path, then obtain a fresh exact-icon layout before clicking. Never borrow5ea coordinates for61b, and never cache ps/window/boot observations as if current. Keep layout-animation/failed-swipe ambiguity fail-closed.
5. Overlap host-only decoding, triage, source preparation and report assembly with board waits. Preserve per-app raw hilog collection before the next reset. Keep window bookends: their measured file span is too small to justify weakening them. Keep whole-file screenshot/run.sh SHA checks.

Savings categories overlap; do not add the guard ceiling, UI ceiling and screenshot wait. Caching immutable *local* bytes by SHA is safe; cached device hashes do not replace before/after observations. Same-board UI apps remain serial. No deployment guard, running script, acceptance threshold, or existing evidence was edited; only this new README and results.json were written, with no git action.

## Final61b source-map preparation

The preserved V1 `source-files.json` has **811** entries; **0** referenced local sources are missing. The current f28 template has **11/11** local member sources. Seven bind targets resolve to the corresponding member local source. The full resolution table is in results.json; paths are workspace-portable where supplied.

The remaining inputs are real61b metadata/UID and its regenerated provider plan, newboot `parameter-observation.json`, whole-file run.sh derivation, current composition, independent Boat admission, actual capture/UI and signoff. Stable sources can be prepared now. Final collection reuses `benchmark/2026-10-12-seal-snapshot-adapter/collect.py --groups <new61b-composed/groups.expected.json> --manifest benchmark/2026-10-09-demo-baseline/demo-manifest.json --extra-package org.westlake.imehost --extra-package com.Unity3d.BoatAttackDay --serial <61b> --hdc <pinned-hdc> --out <fresh>`, then the original `benchmark/2026-10-09-demo-baseline/t5/build_seal.py`. The5cd rehearsal needs only actual954 R5/UI, not a new5cd seal compiler.

Original R5 `collect_live` already emits `parameter-observation.json`; no custom WMS collector is needed. Its binary-safe adapter is SHA `64421012ff2bc905970a5d2d0dd72073755b81b6f42f8c182680fc91ef95ef34`. Do not execute the historical two-reboot `demo_seal_61b` workflow, and do not borrow the5cd source realization as61b observation.

The non-screenshot hash category contains 114 distinct literal remote fragments. Its repeated fragments and counts are retained in results.json. Immutable local-file hash caching and same-operation remote batching are candidates; changing the number/timing of actual device identity observations is not implied. The source-map missing count checks local existence only, not a new source-byte hash audit.

## Current adoption status

Implemented this round: static source mapping/parameter preparation and independent visual review run in parallel with the long hardware work. Transport batching, settled-layout reuse, and page-direction hints remain next-run proposals requiring measured validation. The assumed9-15min transport saving is excluded from the current ETA. The running runner, gates, and acceptance criteria are unchanged.
