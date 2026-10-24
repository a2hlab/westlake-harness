# T141 reentry retain entry: two software boots accepted

Status: **candidate retained on 61b after two independently reviewed software boots.** The accepted result is `retained_reentry_validated_av_pending`, not a full audio/video or physical-power seal. Actual run summaries, original images, receipts and the outer signoff are in `benchmark/2026-10-25-61b-reentry-delivery/`. Historical plan/receipt fields remain unchanged.
The entry is handed to the single device writer, who runs it under a separate outer receipt per phase.

Base: **`execute_v7.py`** (sha `0658440f…`, outer-verified 14 checks; `steps_v7.json` `22386f2b…`).
Earlier drafts were diffed against v6; v7 already carries the lineage selector, cat maps and the early recovery poll.

## What was wrong before (why this delta exists)
- v6/v7 decide samehost/recreated assertions by **stage name**.
  A suggested `second-samehost` label would silently skip them. Here every stage carries an explicit
  `stage_kind` (`firstopen|samehost|recreated|restore`); assertions key on the kind, never on the label.
- v6 read review fields without a schema check (a clock receipt without `swipe` -> `KeyError` -> needless recovery).
- v6 picked "the" child with `one(name)`; real 61b shows a same-name descendant (7331 main, 8080 descendant).
- v6 had a single window that always rolled back; T141 needs two software boots and retention on success.

## Delta vs v7 (`v7-to-retain.diff`; includes the moved idle block)
0. **Rollback restore stage = verbatim v7 early observation**: after the icon click, read-only identity poll every
   1.5 s for up to 90 s and strict `bind` as soon as the main child appears (old baseline processes exit fast; a fixed
   30 s sample missed them; v7 bound main 29773 in window 2688cd). Candidate three stages keep 5/30/60/90 s samples.
1. **Main child + lineage**: `select_main(identity, allow_empty)` identical to v7 (same logic as outer `recovery_lineage.py` `a18e4748…`):
   exactly one `com.ss.android.article.news` whose PPID is the unique `appspawn-x`; every other same-name
   process must reach it by PPID chain, same UID, unique PID, acyclic. `bind` verifies main + every descendant
   (main must map the bridge; descendants are `not_mapped` or the same object), with a **full** identity equality
   bracket and the candidate `published` dev/inode assertion kept. Maps are read with
   `test -r /proc/PID/maps; cat /proc/PID/maps` and filtered host-side in Python (61b has no `awk`, rc 127).
1a. **Startup transient + appspawn-x root rule**: right after a click the earliest sample may contain only the host
   (appspawn-x not started) or host+appspawn-x without a child. `select_main(allow_empty=True)` therefore returns
   `None` when no child exists **before** looking up the parent; that is normal "not started yet", not a failure.
   The parent is `parent_root`: the unique `appspawn-x` with PPID 1 and UID 0 (RUNBOOK unspecialized-children rule);
   other appspawn-x-named unspecialized children stay in the raw identity; zero or two roots are rejected. Any present
   child, and every real `bind`, still requires the root and the main child strictly. Idle admissions compare the root.
1b. **Bounded bind resampling (sampling race only)**: v7 s30 showed boot/host/parent/main unchanged while a
   same-name worker descendant appeared between the before/after identity reads, and the full-table equality stopped
   the window. `bind` now compares core identity (boot, host, appspawn-x, main child full records) every round; if
   only the legal descendant set changed it takes a complete fresh read-only sample, at most 3 rounds within 20 s,
   and accepts only a round with full before==after identity and every descendant's maps verified. Core change,
   wrong SHA/inode/metadata and unknown lineage still stop immediately. Rounds are recorded in `binding.json resamples`.
   Final evidence is not relaxed; the executed entry and actual per-frame binding receipts are pinned in the delivery package.
