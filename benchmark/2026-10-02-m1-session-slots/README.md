# M1 fix: per-session window slots in the bridge (for U13): source and proofs done, build blocked

#80/#90, offline, no board. M1 is the multi-window white of `2026-10-02-white-vs-lit`: the top Activity's window
gets an empty Surface. The outer loop checked its static root in the source and in the deployed bridge `84695d62`.
This round:
1. wrote the fix in `bms/src/adapter/framework/window/jni/oh_window_manager_client.cpp` (one file, `bridge-m1.patch`);
2. proved it statically on 144 real runs;
3. tested the changed code on the host;
4. wrote the prediction table for the U13 window.

**The bridge build (step 3 of the dispatch) is not done.** There is no exact build chain for `84695d62`, and the
one strict rebuild so far killed every app on the board. That needs the outer's decision (below).

## What was wrong

The bridge's cross-copy window lookup was built on one assumption, written in its own comment at
`oh_wm_get_last_session`: "Each child appspawn-x process spawns one app with one session, so a process-global
last-session is unambiguous". The lookup works like this:

1. `publishProcessWindowTarget` keeps exactly one session id and one window pointer in two process environment
   variables, `WESTLAKE_WINDOW_SESSION_ID_V1` / `WESTLAKE_NATIVE_WINDOW_PTR_V1`.
2. `readProcessWindowTarget(N)` answers only if N is that last session.
3. The compat shim's bridge copy (`dlopen(..., RTLD_NOLOAD)` in its own namespace) is not the copy that created the
   sessions. Its `sessions_` map misses, so every BBQ lookup goes through this one slot.

Apps that start a second Activity at launch break the assumption: wikipedia, noice, fd-noice and fd-uhabits.

## Static proof (`static_proof.py` → `proof.txt`, `proof.json`)

Inputs: 144 real runs, the 11 outer-signed paired runs plus the 133 U10.1T8 signing runs. In each run the app
process's events are replayed in order:
- `createSession: published process window target session=N`;
- a BBQ lookup answered `unknown sessionId=N`;
- its outcome, `BBQ.update: sessionId=N → OHNativeWindow=` (rescued) or `… returned null` (empty Surface).

| claim | result |
|---|---|
| a) the outcome is exactly "N is the last published session" (rescued) / "N was published earlier" (empty) | **367 lookups, 0 violations** |
| a) in the white runs of the 4 keys, the empty lookup is the top Activity's session, published first | wikipedia w1 / w5 r2, noice U7, fd-noice U5 r3, fd-uhabits U5 r1/r2 and U10.1T8: all, e.g. wikipedia r2: 702 (InitialOnboarding) published, then 703 (DefaultIcon) = last; 702's BBQ → `returned null` |
| b) a run that publishes one session only looks that session up, and it is always rescued → the per-session read returns the same pointer as V1 (no-op) | **98 single-session runs, 0 violations** |
| c) sessions published per process | 0: 2 runs, 1: 98, 2: 40, 3: 4 (max 3) |

**Which lookups the fix changes.** Under the fix, a lookup is rescued if and only if N was published.

| runs | lookups changed (all empty → rescued) |
|---|---|
| white pair runs | 6 |
| white population | 5 (noice, fd-uhabits, dddmodel2) |
| lit pair runs | 8 |
| lit population | 24 |

The lit-side changes are the regression-watch list in `predictions.csv`: windows behind the top Activity
(DefaultIcon, theClockActivity, Main behind Intro) and later re-lookups of a top window after another session was
published (secuso memory / pin / ruler, timetable, studytracker, beecount, fd-seal). Today these get an empty
Surface; with the fix they get their real window.

## The change (`bridge-m1.patch`, +36/−7, in the anonymous namespace and `destroySession`)

- **publish:** also writes `WESTLAKE_NATIVE_WINDOW_PTR_V2_<sessionId>`. The V1 pair is still written exactly as
  before.
- **read:** `readProcessWindowTarget(N)` first reads `…_V2_<N>`. If that is absent or malformed it runs the old V1
  check unchanged.
- **cleanup:** `destroySession` unsets `…_V2_<N>` when it erases the session from the creating copy's map. Live
  variables = live sessions (≤ 3 observed); V1 behaves as before.
- **Transition:** both loaded copies are the same file, so after deployment both are new. In a mixed pair:
  - an old publisher writes only V1, and a new reader falls back to V1;
  - a new publisher still writes V1, and an old reader reads only V1.

  Either way the result is today's behavior, never worse. The host test checks this.
- **Not touched:** the frozen registry has no entry for the bridge or this file (FZ-001…008). No frozen file is
  touched.

**Host test** (`test/run_slots_test.sh`) extracts the anonymous namespace from the real cpp (no hand copy), compiles
it with `c++ -std=c++17 -Wall -Wextra -Werror` and checks:
- single session = V1;
- the white wikipedia order resolves both sessions;
- the V1 last session is unchanged;
- destroy clears only its slot;
- old/new mixed behavior equals pre-fix;
- a malformed slot falls back.

