# t13 5cd owned-child-reentry — blueprint/contract narrow review (4 axes)

Reviewed (read-only, api-progress-peer commit `8af35a66c2`):
- `benchmark/2026-10-20-5cd-owned-child-reentry/BLUEPRINT.md` sha `dd1b204a44c1c4e173c2dae0921a3dbaa184aaa14014a55890acc1e5b08de822`
- `specs/toutiao-video-playback/t13-5cd-owned-child-reentry.spec.md` sha `8e53271faf39c8c535bcd582326f2d5183c2fa3ad87d6dce1e825de17d4dba6b`
Scope = **blueprint/contract only** (executor not implemented; base5 implementing). No device, no push.

## Verdict: **NO BLOCKER on the blueprint.** All 4 axes sound. 6 implementation pins (D1,D4 state-now).

## Axis 1 — exact child adoption, zero first-round spawn — SOUND
Preflight/apply require child **31210/birth7485570**, parent **19163/7265322**, boot **0525bb05**, child
UID **20011300**, SceneBoard UID **20010017**; dead/replaced/drifted/ambiguous child ⇒ refuse, no PID
discovery substitutes another child (BP §1,§2; spec 决策/scenario `adoption_refuses_drift`). Derives the
original R2 `if TT_CHILD_PID` adoption branch (lines 506-512) with an explicit positive fixed-child
requirement before it and the missing-child else as a **refusal** (not `do_one_launch`); `child_owned`
+ seq0→1 + instance + `monitor_child` **without spawning**; entry admits **exactly this owned child**
(spec `adopts_without_spawn`: external spawn calls = 0). ✓

## Axis 2 — seq1 adoption / seq2 unique icon reentry — SOUND
Completion threshold moved from T12 `seq>=1` to **`seq>=2`**: adoption = instance1, the only later
successful spawn = instance2; sticky unknown hold after an entered failed spawn, no retry, no
pre-launch auto-restart (BP §3; spec 决策/scenario `one_reentry`,`stop_deadline`). The STOP-crosses-sample
guard "不因seq1的收养计数提前停止；seq2不再接受新spawn" correctly prevents (a) adoption prematurely
tripping completion and (b) a second spawn after seq2. ✓

## Axis 3 — one rb_signal TERM, unknown ⇒ no resend — SOUND
Exit mode fixed before execution; natural = no signal. term-once: re-verify receipt+lock+deadline+boot
+parent **and actual child_owned immediately before** `rb_signal 31210 7485570 TERM` **once**; dispatch
intent recorded **before** the command so timeout/lost-receipt cannot retry; no parent/group/alt-PID
signal, no KILL escalation, no auto-resend; **TERM rc0 ≠ exit evidence** (unconfirmed ⇒ unknown
close-out); natural exit after adoption ⇒ observe, no TERM; absent at preflight ⇒ refuse (BP §4; spec
决策/scenario `signal_exact_child`,`exit_classification`). Mirrors T12's proven guardian-TERM discipline. ✓

## Axis 4 — STOP deadline + awake restore — SOUND
600s includes observation+cleanup, guardian uptime deadline reserves 60s; post-deadline recovery only
same-receipt STOP/awake-restore (no extra UI/TERM/spawn); read original Timeout/Override, temp awake
`86400000`, restore original Override + verify Timeout unchanged; failure ⇒ retain lock +
`recovery_required`; **stop only the new guardian** (exact PID/birth/argv), **preserve parent, the NEW
child, and app data**; no cfg/runtime/JAR/APK replace or reboot (BP §6; spec 决策/scenario `cleanup`). ✓
(Correct T12 divergence: T13 ends with a live new child — cleanup must not kill it.)

## Implementation pins for the code review (D1,D4 = state explicitly before code)
- **D1 (Axis 1) — adoption ownership proof.** `child_owned` at adoption must establish child
  **ppid==19163 + private namespace == parent's**, not only pid/birth/UID/exe. BP §4 flags that
  `rb_owned` alone does not establish ppid/private-ns — adoption (which enters monitor with no signal)
  needs the same proof; the blueprint guarantees it for TERM but not explicitly for adoption. Make it
  explicit so a same-named look-alike cannot be adopted.
- **D2 (Axis 1) — exact-allow-one.** The T13 `processes()` replacing T12's reject-all must assert
  **exactly** child `31210/7485570` and **reject 0 / ≥2 / ambiguous** — the #1 code item.
- **D3 (Axis 2) — seq accounting.** Adoption sets seq=1 (no spawn, must not trip completion); one spawn
  *attempt* (success OR entered-fail) ⇒ seq=2 ⇒ stop; sticky hold blocks a 3rd. Verify an entered-fail
  spawn still reaches seq2 (so FOREGROUND_HOST_NOT_READY on the icon ⇒ hold+stop, never auto-retry).