1c. **Honest restore when the old baseline does not start (`restored_idle_exact_object`)**: per the current t3 spec
   (`e797dbbd…`, line 11), if the restore stage ends with exactly "no actual baseline mapping within90s early
   observation" the window may still close: under its own lock two identity points 5 s apart with no article process
   and stable boot/host/unique appspawn root, target full stat/SHA/metadata equal to this window's preimage, recovery
   boot different from candidate boots, system object restored, final image retained, power restored before unlock.
   Result: `rollback=restored_idle_exact_object`, `baseline_actual_mapping_verified=false`, `mapping_now=not_running`,
   `app_health=not_claimed`, `historical_provenance` (admission mapping or idle source; boot2 takes it from the boot1
   handoff) and receipt `restored-idle-exact-object.json`. Any other restore error, an article process, role drift or
   object drift stays `recovery_required` (lock kept). An actual restore bind still writes `baseline_actual_mapping_verified=true`.
   The idle admission accepts a restored source only when `source_kind=restored_idle_exact_object` is pinned in steps,
   and then only `not_running`. Accepted shapes: the **canonical T136 receipt** (`status=restored_idle_exact_object`,
   `released=true`, `baseline_actual_mapping_verified=false`, `mapping_now=not_running`, no maps/health claim,
   `identity_before`/`identity` roles stable without article process), replayed unmodified from the real
   `restored-idle-binding-t136.json` (`c1697eb7…`); or a T141-own `kind` receipt only together with its released
   `result.json` pinned as `source_result_sha256` (orphan receipts refused). Same boot/host/appspawn root/object still required.
   Article detection uses the package prefix (`com.ss.android.article.news*` in the identity collector,
   `startswith` in admission/restore checks), so colon subprocesses never count as "nobody running".
1d. **Content-after review aligned to T136 v9** (`execute_v9.py` `30cd6564…`): no content touch is sent when fewer
   than 60 s remain in the 900 s operation budget; the content-after image gets its own 60 s review capped at
   `start+900` (recovery reserve untouched); after `usable` the identity is re-read and boot/host/appspawn root/main
   child (pid, birth, uid) must be unchanged, while a legal same-name descendant change is allowed.
1f. **Content-after multi-frame observation (tool only)**: one touch, then read-only frames inside the same 60 s window
   (capped at `start+900`), at least 2 s apart, each with its own label/hash/review. `unknown` or `feed` with
   `changed_from_feed=false` means no change in that frame yet; any other verdict, core identity drift after any frame,
   a review timeout or the window end fails; only a changed `usable` frame passes. Basis: in ffd0d4 recreated the tap
   was handled and ArticleInflowActivity resumed about 1 s after UP while the single 2 s frame fell inside the switch.
   This does not establish that the cause is timing only; if the new activity's window was shown before a still-unchanged
   frame, surface binding/top visibility must be compared next. Runtime, stages and two-boot criteria are unchanged.
1e. **Bounded layout re-dump for one known UITest transient**: attempt 1 is the original 15 s dump. Only local rc0,
   empty stderr, none of the `call()` failure markers, remote rc1 and a body exactly equal to
   `DumpLayout failed:Get window nodes failed` may be re-dumped: at most 2 more attempts within 10 s after attempt 1
   returns, 1 s apart, each call timeout clipped to the window/operation budget left (not started below 2 s); worst case
   15 s + 10 s. Each attempt uses a new run-unique file; raw stdout/stderr/rc of every attempt stay in its receipt and
   `result.layout_attempts`. Any other outcome is refused immediately. Identity/maps/review logic is unchanged.
2. **Review schema before use, by context** (`validate_review(r, context, allowed_touch)`):
   `desktop` feed = Home only (no touch fields); `stage` feed needs `touch_kind` + `touch_coordinates`;
   clock/Recent always need `swipe[4]`; `content` usable needs `changed_from_feed: true`;
   `closeout` needs `closeout_ok|closeout_reject`. A bad receipt is logged once in `review_errors` and polling
   continues; it is an image-review error, never an application failure.
3. **Touch rule**: per boot, the three stages must include >=1 swipe and >=1 content click, each followed by a
   `usable`+changed review. When remaining stages equal the missing kinds the entry prints `TOUCH_REQUIRED`
   and accepts only those kinds. Three scrolls never pass. Kinds are recorded in `result.stage_touches`.
