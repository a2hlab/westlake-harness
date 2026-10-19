# CHECKPOINT — Durable manual icon reentry (61b), design before code

Date: 2026-10-19. Inner CC lane, worktree `analysis/toutiao-icon-reentry-20261019`.
This file is written **before** implementation per AGENTS.md ("先尽快写设计 CHECKPOINT 后编码")
and records the design plus the boundary tensions, so the outer loop can veto early.

## 1. Goal (from specs/toutiao-icon-reentry/*)

On the sealed 61b demo baseline, after Toutiao (the Route-B child) crashes, let a **manual
desktop→host icon tap** bring the feed back. Exactly one manual foreground transition starts
exactly one spawn. We do **not** diagnose or fix the random SIG11, do not touch the APK /
native / JAR, do not clear data, do not auto-consent privacy. The board is driven only by the
outer loop; this lane produces code + tests + docs, commits, does not push, does not touch the
device.

## 2. What the current sealed base actually does (evidence, not memory)

Base = `benchmark/2026-10-12-v1-seal-execution/capture-feed-package/payload/` (copied verbatim
into this worktree by the outer loop; watchdog sha256 `2b635ef1…`, entry `81dd0557…`). Launch
chain, read line-by-line:

- `boot-entry.sh` (init condition job): sources `config-common.sh`, verifies every `members.tsv`
  entry by sha256, copies them into `boots/$BOOT/` (a fresh per-boot dir, `mkdir` fails if it
  exists → **never overwrites an existing boot**), then `exec entry.sh`.
- `config-common.sh`: pins `ROOT=/data/westlake-demo/toutiao/recovery-attempts/r1-9763171a-preview`,
  verifies `startup.env` against `startup.expected.sha256`, requires `STARTUP_ENABLED=1` and
  `STARTUP_SERIAL=61b0657200000000000000000324012c`, host uid `20011206`, derives
  `AUTH_BOOT` from `/proc/sys/kernel/random/boot_id` at runtime (**no fixed expiry**), refuses on
  any candidate/historical `stop`.
- `entry.sh`: decodes a pinned JPEG through `screen-gate` before any launch, then **waits for the
  first manual host foreground window** (`while ! foreground_window_id`) — this is the first tap —
  re-checks `watchdog.sh` sha against a **hardcoded** constant (line 23) and `route-b-owner.sh`
  sha, then `exec watchdog.sh`.
- `launch-common.sh :26 foreground_window_id()`: `hidumper -s WindowManagerService`, grep the
  single `imehost0` row, return field `$4` (window id). WMS read failure / non-unique row / bad
  fields → **nonzero**. This is the manual-tap primitive.
- `watchdog.sh`: acquires an exclusive lock (no takeover of a stale lock), starts/validates the
  parent (`start-parent.sh`), then an attempt loop `while attempt < TT_MAX_ATTEMPTS(=3)`: one
  `spawn.sh` per attempt → readiness probe (`readiness-probe.sh`, pure read-only, 2 s) → inner
  monitor loop that captures frames into a **fresh private 0700 dir** and classifies feed/privacy.
  On child disappearance: `event process_exit; break` → `state RECOVERING` → **auto-respawn** with
  `sleep attempt*5` backoff, up to 3 attempts, then `RETRY_LIMIT` exit.

So today: tap icon → opens imehost (host) only; after the child dies the guardian **auto-respawns
≤3 times then exits**. There is no "wait for a new manual tap" path. That gap is this task.

## 3. Identity / safety invariants I must preserve (route-b-owner.sh)

- `rb_birth p` = PID + `/proc/p/stat` field 22 (starttime). Any PID reuse ⇒ birth differs ⇒ reject.
- `rb_owned p` = uid == owner uid (all four) AND exe is an exact Route-B alias AND exe sha ==
  `RB_SPAWNER_SHA` AND private-root `run.sh` inode == physical inode AND birth stable across the
  check. `parent_owned` additionally accepts uid `0:0:0:0`, and the parent **never receives a
  signal**. `child_owned` adds ppid==parent and private mount ns.