- **D4 (phase-scoping) — the exact-`31210` gate is PRE-reentry only.** After seq2 a **new** child
  (≠31210) is expected; do not re-assert the 31210 identity against it. The new child is validated by
  new-PID/birth + readiness + owner (BP §5); ensure stop/restore do not re-run the 31210 `processes()`
  gate (by then the new child exists).
- **D5 (Axis 3) — single-use TERM receipt** consumed/recorded before dispatch (idempotent); a re-run,
  timeout, or lost receipt must not resend; `kill` rc0 is not exit proof.
- **D6 (Axis 4) — cleanup target.** Stop only the new guardian by exact PID/birth/argv; never signal
  parent/new-child/group; restore `-o` original Override, verify Timeout unchanged; recovery parent=False.

## ACTUAL-CODE VERIFICATION (landed isolated tree) — **NO REMAINING BLOCKER**
Reviewed real code: `derive.py 874c2db6813840b384113f789ecf5abe27eb2abade127a5bd2410e6547f5ac00`,
`tool.py 279fa626a4e6e2057f5fefdd0d62f5b14be8a2b688bb2ea6d5f32af73c7dbc3e`,
`ui.py 7f094f42acf8abb9952079b3bd45154374c9698e93d53c921a7c302636697f85` (author: 18 Python + 7 Rust
passing; final fixed SHA to be reported by author — re-confirm if it differs). All D-pins resolved:
- **D1 ✓** — `child_owned()` (watchdog-reentry.sh:96) proves birth bookend + `rb_owned` (exe-SHA +
  run.sh private-inode view) + `mnt` ns ≠ init (**private namespace**) + **ppid=="$parent"** from
  `/proc/$p/stat`. `ownership_probe` runs `parent_owned 19163 7265322; child_owned 31210 7485570;
  test rb_owned_pids == 31210`. The blueprint under-stated it; the code does the full proof.
- **D2 ✓** — `processes()` requires any `com.ss.android.article.news` line to be PID `31210`
  (`need(pid==CHILD)`), `ownership_probe` asserts `rb_owned_pids == 31210` (exact, rejects extra), and
  `entry.sh` admits `[ rb_owned_pids == 31210 ]`; any guardian/entry process rejected. `processes()`
  runs only in preflight/apply (pre-arming).
- **D3 ✓ (reframed per outer)** — uniqueness = durable `spawn.intent` (`set -C` noclobber) +
  existence-refusal **sticky hold** (derive.py:40-46), NOT a faked seq. `seq` stays the original
  **success** counter: adoption→1, successful spawn→2, `rc_stop_present` threshold `seq>=2`. A failed
  first spawn leaves `spawn.intent` so the next external attempt refuses — one attempt, original
  success-count semantics preserved. (I withdraw the earlier "entered-fail reaches seq2" wording.)
- **D4 ✓** — the fixed-`31210` check lives only in the adoption branch; `processes()` is pre-arming
  only; the post-reentry new child (≠31210) is validated by new-PID/birth + readiness + owner.
- **D5 ✓** — `term-once.sh`: `adoption_guard`→`child_owned`→single-use `term.intent` (`set -C`)→
  `adoption_guard`→`child_owned`→`rb_signal 31210 7485570 TERM` once; tool status
  `TERM_SENT_EXIT_NOT_PROVEN` (kill rc ≠ exit). `rb_signal` re-verifies birth+ownership before `kill`,
  exact PID only, no group/parent/alt/KILL/resend. UI one-icon is likewise gated by `t13_adoption_guard`
  + single-use `icon.intent` (ui.py:79,84).
- **D6 ✓** — `stop` TERMs only the recorded guardian pid/birth/cmdline==`watchdog.sh`, bounded confirm,
  preserves parent + **new child** + app data; `restore` `-o` original Override + `read_power()==original`
  + old-7-control + cfg/run close recheck.
- **Extras** — `apply` proves the actual adoption (`adopted == guardian+seq1`, 131-137) before `ARMED`,
  not just nohup; guardian deadline bounded within the window (`up+60<deadline<=up+left`, 115); exit_mode
  + `implementation_pins` (derive/tool/ui/source-pins SHAs) receipt-bound; `shell_guard` live-parent
  bookend on every forward command; holder+ISO lock binding; evidence-first + noclobber + SHA-readback.

Feed/video-cover ≠ playback (human-reviewed); mechanical pass ≠ feed. No device operation; no new gates
added (per outer). **tool.py scope + blueprint axes: ADMITTED, no remaining blocker.**

token t13-review-ready