4. **Close-out final image is consumed**: `closeout_ok` -> `closeout_review=passed`; `closeout_reject` ->
   failure path (exact rollback); review timeout -> `pending_outer_signoff`, never auto-pass.
5. **Two windows**: `--phase boot1` publishes the candidate, reboots, runs firstopen/samehost/Recent/recreated,
   closes with the candidate in place and writes `boot1-handoff.json`. `--phase boot2` requires that handoff
   and a released boot1 result (and boot1 close-out passed or outer-signed), reboots again (boot != boot1),
   runs `second-*` stages and either retains or performs the v6 exact rollback.

## Result semantics
| outcome | runtime_result | retain_eligibility |
|---|---|---|
| boot1 ok | `boot1_three_stages_passed_candidate_in_place_pending_boot2` | n/a (boot2 needed) |
| boot2 ok, close-out reviewed | `retained_reentry_validated_av_pending` | `granted_av_pending` |
| boot2 ok, close-out review timeout | `retained_reentry_closeout_review_pending` | `pending_outer_signoff` |
| any failure, restore bound | `experiment_stopped`, `rollback=verified`, baseline actual mapping verified | none |
| any failure, baseline never starts | `experiment_stopped`, `rollback=restored_idle_exact_object`, mapping `not_running` (not verified) | none |

`speaker_audio`, `video_audio_acceptance`, `t4_full_seal` stay `pending`. This is not a full seal; t4 unchanged.

## Initial writer plan (historical; see executed plan below)
1. Place `.private/t141-retain-input/candidate.so` (`3291f76d…`) and `rollback.so` (`b0e5602a…`).
2. `idle_exception` is pinned to v7 window 2688cd `baseline-early-17-binding.json` (`457d7b4b…`, object 66352/560578).
   If the v7 08 window leaves a newer restored binding, the outer repins it in `steps_retain.json` (steps SHA only).
   The path is repo-relative, so the entry must run in the worktree that holds that private run directory.
3. `python3 execute_retain.py --phase boot1 --outer-receipt <r1>`; receipt: decision, serial, phase,
   entry_sha256, steps_sha256, candidate_sha256, rollback_sha256, idle_source_sha256.
4. `python3 execute_retain.py --phase boot2 --outer-receipt <r2> --boot1-handoff <run>/boot1-handoff.json`;
   receipt adds boot1_handoff_sha256 (+ boot1_closeout_signoff_image_sha256 if boot1 close-out was pending).
Budgets per window: 900 s stop new work, 1200 s close-out/recovery start, 1800 s release.

## Inputs required for a new execution window
- `idle_exception` may need a repin after the v7 08 window; when the peer publishes its real restore receipt SHA,
  repin `source`, `source_sha256` and `source_kind=restored_idle_exact_object` together (steps SHA only).
- The two `.so` inputs are not in this repo; the writer supplies them.
- `select_main` and the recovery early poll are v7 verbatim; `bind` is v7 plus the bounded resampling loop
  (the executed implementation is pinned by SHA in the delivery signoff).
- Residual race not covered by the rule: a descendant exiting during its own maps read is a remote read failure and
  stops the window (strict, same as v7).

## Tests
`python3 tests/test_retain_dry_run.py` (81 cases, no device; 4 replay the real private T136 receipt and skip if it is absent). Selector:
`cargo test --test host_window_reentry_retain` (`host_window_reentry_retain_receipts`).
Synthetic tests prove control flow only, not deployment, rollback or visual success.

## Executed plan and current deployment

The current `steps_retain.json` is the exact SHA6614eafe plan executed in successful boot1 b8eafe and boot2 e42601. It pins an earlier restored baseline as historical admission input; that baseline is no longer the deployed candidate. Source, input hashes and outer receipts are preserved for replay/audit, not permission to blindly rerun an old plan. `final-signoff.json` in the delivery directory binds the retained object, OpenHarmony version and rollback basis. The native candidate and observation entry were unchanged between the two accepted boots.