- Private capture gate: snapshot only into a brand-new `0700` dir whose owner file we verify; every
  frame re-checks boot, lock owner, stop, child identity (`capture_context`).
- IO failure on a control file ⇒ `io_fail`: keep the lock, best-effort mark `IO_FAILED`, exit 5.
  Never repair/clean the app on control-plane IO failure.

These are frozen behaviours; the reentry change must not weaken any of them.

## 4. Design of the change

### 4.1 Minimal, visible, testable surface

New candidate = base, with the launch tail of the guardian replaced by an **edge-triggered manual
reentry wait**. To keep the change both a *visible diff of one script* and *unit-testable without a
device*, the reentry state machine is factored into a **new** file `reentry-common.sh` built from
overridable seams. The derived `watchdog-reentry.sh` differs from base `watchdog.sh` only by:

1. sourcing `reentry-common.sh`;
2. after the first spawn's monitor loop breaks on real child exit, instead of the
   `RECOVERING`→backoff→auto-respawn tail, calling `rc_reentry_loop`;
3. collapsing the outer `while attempt<3` into the single first launch (attempt 0). The first
   launch path (lock, parent start, spawn, readiness, capture) is **unchanged** → "首次启动维持原链".

Everything else in the payload is reused byte-for-byte. The only other derived files are the
mechanical SHA/ROOT rewrites forced by the hash chain (§4.4).

### 4.2 Reentry state machine (`rc_reentry_loop`), fail-closed

In-memory edge detector, **no counter cap**, **quiet** (events only on edges/decisions, never per
poll → "不无限建观察文件"), no fixed deadline (loops until stop or boot change → "不固定expiry"):

```
host_fg_prev = 0            # rising-edge detector
hold = 0                    # sticky fail-closed after unknown child
loop:
  gates = rc_gates_ok       # boot unchanged, lock ours, no stop, parent owned, no PID reuse
  if stop present            -> STOPPED, return 0 (do NOT delete stop)
  if boot/identity bad       -> OWNER_REFUSED, retain lock, no signal to parent, return 2
  fg = rc_foreground_state   # "fg <wid>" | "none" | "error"
  case fg:
    error -> (WMS exception) no transition, consume nothing; sleep; continue   # fail-closed
    none  -> host_fg_prev=0; sleep; continue                                   # reset edge
    fg    -> if host_fg_prev==1: sleep; continue      # same episode already handled → consume
             host_fg_prev=1                           # rising edge = one manual tap
             if hold==1: event reentry_hold_fail_closed; continue   # sticky: never blind-spawn
             child = rc_child_state                   # alive|gone|unknown
             win   = rc_window_present                # yes|no|unknown
             if child!=gone OR win!=no:
                 event consume_live_or_window ; continue   # child alive / any window / unknown
                                                           # -> no TERM, no spawn, consume event
             if ! gates: event refuse_gate ; continue      # no spawn, no stop delete, no signal
             r = rc_do_spawn                          # reuses first-launch spawn+readiness+capture
             case r:
               ok      -> event reentry_spawn_ok      # child now alive; further edges consumed
               fail    -> event reentry_spawn_fail    # KNOWN no child -> wait for NEXT rising edge
               unknown -> hold=1; event reentry_spawn_unknown_hold   # fail-closed, never again
  sleep
```

Mapping to the five scenarios:

- **S1** child confirmed gone + parent ok: before any rising edge → 0 spawn; one rising edge →
  exactly one `rc_do_spawn` which runs the original readiness gate.
- **S2** child alive or hidden window + host gains foreground: `child!=gone OR win!=no` → consume,
  no TERM, no spawn.
- **S3** boot change / PID reuse / stop present / parent identity mismatch: `rc_gates_ok` fails or
  stop wins → refuse; never delete stop, never signal parent.