Result: **PASS (0 failures)**. `test_m1.py` runs it.

## Build: blocked, needs the outer's decision

`benchmark/2026-10-01-bridge-846-provenance` searched the Mac, a2hlab and hw248. For `84695d62` it recovered the
exact bytes but not the build: no patch set, object cohort, ordered link or toolchain receipt; the nearest record
is `bc878f4f`.

The one strict rebuild of this bridge, `7cf8ebcc` (`benchmark/2026-10-01-abi-diff`), had 8 signature drifts in 5
functions. On board #96 it made every app, controls included, die in `ViewRootImpl.setView`. DIGEST 2026-10-01 forbids
passing a rebuilt bridge off as a one-variable change.

So "two builds byte-identical + `deployed_strings_diff` vs 84695d62 differs only here" cannot be met from this
source: a rebuild differs everywhere, not in one function.

Options:

| route | what | single variable? | status |
|---|---|---|---|
| **R1** rebuild the bridge from `bms/src` + this patch | the dispatched route | no: whole-library rebuild (7cf8ebcc precedent: 8 drifts, every app died) | blocked; only with a reconstructed 84695d62 chain or outer acceptance of a full-library change with `abi_diff.py` exit 0 and a full sweep |
| **R2** patch the deployed 84695d62 binary | add per-session publish/read in machine code | yes (binary) | possible but needs new code (name formatting, a second getenv) in a code cave; not recommended |
| **R3** same effect in the runtime's compat shim (`android_graphics_compat_shim.cpp`, liboh_android_runtime `ac59dec0`) | when its own bridge copy returns null, ask the other loaded copy, located by `dl_iterate_phdr` (same file, so same symbol offset). The creating copy's `sessions_` holds every window it created. No env vars, bridge untouched | yes: N10b `build-runtime.py` rebuilds the runtime per object (baseline `216b68fb` byte-identical, per-.o hashes), so only `android_graphics_compat_shim.o` changes | recommended; first check statically (OH musl `dl_iterate_phdr` source/disasm) that it lists objects of every namespace |

`bms/src` is outside land.py's allowed prefixes, so the change lands as `bridge-m1.patch`. It applies to master's
`oh_window_manager_client.cpp` (`git apply`), and the edited cpp is committed on this lane's branch, so R1 has it
whenever a bridge chain exists. R3 waits for the outer's word, because it moves the fix out of the file the dispatch
named.

## Predictions (`predictions.csv`, judged by k/n in the U13 window)

**White → lit, high confidence:**
- **noice**, **fd-uhabits**: misroute True on every white run; they light whenever the race goes the other way.

**Lottery → stable lit:**
- **wikipedia**: today 1/3; both white runs misroute, the lit run not.
- **fd-noice**: U5 2/3, U8 3/6.

**May move, low-medium:**
- **dddmodel2**: its MainActivity's re-lookups return null after a second window session is published (3 lookups).

**Regression watch, expected to stay lit:**
- the 10 lit keys whose non-top / re-lookup windows change;
- judged by t20 and by the absence of empty lookups.

## Rule this round sets

- Before rebuilding a native library for a one-function fix, check that the deployed binary has a reproducible
  chain.
- If it has none (bridge `84695d62`), put the fix where a chain exists (here, the runtime), or treat it as a
  whole-library change with `abi_diff` and a full sweep.
- A static proof of a lookup fix replays every lookup in real runs and lists exactly which outcomes change, including
  on lit keys.

## Files

- `static_proof.py` → `proof.txt`, `proof.json` (per-run publish/lookup replay, changed lookups).
- `bridge-m1.patch` (the cpp diff against master).
- `test/slots_test.cpp`, `test/run_slots_test.sh`, `test_m1.py`.
- `predictions.csv`.

## Update: baseline reproduction of 84695d62 (after master's hardened build scripts 9c14005a01 / 0c8639ba1b)

`baseline-repro/` answers the outer's "reproduce 84695d62 byte-identically first". The answer is static, before any
build: it **cannot be reproduced** from any source on the Mac, a2hlab or hw248.

1. **The window client version in the binary is in no source tree.** Its process-published cross-namespace
   RSSurfaceNode path is absent from all 8 local versions; the closest, `89183eb549d9` (real-work oh61-v7), differs
   by 2/3 strings.
2. **`oh_canvas_renderer.cpp` was not compiled in.** 0/18 literals and 0 `OHCanvasRenderer::draw*` symbols are in the
   binary; the hardened script compiles it.
3. **`display_manager_adapter_jni.cpp` came from the oh61 copy** (3/4 literals vs 3/16), which the script now excludes.

The bridge's real window cohort is the oh61-v7 snapshot, not `bms/src`. If the bridge route is kept, M1 must be ported
there. No M1 build was started; options (a) reconstruct, (b) new baseline, (c) runtime-side are in
`baseline-repro/README.md`.
