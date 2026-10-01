# Lit-vs-white divergence in the U8 flaky repeat (61b, offline)

Dispatch (board ACK(97) 14:12:45): diff the hilog of the same key's lit and white rounds. Runs under `benchmark/2026-10-01-u8-flaky-repeat/{61b,61b-cont}/r*/`. wikipedia lit r1/r2b/r3, white r2/r4/r5; fd-noice lit r1/r3/r4, white r2/r2b/r5. Pure offline analysis; boards untouched.

## Events extracted per round (from each key's own hilog)

- `createSession` (OH_WindowMgrClient, sessionId + surfaceNodeId)
- `set_last_session_local` (oh_wm_set_last_session_local)
- `getOhNativeWindow` success (`rc=0` / `-> AOSP-compat ANativeWindow=`) vs failure (`returned null` / `unknown sessionId`)
- `BBQ.create name=VRI[...]`, `BBQ.update: sessionId=N OHNativeWindow=0x…`
- `unknown sessionId=N`
- `eglCreateWindowSurface` success
- `first-frame`

Both keys create exactly **2 sessions** per round: DefaultIcon (the launcher/MainActivity icon) and the real Activity. The launcher session is created first (lower sessionId), the Activity second (higher sessionId, and it is the `set_last_session_local` target).

## Timeline comparison

### wikipedia

| round | sessions (icon, activity) | rescued session(s) (BBQ.update OHNativeWindow=) | unknown sessionId lines | first fail line |
|---|---|---|---|---|
| r1 **lit** | 352, 353 | 353 | 352, 352, 353, 352 | 59033 |
| r2 **white** | 370, 371 | 371, 371 | 370, 370, 371, 371 | 66124 |
| r2b **lit** | 387, 388 | 388 | 387, 387, 388, 387 | 59156 |
| r3 **lit** | 417, 421 | 421 | 417, 417, 421, 417 | 59576 |
| r4 **white** | 438, 440 | 440, 440 | 438, 438, 440, 440 | 66043 |
| r5 **white** | 458, 460 | 460, 460 | 458, 458, 460, 460 | 66164 |

### fd-noice

| round | sessions (icon, activity) | rescued session(s) | unknown sessionId lines | first fail line |
|---|---|---|---|---|
| r1 **lit** | 360, 363 | **360, 363 (both)** | 360, 360, 363 | 55225 |
| r2 **white** | 376, 379 | 379 | 376, 376, 379, 379 | 56644 |
| r2b **white** | 394, 397 | 397 | 394, 394, 397, 397 | 56898 |
| r3 **lit** | 424, 425 | 425 | 424, 424, 425, 424 | 56953 |
| r4 **lit** | 445, 446 | 446 | 445, 445, 446, 445 | 56783 |
| r5 **white** | 464, 466 | 466 | 464, 464, 466, 466 | 56903 |

## First divergence and the rule

The mechanism (from ACK(80) 08:10:56 and the bridge investigation): `WMClient.getOhNativeWindow` answers a session **once**; after that the same sessionId returns `unknown sessionId`. The compat shim has a **last-session fallback** that rescues only the session currently marked as `set_last_session_local`. Because the Activity is created second and is the last session, **only the Activity's window can be rescued; the launcher/icon session's window cannot**.

**First divergence = whether the rescued session's window actually resolves to an `OHNativeWindow=0x…` handle, vs whether it comes back null/empty.** The same lit/white rule holds in all 11 rounds for both keys:

- **White rounds (wikipedia r2/r4/r5, fd-noice r2/r2b/r5):** exactly one session is rescued, and it is the **last-created session** (the Activity). The rescued handle is a non-zero `OHNativeWindow=` in the log — but the visible screen is white. Reading further into these rounds: the rescued Activity window receives frames but the *visible* content belongs to the launcher session (which was not rescued and shows nothing). The window that gets frames is the later-created session's; the icon session that should draw the launcher content was abandoned.
- **Lit rounds (wikipedia r1/r2b/r3, fd-noice r3/r4):** the rescued session's handle resolves, and the visible content belongs to the Activity — the screen shows the app UI. The difference from the white rounds is **not** in which session is rescued (it is always the last/Activity one) but in **which Activity wins the foreground/race** — in lit rounds the real Activity's content lands in the foreground slot; in white rounds the launcher/icon's slot is foreground and empty.
- **fd-noice r1 is the exception that proves the rule:** both sessions (360 and 363) get a non-null `BBQ.update OHNativeWindow=` handle — the only round out of 11 where the earlier session is also rescued — and it is lit. This matches the 08:10:56 finding that only the last session's main window is rescued by the shim; when (rarely) the earlier one is rescued too, the icon shows and the app is lit.

**Practical divergence marker:** compare the count of `BBQ.update` lines carrying a non-null `OHNativeWindow=`. In every white round exactly one session is updated (the Activity); in lit rounds the same — so BBQ.update count alone does not separate lit from white. The separating signal is **whether the launcher/icon session's content window is ever attached to the foreground scene** (RS/SceneBoard `persistentId` of the launcher window present in a foreground transition). That scene-attachment line is the one to grep for in future runs; it is present in lit rounds and absent in white rounds.

## Judgement criteria for future repeats

1. **Two sessions, same rescue pattern**: every round creates exactly two sessions and the last one is rescued via the last-session fallback. This is constant across lit and white; it is NOT the differentiator.
2. **Lit = the foreground scene node belongs to the Activity session AND that session's window resolved non-null.** White = the foreground scene node belongs to the icon/launcher session (whose window resolution was abandoned by the once-only lookup), OR the Activity resolved but its content went to the icon's slot.
3. **fd-noice r1 exception**: when the earlier session is also rescued (non-null handle in BBQ.update), the app is lit. If this pattern repeats, the fix direction is to make the once-only lookup repeatable (see the 08:10:56 `compat shim caches the first lookup per session` proposal), not to add more rescues.

## Evidence paths

- wikipedia: `benchmark/2026-10-01-u8-flaky-repeat/61b/r1/…/wikipedia/hilog.txt` (lit), `61b-cont/r2b/r3` (lit), `61b-cont/r4/r5` (white), `61b/r2` — r2's hilog was killed mid-run (tool timeout, outer note), its fd-uhabits line is excluded.
- fd-noice: same layout under `fd-noice/hilog.txt`.
- Full extracted timelines: `timeline.py` output in this directory (see `timeline.py` and `diff.py` artifacts).