- **S4** ≥21 independent taps + one launch failure: loop has **no 20-cap** (that `20` is only the
  readiness probe's internal 2 s poll, in frozen `readiness-probe.sh`, untouched); after a `fail`,
  `host_fg_prev` stays 1 so no spawn occurs until the host loses and regains foreground (a *new*
  tap) → "失败后无新手点不重试". `unknown` is stickier (`hold`).
- **S5** real board screenshot: human review, outer-loop only.

"spawn 失败后未知 child 状态不要继续盲 spawn，明确 fail closed": `rc_do_spawn` returns `unknown`
whenever it cannot prove the child was *not* created (e.g. `spawn.sh` nonzero after emitting a pid,
or birth unreadable). `unknown` sets the sticky `hold` → no further spawns this boot, lock retained,
no signal. Only a clean `fail` (spawn proved no child, e.g. socket/parent precheck refused before
host_spawn) permits a spawn on the next manual tap.

### 4.3 Production seam implementations (device side, no awk/python)

- `rc_foreground_state`: wraps `foreground_window_id` (host foreground id) → `fg <wid>`; distinguish
  "host not foreground" (`none`) from "WMS unreadable/ambiguous" (`error`) by inspecting the
  hidumper rc and whether any WMS output was obtained.
- `rc_window_present`: any `imehost` window row in the WMS dump (foreground or hidden) → `yes`;
  clean empty → `no`; unreadable → `unknown`.
- `rc_child_state`: `rb_birth child` + `child_owned` → `alive`; proven gone (no dir / zombie) →
  `gone`; unreadable/ambiguous → `unknown`.
- `rc_gates_ok`: boot==AUTH_BOOT, lock owner == ours (exact bytes), no `stop`, `parent_owned`.
- `rc_do_spawn`: exactly the first-launch block (spawn.sh → readiness-probe → first capture
  confirm), returning `ok <pid> <birth>` / `fail <reason>` / `unknown <reason>`.
- Tools used: `hidumper grep wc sed cat cut stat readlink timeout sha256sum od sleep` — all already
  required by `boot-entry.sh`. **No awk, no python.** POSIX sh only (OH mksh/toybox compatible).

### 4.4 Hash-chain cascade (handled by the generator, not by hand)

Changing `watchdog.sh` → new file name `watchdog.sh` (candidate content) with a new sha ⇒ update:
`entry.sh` line-23 constant, `members.tsv` watchdog row (+ add `reentry-common.sh` row), then
recompute `members.tsv` sha → `STARTUP_MEMBERS_SHA` in `startup.env` → recompute `startup.env` sha →
`startup.expected.sha256`. Changing `config-common.sh` ROOT (new durable root) also changes its sha
→ `members.tsv` config row → same cascade. A deterministic generator does the whole cascade so the
on-device sha gates all pass.

## 5. New persistent ROOT, 61b / 5cd params

`boot-entry` refuses to overwrite an existing `boots/$BOOT` and the live sealed boot
`6944c37e-…` lives under the **old** root `r1-9763171a-preview`. The candidate therefore uses a
**new** root (default `…/recovery-attempts/r1-reentry-<tag>`), so its `boots/` tree is independent
and the sealed boot is never touched ("新 boot 存在不许覆盖"). The generator takes
`ROOT / SERIAL / OWNER_UID / OLD_STOP_SHA` as parameters; 61b defaults match `startup.env`
(serial `61b0657…`, uid `20011206`), and a 5cd variant only swaps serial/uid — no code change.

## 6. Default-disabled publication + outer runbook

The generator only **writes files**; it never deploys and never arms device execution
(`TT_RECOVERY_EXECUTE` is unset, no enabled plan is emitted; the composed package stays
`execution_enabled:false`, `device_calls:0`). It emits a per-file **hash manifest**, a **visible
unified diff** of every file that differs from the pinned base (base SHAs recorded, base never
modified), and `OPERATIONS.md` with the exact outer steps to (a) generate a fresh ROOT, (b) arm,
(c) deploy, (d) roll back.

## 7. Boundary tensions surfaced (none blocking)

1. Base payload dir was initially absent in the worktree; outer copied it in verbatim. Resolved;
   base is pinned by sha and never modified.
2. `entry.sh` hardcodes the watchdog sha, so the change necessarily produces a derived `entry.sh`
   (one-line visible diff). Acceptable and documented.
3. The reentry logic depends on device-only primitives (hidumper/snapshot/spawn) untestable on
   Mac. Resolved by the seam split: the fixture test drives the **real** state-machine control flow
   in `reentry-common.sh` with injected seams; the on-device primitive wiring is validated only by
   the human screenshot scenario (S5, outer loop).
4. "一次手点一次 spawn" requires an edge, not a level. Implemented as an in-memory rising-edge
   detector reset whenever the host is not foreground; WMS errors never fabricate an edge.

## 8. Test plan (Rust selector → shell fixture harness)

`tools/spec-checks/tests/toutiao_icon_reentry.rs` transcalls
`benchmark/2026-10-19-toutiao-icon-reentry/tests/run-reentry-fixtures.sh` (shell, no python/awk),
which sources the real `reentry-common.sh` with mocked seams and asserts:

- 21 independent taps each produce exactly one spawn (no 20-cap exit);
- a launch `fail` does not auto-retry until the next rising edge;
- a launch `unknown` sets sticky hold (no further spawns) — explicit fail-closed;
- WMS `error` fabricates no edge (no spawn);
- UID / boot change / PID reuse / existing stop / parent mismatch all refuse without deleting stop
  or signalling the parent;
- child alive or hidden window ⇒ consume, no TERM, no spawn;
- the quiet invariant: a no-change poll appends no event line.

Raw harness stdout is tee'd to `tests/last-run.log` and summarised into `results.json`.

## 9. Outer pre-review BLOCKERS (2026-10-19) and resolutions

The outer loop reviewed §1–8 before full coding and raised six substantive blockers. Recorded
here verbatim-in-intent with the resolution applied in this revision:

1. **Edge detector too weak.** `rc_host_fg_prev=0` start + "none arms on any non-host" treated a
   host-already-foreground loop start (post-crash) as a first tap, and did not require a real
   desktop→host move. → Replaced with an explicit tri-state **`UNARMED → DESKTOP_SEEN →
   HOST_CONSUMED`**. Only a *strict SceneBoard desktop focus row* (name + Pid + birth + UID + WinId
   verified) arms (`DESKTOP_SEEN`). Only from `DESKTOP_SEEN` does a *strict verified host focus*
   fire exactly one spawn, then `HOST_CONSUMED`. Any other/unknown focused window **cancels
   qualification** (→ `UNARMED`). The loop starts `UNARMED` and re-arms to `UNARMED` whenever the
   monitored child is confirmed gone, so a post-crash host-foreground never auto-restarts. New
   counterexamples added: host-already-foreground at start, notification→host (no desktop between),
   a stale/old desktop event before loop entry, and WMS error.
2. **`rc_window_present` counted any `imehost` row** → the host's own `imehost0` window would be read
   as a child window and block spawns forever. → Renamed `rc_owned_window_present`: matches windows
   to the **bound old child PID + the actual owned-child set** (incl. hidden windows). The host
   window is validated on a *separate* path (parent WID + host PID/birth/UID). An old child window
   still present ⇒ consume, **no TERM**.
3. **`rc_spawn=$(rc_do_spawn) || :` swallowed the rc**; a printed `ok` could pass on error. → The
   loop now captures the real rc and requires **rc==0 AND a single `ok <pid> <birth>` line with
   numeric pid+birth and no trailing fields**. Non-zero / multi-line / extra fields ⇒ not ok.
   `rc_after_spawn_ok` (the monitor) propagates identity / IO failures **upward to stop**; they are
   never swallowed.
4. **Tests must exercise real WMS parsing + gates**, not only a mock that returns `fg`. → Added pure
   parsers `rc_parse_focus` / `rc_parse_owned_window` tested against the **real WMS schema**
   (`WindowName DisplayId Pid WinId Type Mode Flag ZOrd …` plus `Focus window: N`), and a faked
   `/proc` tree exercising the real `route-b-owner.sh` UID / birth / namespace gate (`rb_owned`,
   reused verbatim). The original readiness-probe and private-capture code and the single-parent
   object are preserved unchanged.
5. **"5cd = only serial/UID" is false** (JIT / request / old-stop SHAs also differ). → This delivery
   ships **61b only**; I do not claim 5cd support. ROOT is parameterised; the generator's default is
   **`/data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r1`** (outer's fixed
   `icon-manual-*` whitelist). The outer loop owns the separate cfg deploy/rollback transaction;
   this lane ships only the package generator, the `source+diffs`, and the offline tests, and
   commits **all useful source including the small base members** so nothing depends on the main
   tree's untracked payload.
6. **Baseline already proven** (outer saw 61b online with the same child 13101 feed). No further
   study of networking or the random crash; this candidate does not claim to fix the crash.

## 10. Final state (post-integration, 2026-10-19) — supersedes stale paragraphs above

The design above holds; two implementation specifics changed during integration and the
reader should treat §8's "stdout" seam capture and §4.3/§8's earlier parser description as
superseded by this section:

- **Seam contract is current-shell variable return, not stdout capture.** The final
  `reentry-common.sh` (`43d7b073…`, adapter-owned) sets/reads `rc_focus_result`,
  `rc_owned_result`, `rc_spawn_result`, and `rc_classify_spawn` populates
  `rc_sres`/`rc_spawn_pid`/`rc_spawn_birth` in the current shell so child/birth/seq and
  fatal exits persist (no `$(...)` subshell). `rc_child_state` remains stdout; a child
  state of `invalid` is a fatal refuse. Focus `error` now re-arms to `UNARMED` (a gap
  cannot prove a desktop→host transition). Tests in `tests/run-reentry-tests.sh` bind to
  this exact contract.
- **Parser is the outer-reviewed file-based whole-dump validator** (`reentry-seams.sh`
  `febc7094…`): it validates header/footer/focus presence, anchors a standalone
  `Focus window:` line (never the `All Focus window:` heading), requires `Total ≥ visible`
  (not `==`), rejects malformed/truncated rows (not skip→no), counts hidden `ZOrd=-1`
  rows for owned windows, and rejects a hidden focus. `tests/run-parser-tests.sh` proves
  it against the real locked 61b dump.
- **Generator & ROOT delivered.** `generator/derive-candidate.sh` reproduces the base
  from tracked V/R/base-ref (19/19 pins), overlays the reentry change, and emits the
  disabled `candidate-payload/` (21 files) with the full members→startup→startup.expected
  cascade. Default ROOT `/data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r1`.
- **Restart/first-launch boundary (board fact 2026-10-19).** Child 13101 exited (uptime
  22640); the OLD watchdog auto-retried then `START_FAILED`; parent 11444 (birth 107387)
  still alive. The candidate refuses socket/parent takeover by design; the only execution
  path this round is a fresh boot (no reviewed attach implementation exists, so none is
  offered), never clearing the socket or signalling the parent (OPERATIONS §4). Not a
  regression of this candidate (not deployed).
- **Deploy transaction correction (outer clean-checkout review).** The real transaction
  `benchmark/2026-10-19-toutiao-icon-deploy/prepare.py` + `deploy.py` keeps the existing
  `/system/etc/init/01_westlake_u13_toutiao.cfg` (service `westlake-u13-toutiao-overlay`,
  trigger `sys.westlake.demo.u13.ready`, permissions) and only repoints the boot-entry
  path to the new ROOT; it requires an armed payload and rejects any other cfg change.
  The payload's `recovery.cfg` (with its own service/trigger) is a reference artifact and
  is NOT installed; OPERATIONS §2/§3/§5 were corrected accordingly. Rollback restores
  `before.cfg` and never deletes the candidate ROOT evidence.
