# 2026-10-19 — Toutiao durable manual icon reentry (61b)

Evidence-first. Offline only; **no device actions were taken by this lane**. The
real-board screenshot acceptance is the outer loop's job (spec scenario 5).

## What was wrong before

The sealed 61b guardian (`watchdog.sh` `2b635ef1…`) auto-respawns the Route-B child
up to `TT_MAX_ATTEMPTS=3` after a crash and then exits (`RETRY_LIMIT`). There was **no
path to recover via a manual desktop→home icon tap** once the guardian gave up. Board
fact 2026-10-19: child `13101` exited at uptime 22640, the old watchdog auto-retried,
hit `START_FAILED`, and the original parent `11444` (birth `107387`) stayed alive — a
dead feed with no manual way back.

## What this delivers

A **separate, disabled-by-default candidate** that keeps the first-launch chain
unchanged and, after the child exits, waits for a genuine **desktop→host icon tap** and
spawns exactly once per tap — preserving every ownership guard, the readiness probe, and
the private capture gate. It does **not** touch the APK/native/JAR, does not clear data,
does not auto-consent privacy, and does **not** claim to fix the random SIG11.

Change surface (visible diffs in `candidate-payload/diffs/`):

- `src/reentry-common.sh` (`43d7b073…`) — the reentry state machine. Replaces the base
  auto-respawn tail with an explicit `UNARMED → DESKTOP_SEEN → HOST_CONSUMED` detector:
  only a verified SceneBoard desktop focus arms, only then does a verified host focus
  fire one spawn; child-alive / any owned window / unknown / WMS-error never fire; a
  launch `fail` waits for the next tap; an `unknown` child status is a sticky fail-closed
  hold; no 20-cap; quiet between taps; no fixed expiry.
- `src/reentry-seams.sh` (`febc7094…`) — a pure, device-free WMS parser (whole-dump
  schema validation, standalone `Focus window:` anchoring vs the `All Focus window:`
  heading, `Total ≥ visible` rather than `==`, hidden `ZOrd=-1` still counts for owned
  windows, malformed rows fail instead of being skipped).
- `src/watchdog-reentry.sh` (`bd2f83be…`) — base watchdog with frozen helpers verbatim;
  first launch unchanged, then the reentry loop; file-based WMS capture; the host window
  is validated separately from owned-child windows (the host pid is never counted as a
  child).

The three `src/` files were cross-reviewed by the outer loop (`OUTER-ADAPTER-READY.json`;
parser-review 18+14, adapter sh/dash 18+18, cfg 14, remote/rollback 8, identity edge 1 —
all PASS). This lane owns the parser, generator, inputs, tests, docs and spec selector.

## Numbers (offline, this lane)

| check | result |
|---|---|
| WMS parser tests (`tests/run-parser-tests.sh`, real locked dump + synthetics + error paths) | **21 passed, 0 failed** |
| reentry state-machine tests (`tests/run-reentry-tests.sh`, final seam contract) | **29 passed, 0 failed** (sh and dash) |
| generator smoke + SHA cascade linkage | **PASS** (21 files, cascade linked, disabled) |
| Rust selector `cargo test --test toutiao_icon_reentry` | **ok, 1 passed** |
| `agent-spec lint t1-reentry.spec.md` | **100%** (det/test/cov 100%, ≥0.7 gate) |
| generator base-pin verification | **19/19 base files match pins** |
| device calls | **0** |

## Rules established this round

1. **A crash leaves the host foreground**, so manual reentry must be a *sequence*
   (desktop→host), not a host-foreground level. An explicit tri-state arming detector is
   mandatory; a bare rising edge is a false trigger.
2. **The host window is not a child window.** Owned-window detection matches the bound
   child PID / owned-child set; the host `imehost0` window is validated on a separate
   identity path and never counted as the child.
3. **Fail closed on indeterminate spawns.** A spawn result is `ok` only with rc 0 and
   exactly one numeric `ok <pid> <birth>`; anything that reached `host_spawn` but cannot
   prove the child state is `unknown` → sticky hold, never blind-respawn.
4. **Never work around a stale socket/parent.** The candidate refuses socket/parent
   takeover by design; the only execution path this round is a **fresh boot** — never
   clearing the socket or signalling the parent, and no ad-hoc attach (no reviewed attach
   implementation exists in this delivery; see `OPERATIONS.md §4`).
5. **Deploy reuses the existing init cfg.** The real transaction
   (`benchmark/2026-10-19-toutiao-icon-deploy/prepare.py` + `deploy.py`) keeps
   `/system/etc/init/01_westlake_u13_toutiao.cfg`'s service `westlake-u13-toutiao-overlay`,
   trigger `sys.westlake.demo.u13.ready` and permissions, and changes **only** the
   boot-entry path to the new ROOT; the payload's `recovery.cfg` is a reference artifact
   and is not installed. Rollback restores `before.cfg` and **never deletes** the candidate
   ROOT evidence (`OPERATIONS.md §3, §5`).

## Layout

- `src/` — the three reviewed candidate sources.
- `generator/derive-candidate.sh` + `base-pins.json` + `base-ref/` — deterministic
  payload generator (host-only, no device), runnable on a clean tracked checkout.
- `candidate-payload/` — the committed **disabled** payload (21 files) + `MANIFEST.sha256`,
  `generation.json`, `diffs/`, `build.log`, `build-command.txt`, for outer `prepare.py`.
- `tests/` — `run-parser-tests.sh`, `run-reentry-tests.sh`, `run-all.sh`, `outer-fixtures/`,
  `last-run.log`.
- `OPERATIONS.md` — outer deploy/arm/rollback runbook + restart/first-launch boundary.
- `CHECKPOINT.md` — design + boundary-tension log.
- Spec selector: `tools/spec-checks/tests/toutiao_icon_reentry.rs`.

## Remaining pending (outer / real board)

- Spec scenario 5: real-board screenshot acceptance (crash → manual icon tap → feed; and
  reboot → manual tap → feed) with process identity + capture receipts.
- Confirm on 61b the SceneBoard desktop WindowName/UID and host identity used by the
  production focus seam (evidence already gathered in `OUTER-ADAPTER-READY.json`
  `window_identity_evidence`; desktop uid 20010018 / `com.ohos.sceneboard`, host uid
  20011206 / `org.westlake.imehost`).
- Reentry polling is 1-second integer sleep; an extremely fast home→icon transition can
  be missed (no auto-retry; a further manual tap recovers).
