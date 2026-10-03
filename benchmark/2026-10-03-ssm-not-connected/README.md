# chessclock's session wall: `createSession: Not connected to SceneSessionManager` — a connected-then-stale race, unique in the corpus

#90, offline, no board. chessclock's terminal `InvalidDisplayException` traces to `OH_WindowMgrClient createSession:
Not connected to SceneSessionManager` → `wsErr 1005` → `addCode -9`. This separation-tables the marker across all U12/U13
hilogs, times chessclock's occurrence, and judges bridge-timing vs chessclock-specific. (`evidence/separation-table.txt`
= the corpus count; `evidence/chessclock-timeline.txt` = the timeline + WMClient internals.)

## ① Separation: the marker is chessclock-only (1 of 1849 hilogs)
Swept **1190** run `hilog.txt` under `westlake-harness-u7-executor/benchmark` (U12 + U13) + **659** under
`westlake-inputs/generations`. The marker `createSession: Not connected to SceneSessionManager` occurs in **exactly one
distinct key**: `cv2-com-chessclock-android` (U13, 5cd, window1) — all other grep hits are the C++/strings **source** that
emits the string, not run logs.

| group | keys with the marker |
|---|---|
| lit | **0** |
| white (other than chessclock) | **0** |
| dead | **1** — chessclock (terminal `InvalidDisplayException` + process died) |

So the marker is **non-lit** here — but n=1, so it is a single data point, not a proven population discriminator; it does
confirm the marker never co-occurs with a lit outcome in this corpus.

## ② Timing/thread — and the decisive lit contrast
chessclock (`evidence/chessclock-timeline.txt`): connect logs **"Connected to SceneSessionManager through official
SessionManager route"** on worker tid 7852 @08.884 (and on main tid 7829 @08.377); process launch
(`nativeOnScheduleLaunchApplication`) @08.913; `createSession` on tid 7852 @09.203 → **"Not connected"** (~**0.29 s** after
launch); **no WMClient disconnect** in between, **no reconnect** after → terminal.

**Decisive refinement (lit contrast):** helloworld (lit) emits **0** markers and reaches `createSession: success` **on a
worker tid too** (5486, main=pid 5461). So a **worker-thread createSession is not the defect** — lit keys do it on workers
and succeed. chessclock's signature is **not** "worker thread" and **not** "never connected": it is
**connected-then-stale** — connect logged success, then by the time createSession ran (0.29 s later, same tid) the SSM link
(`ssmProxy_`) was already unset, with **no retry**.

## ③ Mechanism — bridge timing/retry gap (surfaced by chessclock's early createSession)
`OHWindowManagerClient::getInstance()` is a process **singleton** (shared `connected_`/`ssmProxy_`); `createSession`
guards `if (!connected_ || ssmProxy_ == nullptr) → "Not connected"` and **fails immediately — no wait, no retry, no
re-connect** (bms/src; the deployed WMClient is newer — it logs "official SessionManager route" ×4 vs the source's "legacy
via SA" ×0 — so the deployed guard is read from the hilog behaviour, not this stale source). The deployed connect logs
"Connected" when the **SessionManager route** is established, but the **SceneSessionManager proxy** `createSession` requires
is populated by the async **WMSConnectionStatus** callback (the WMS side broadcasts `NotifyWMSConnectionStatus: wms is
already connected, notify client` periodically). chessclock builds its window **unusually early** (createSession at resume,
0.29 s after launch, right after an onCreate that stalls on ringtone/settings/MediaPlayer) → it **raced ahead of the proxy
population** → `ssmProxy_` null → "Not connected"; and because createSession neither waits/retries nor forces a reconnect,
the single early createSession fails outright → `wsErr 1005 → addCode -9 → InvalidDisplayException → process death`.

**Verdict:** a **bridge timing/retry gap** (createSession fails immediately on a not-yet-populated/stale SSM proxy instead
of re-acquiring it) **surfaced by chessclock's unusually early window creation**. It is **not** the worker thread (lit keys
succeed on workers), and it is unique in the corpus because chessclock is the only app whose createSession lost this race.
(Honest limit: with no disconnect logged and n=1, "async-population race" vs a chessclock-specific state reset is not
fully separable from logs — but the fix below is robust to either, since it re-acquires the proxy regardless of why it is
null.)

## Minimal fix + prediction
**Minimal fix (deployed WMClient `oh_window_manager_client.cpp`, `createSession` guard — cc-t3 / window-bridge owner):**
make `createSession` robust to a not-yet-populated/stale SSM proxy — when `!connected_ || ssmProxy_ == nullptr`, **re-acquire
and retry once** (call `connect()` / re-`GetSystemAbility(SCENE_SESSION_MANAGER_ID)`, with a short bounded wait for the
WMSConnectionStatus population) **before** returning the failure, instead of failing immediately. Equivalently, populate
`ssmProxy_` synchronously at connect() time rather than relying on the async callback. This closes the race for any app
that creates its window early (chessclock and any future one). Rollback = revert the retry block.
- Not the worker-thread (no change there — lit keys already succeed on workers).
- Note the `addCode=-9` is correctly surfaced by AOSP as `InvalidDisplayException`; the fix is upstream (get a valid SSM
  proxy), not in the AOSP mapping.

**Prediction (first-fatal):** with the retry/re-acquire, chessclock's createSession obtains the proxy → the window attaches
→ no `InvalidDisplayException`; chessclock moves past the session wall. (Its earlier `nativeConsumeConnectionFailure` NSME
during `MediaPlayer.<clinit>`/ringtone was non-terminal — onCreate still reached resume — so the session fix should let it
reach UI; see `u13-unowned-singles` for that secondary JAR-decl fix.) Lit likelihood medium. Blast radius: clears this 1
key and hardens any future early-createSession race; not a population-wide wall.

## This round's rule
Separate the marker before naming the wall: `Not connected to SceneSessionManager` is **chessclock-only** (1/1849) and the
tempting "worker thread" reading is refuted by a lit key that createSessions on a worker and succeeds. The real defect is
**connected-then-stale with no retry** — a singleton whose async SSM proxy wasn't populated when an unusually-early
createSession ran. Fix at the one guard that fails hard (re-acquire + retry), not at the thread or the AOSP display mapping.

## Files
- `evidence/separation-table.txt` — the 1849-hilog sweep, the 1-key result, lit contrast, bottom line.
- `evidence/chessclock-timeline.txt` — chessclock's connect→createSession timeline + WMClient singleton/guard internals + source skew.
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; no board; no push. The deployed WMClient is newer than `bms/src` (source skew) — the guard/mechanism is read from
the hilog; the fix is the deployed-WMClient owner's (cc-t3 / window bridge) to implement + build. "async-race vs state-reset"
is not fully separable from logs (n=1); the retry/re-acquire fix is robust to both. Sources read read-only: the U13 hilogs
(`westlake-harness-u7-executor`, `westlake-inputs/generations`), the WMClient source (`westlake-harness/bms`).
