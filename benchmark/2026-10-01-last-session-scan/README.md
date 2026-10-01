# U7 last-session lookup impact

## Corrected assumption

A failed lookup is not itself a white-screen verdict. Only app-PID execution lines count; a later RESUME or focus request is not proof of which Activity owns the screenshot. Counts include pre-click initialization through signed t20. Session count means successful creations, not every createSession diagnostic.

Criteria were written before the full scan in `CRITERIA.md`. All 66 signed first attempts are preserved; no screenshot category is recomputed. Queue links without explicit queue IDs are provisional and labeled. Null counts and last-session comparisons use explicit session IDs.

## Summary

```json
{
  "keys": 66,
  "signed_visuals": {
    "own-ui": 34,
    "desktop": 24,
    "white": 6,
    "black": 1,
    "no-capture": 1
  },
  "impacts": {
    "null-foreground-unknown": 6,
    "multi-session-no-null-observed": 8,
    "no-session-observed-not-a-negative": 23,
    "single-session-not-exposed": 27,
    "unknown-incomplete-evidence": 1,
    "foreground-null-white-candidate": 1
  },
  "null_keys": [
    "aegis",
    "anki",
    "fd-noice",
    "fd-uhabits",
    "markor",
    "noice",
    "wikipedia"
  ],
  "null_events": 9,
  "empty_surface_events": 2,
  "session_distribution": {
    "2": 15,
    "0": 24,
    "1": 27
  },
  "null_non_last_events": 9,
  "unknown_session_events": 108,
  "unknown_session_keys": [
    "aegis",
    "anki",
    "antennapod",
    "fd-AppManager",
    "fd-android",
    "fd-app",
    "fd-auxio",
    "fd-binaryeye",
    "fd-calendar",
    "fd-catima",
    "fd-com-amaze-filemanager",
    "fd-com-kunzisoft-keepass-libre",
    "fd-droidify",
    "fd-etar",
    "fd-feeder",
    "fd-filemanager",
    "fd-fitness",
    "fd-gallery",
    "fd-k9",
    "fd-libretube",
    "fd-minetest",
    "fd-mobile",
    "fd-mpv",
    "fd-musicplayer",
    "fd-netguard",
    "fd-noice",
    "fd-notes",
    "fd-organicmaps",
    "fd-reader",
    "fd-shatteredpixeldungeon",
    "fd-stk",
    "fd-tasks",
    "fd-tusky",
    "fd-uhabits",
    "markor",
    "newpipe",
    "noice",
    "ooniprobe",
    "opencamera",
    "ppsspp",
    "wikipedia"
  ],
  "unknown_session_timing": {
    "after-success": 108
  },
  "unknown_session_then_last_equal": 97,
  "unknown_session_next_bbq_update": {
    "update-ok": 97,
    "update-null": 10,
    "unobserved": 1
  },
  "gl_valid_surface_iae_events": 2,
  "gl_valid_surface_iae_keys": [
    "fd-app",
    "fd-shatteredpixeldungeon"
  ],
  "signed_bright_null_keys": [
    "aegis",
    "anki",
    "fd-noice",
    "fd-uhabits",
    "markor",
    "noice"
  ]
}
```

Three signed-bright, one-session, zero-null controls: **fd-android, fd-auxio, fd-binaryeye**.

**Boundaries:** six signed-bright keys also have null lookup(s): a null is not sufficient for white. Their exact on-screen Activity is not independently bound by a bare RESUME/request-focus event, so background-only attribution stays unknown unless an Activity-level sign-off exists. Anki has two sessions with the same DeckPicker name (androidType 2 then 1); do not call this two Activities. AppManager has one successful session and no null in this sweep, despite its later A-class classification. No-null and zero-session cases are not universal proof of native-window correctness.

## All 66 keys

| Key | Sessions / unique | Last-session sequence | Null / empty | Unknown session | GL valid-Surface IAE | Null Activity (session) | Signed t20 | Impact |
|---|---:|---|---:|---:|---:|---|---|---|
| aegis | 2/2 | 44 → 45 | 1/0 | 3 | 0 | com.beemdevelopment.aegis.ui.MainActivity (44) | own-ui | null-foreground-unknown |
| anki | 2/2 | 62 → 63 | 3/1 | 6 | 0 | com.ichi2.anki.DeckPicker (62) | own-ui | null-foreground-unknown |
| antennapod | 2/2 | 39 → 41 | 0/0 | 4 | 0 | none observed | own-ui | multi-session-no-null-observed |
| burgerking | 0/0 |  | 0/0 | 0 | 0 | none observed | desktop | no-session-observed-not-a-negative |
| fd-AppManager | 1/1 | 48 | 0/0 | 2 | 0 | none observed | white | single-session-not-exposed |
| fd-android | 1/1 | 66 | 0/0 | 2 | 0 | none observed | own-ui | single-session-not-exposed |
| fd-api | 0/0 |  | 0/0 | 0 | 0 | none observed | desktop | no-session-observed-not-a-negative |
| fd-app | 1/1 | 69 | 0/0 | 2 | 1 | none observed | white | single-session-not-exposed |
| fd-auxio | 1/1 | 50 | 0/0 | 2 | 0 | none observed | own-ui | single-session-not-exposed |
| fd-binaryeye | 1/1 | 88 | 0/0 | 2 | 0 | none observed | own-ui | single-session-not-exposed |
| fd-breezyweather | 0/0 |  | 0/0 | 0 | 0 | none observed | desktop | no-session-observed-not-a-negative |
| fd-calendar | 1/1 | 73 | 0/0 | 1 | 0 | none observed | own-ui | single-session-not-exposed |
| fd-catima | 1/1 | 75 | 0/0 | 2 | 0 | none observed | own-ui | single-session-not-exposed |
| fd-client | 0/0 |  | 0/0 | 0 | 0 | none observed | desktop | no-session-observed-not-a-negative |
| fd-com-amaze-filemanager | 1/1 | 52 | 0/0 | 2 | 0 | none observed | own-ui | single-session-not-exposed |
| fd-com-kunzisoft-keepass-libre | 1/1 | 54 | 0/0 | 2 | 0 | none observed | own-ui | single-session-not-exposed |
| fd-droidify | 1/1 | 56 | 0/0 | 2 | 0 | none observed | own-ui | single-session-not-exposed |
| fd-etar | 1/1 | 77 | 0/0 | 2 | 0 | none observed | own-ui | single-session-not-exposed |
| fd-feeder | 1/1 | 80 | 0/0 | 2 | 0 | none observed | own-ui | single-session-not-exposed |
| fd-fennec_fdroid | 0/0 |  | 0/0 | 0 | 0 | none observed | desktop | no-session-observed-not-a-negative |
| fd-filemanager | 1/1 | 84 | 0/0 | 2 | 0 | none observed | own-ui | single-session-not-exposed |
| fd-fitness | 2/2 | 58 → 59 | 0/0 | 4 | 0 | none observed | own-ui | multi-session-no-null-observed |
| fd-fluffychat | 0/0 |  | 0/0 | 0 | 0 | none observed | desktop | no-session-observed-not-a-negative |
| fd-gallery | 1/1 | 360 | 0/0 | 3 | 0 | none observed | own-ui | single-session-not-exposed |
| fd-im-vector-app | 0/0 |  | 0/0 | 0 | 0 | none observed | desktop | no-session-observed-not-a-negative |
| fd-immich | 0/0 |  | 0/0 | 0 | 0 | none observed | desktop | no-session-observed-not-a-negative |
| fd-k9 | 1/1 | 365 | 0/0 | 2 | 0 | none observed | own-ui | single-session-not-exposed |
| fd-kitchenowl | 0/0 |  | 0/0 | 0 | 0 | none observed | desktop | no-session-observed-not-a-negative |
| fd-libre | 0/0 |  | 0/0 | 0 | 0 | none observed | desktop | no-session-observed-not-a-negative |
| fd-libretube | 1/1 | 369 | 0/0 | 2 | 0 | none observed | own-ui | single-session-not-exposed |
| fd-meet | 1/1 | 371 | 0/0 | 0 | 0 | none observed | desktop | single-session-not-exposed |
| fd-minetest | 1/1 | 373 | 0/0 | 2 | 0 | none observed | own-ui | single-session-not-exposed |
| fd-mobile | 2/2 | 401 → 402 | 0/0 | 4 | 0 | none observed | black | multi-session-no-null-observed |
| fd-mpv | 1/1 | 375 | 0/0 | 2 | 0 | none observed | own-ui | single-session-not-exposed |
| fd-musicplayer | 1/1 | 378 | 0/0 | 1 | 0 | none observed | desktop | single-session-not-exposed |
| fd-netguard | 2/2 | 351 → 352 | 0/0 | 4 | 0 | none observed | own-ui | multi-session-no-null-observed |
| fd-noice | 2/2 | 355 → 356 | 1/0 | 3 | 0 | com.github.ashutoshgngwr.noice.activity.MainActivity (355) | own-ui | null-foreground-unknown |
| fd-notes | 1/1 | 381 | 0/0 | 1 | 0 | none observed | own-ui | single-session-not-exposed |
| fd-organicmaps | 2/2 | 388 → 389 | 0/0 | 4 | 0 | none observed | own-ui | multi-session-no-null-observed |
| fd-plus | 0/0 |  | 0/0 | 0 | 0 | none observed | desktop | no-session-observed-not-a-negative |
| fd-reader | 1/1 | 396 | 0/0 | 2 | 0 | none observed | own-ui | single-session-not-exposed |
| fd-saber | 0/0 |  | 0/0 | 0 | 0 | none observed | desktop | no-session-observed-not-a-negative |
| fd-seal | 0/0 |  | 0/0 | 0 | 0 | none observed | no-capture | unknown-incomplete-evidence |
| fd-shatteredpixeldungeon | 1/1 | 399 | 0/0 | 3 | 1 | none observed | white | single-session-not-exposed |
| fd-stk | 2/2 | 406 → 408 | 0/0 | 4 | 0 | none observed | own-ui | multi-session-no-null-observed |
| fd-tasks | 1/1 | 391 | 0/0 | 2 | 0 | none observed | own-ui | single-session-not-exposed |
| fd-tusky | 1/1 | 394 | 0/0 | 2 | 0 | none observed | own-ui | single-session-not-exposed |
| fd-tutanota | 0/0 |  | 0/0 | 0 | 0 | none observed | desktop | no-session-observed-not-a-negative |
| fd-uhabits | 2/2 | 400 → 401 | 1/0 | 3 | 0 | org.isoron.uhabits.MainActivity (400) | own-ui | null-foreground-unknown |
| fd-wifianalyzer | 0/0 |  | 0/0 | 0 | 0 | none observed | desktop | no-session-observed-not-a-negative |
| firefox | 0/0 |  | 0/0 | 0 | 0 | none observed | desktop | no-session-observed-not-a-negative |
| localsend | 0/0 |  | 0/0 | 0 | 0 | none observed | desktop | no-session-observed-not-a-negative |
| markor | 2/2 | 385 → 386 | 1/0 | 3 | 0 | net.gsantner.markor.activity.MainActivity (385) | own-ui | null-foreground-unknown |
| mcdonalds | 0/0 |  | 0/0 | 0 | 0 | none observed | desktop | no-session-observed-not-a-negative |
| mindustry | 0/0 |  | 0/0 | 0 | 0 | none observed | desktop | no-session-observed-not-a-negative |
| newpipe | 2/2 | 381 → 382 | 0/0 | 4 | 0 | none observed | own-ui | multi-session-no-null-observed |
| noice | 2/2 | 423 → 424 | 1/0 | 3 | 0 | com.github.ashutoshgngwr.noice.activity.MainActivity (423) | own-ui | null-foreground-unknown |
| ooniprobe | 1/1 | 379 | 0/0 | 2 | 0 | none observed | own-ui | single-session-not-exposed |
| opencamera | 2/2 | 388 → 389 | 0/0 | 4 | 0 | none observed | own-ui | multi-session-no-null-observed |
| ppsspp | 1/1 | 417 | 0/0 | 2 | 0 | none observed | desktop | single-session-not-exposed |
| subwaysurfers | 0/0 |  | 0/0 | 0 | 0 | none observed | desktop | no-session-observed-not-a-negative |
| termux | 0/0 |  | 0/0 | 0 | 0 | none observed | white | no-session-observed-not-a-negative |
| toutiao | 0/0 |  | 0/0 | 0 | 0 | none observed | desktop | no-session-observed-not-a-negative |
| vlc | 0/0 |  | 0/0 | 0 | 0 | none observed | desktop | no-session-observed-not-a-negative |
| wikipedia | 2/2 | 375 → 376 | 1/1 | 4 | 0 | org.wikipedia.onboarding.InitialOnboardingActivity (375) | white | foreground-null-white-candidate |
| x | 0/0 |  | 0/0 | 0 | 0 | none observed | white | no-session-observed-not-a-negative |

## Extended signature scope

Unknown-session diagnostics and BBQ null lookups are separate event families. Each unknown-session event retains its Activity, then-last session, timing relative to successful creation, and next same-PID/TID/session BBQ update (ordered correlation, not proof of a fallback implementation). A zero IAE count does not clear other GL/native failures. Signed-bright apps with these warnings remain bright; single-session controls prove absence of BBQ null, not absence of all warnings.

**GLSurfaceView valid-Surface IAE appears only in fd-app and fd-shatteredpixeldungeon, one each.** Mindustry and x have neither added signature. PPSSPP has two unknown-session messages, Mobile four, but neither has this IAE. All three single-session bright controls themselves have two unknown-session messages and successful BBQ updates: the broader warning cannot be used as the white-screen rule.


## Failure and negative-control evidence

### aegis

PID [14628]; signed **own-ui** at `2026-10-01T06:33:44+0800`; hilog SHA `a93208247a6bec76d124d698bd49b1f89c8c7173028b18e857636c89a731e7e6`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/aegis/hilog.txt:35861` — createSession: bundle=com.beemdevelopment.aegis ability=MainActivity name=com.beemdevelopment.aegis/com.beemdevelopment.aegis.ui.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3beb8140 token=0000007F3BEB8140
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/aegis/hilog.txt:35950` — createSession: success, sessionId=44, surfaceNodeId=62826781605889
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/aegis/hilog.txt:35952` — [IPC] ENTER oh_wm_set_last_session_local session=44
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/aegis/hilog.txt:37198` — BBQ.create name=VRI[MainActivity] ptr=0000007F39627300
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/aegis/hilog.txt:37223` — getOhNativeWindow: unknown sessionId=44
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/aegis/hilog.txt:37225` — BBQ.update: sessionId=44 → OHNativeWindow=0000007F3A615010 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/aegis/hilog.txt:37226` — BBQ.getSurface: returning Surface with mNativeObject=0000007F3A615010 (sessionId=44)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/aegis/hilog.txt:38066` — createSession: bundle=com.beemdevelopment.aegis ability=IntroActivity name=com.beemdevelopment.aegis/com.beemdevelopment.aegis.ui.IntroActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3b4c6140 token=0000007F3B4C6140
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/aegis/hilog.txt:38136` — createSession: success, sessionId=45, surfaceNodeId=62826781605892
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/aegis/hilog.txt:38137` — [IPC] ENTER oh_wm_set_last_session_local session=45
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/aegis/hilog.txt:38413` — getOhNativeWindow: unknown sessionId=44
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/aegis/hilog.txt:38414` — BBQ.update: getOhNativeWindow(sessionId=44) returned null
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/aegis/hilog.txt:38602` — BBQ.create name=VRI[IntroActivity] ptr=0000007F30E7EC70
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/aegis/hilog.txt:38604` — getOhNativeWindow: unknown sessionId=45
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/aegis/hilog.txt:38606` — BBQ.update: sessionId=45 → OHNativeWindow=0000007F3A6167D0 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/aegis/hilog.txt:38607` — BBQ.getSurface: returning Surface with mNativeObject=0000007F3A6167D0 (sessionId=45)

### anki

PID [21386, 21472]; signed **own-ui** at `2026-10-01T06:33:44+0800`; hilog SHA `beb0edae78ddf72f003ce6463794307d2005958836eadbbb5dca1dc2466d76e1`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/anki/hilog.txt:113119` — createSession: bundle=com.ichi2.anki ability=DeckPicker name=com.ichi2.anki/com.ichi2.anki.DeckPicker, androidType=2 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3beb7fb0 token=0000007F3BEB7FB0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/anki/hilog.txt:113182` — createSession: success, sessionId=62, surfaceNodeId=92221537779713
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/anki/hilog.txt:113183` — [IPC] ENTER oh_wm_set_last_session_local session=62
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/anki/hilog.txt:113513` — createSession: bundle=com.ichi2.anki ability=DeckPicker name=com.ichi2.anki/com.ichi2.anki.DeckPicker, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3beb7fb0 token=0000007F3BEB7FB0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/anki/hilog.txt:113580` — createSession: success, sessionId=63, surfaceNodeId=92221537779716
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/anki/hilog.txt:113581` — [IPC] ENTER oh_wm_set_last_session_local session=63
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/anki/hilog.txt:113789` — BBQ.create name=VRI[DeckPicker] ptr=0000007F329ECAB0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/anki/hilog.txt:113793` — getOhNativeWindow: unknown sessionId=62
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/anki/hilog.txt:113794` — BBQ.update: getOhNativeWindow(sessionId=62) returned null
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/anki/hilog.txt:113796` — getOhNativeWindow: unknown sessionId=62
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/anki/hilog.txt:113797` — BBQ.getSurface: ohNativeWindow null (sessionId=62 not attached or BBQ.update not yet called) — returning empty Surface so ViewRoot.mSurface.transferFrom doesn't NPE
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/anki/hilog.txt:114058` — BBQ.create name=VRI[DeckPicker] ptr=0000007F3279CF20
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/anki/hilog.txt:114060` — getOhNativeWindow: unknown sessionId=63
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/anki/hilog.txt:114062` — BBQ.update: sessionId=63 → OHNativeWindow=0000007F3B748650 (1200x1920 fmt=1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/anki/hilog.txt:114063` — BBQ.getSurface: returning Surface with mNativeObject=0000007F3B748650 (sessionId=63)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/anki/hilog.txt:114768` — getOhNativeWindow: unknown sessionId=62
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/anki/hilog.txt:114769` — BBQ.update: getOhNativeWindow(sessionId=62) returned null
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/anki/hilog.txt:114846` — getOhNativeWindow: unknown sessionId=63
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/anki/hilog.txt:114848` — BBQ.update: sessionId=63 → OHNativeWindow=0000007F3B748650 (1200x1920 fmt=1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/anki/hilog.txt:115017` — getOhNativeWindow: unknown sessionId=62
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/anki/hilog.txt:115018` — BBQ.update: getOhNativeWindow(sessionId=62) returned null

### antennapod

PID [13664]; signed **own-ui** at `2026-10-01T06:33:44+0800`; hilog SHA `1196601b0c1c7f699611b7970fdd06ca9b75d419dfef07d4797672432e44cceb`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/antennapod/hilog.txt:22796` — createSession: bundle=de.danoeh.antennapod ability=SplashActivity name=de.danoeh.antennapod/de.danoeh.antennapod.activity.SplashActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3beb8140 token=0000007F3BEB8140
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/antennapod/hilog.txt:22858` — createSession: success, sessionId=39, surfaceNodeId=58686433132545
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/antennapod/hilog.txt:22860` — [IPC] ENTER oh_wm_set_last_session_local session=39
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/antennapod/hilog.txt:23414` — BBQ.create name=VRI[SplashActivity] ptr=0000007F3A11E880
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/antennapod/hilog.txt:23419` — getOhNativeWindow: unknown sessionId=39
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/antennapod/hilog.txt:23421` — BBQ.update: sessionId=39 → OHNativeWindow=0000007FBD2FB290 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/antennapod/hilog.txt:23422` — BBQ.getSurface: returning Surface with mNativeObject=0000007FBD2FB290 (sessionId=39)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/antennapod/hilog.txt:23610` — getOhNativeWindow: unknown sessionId=39
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/antennapod/hilog.txt:23612` — BBQ.update: sessionId=39 → OHNativeWindow=0000007FBD2FB290 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/antennapod/hilog.txt:36038` — createSession: bundle=de.danoeh.antennapod ability=MainActivity name=de.danoeh.antennapod/de.danoeh.antennapod.activity.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3a59a1a0 token=0000007F3A59A1A0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/antennapod/hilog.txt:36096` — createSession: success, sessionId=41, surfaceNodeId=58686433132548
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/antennapod/hilog.txt:36097` — [IPC] ENTER oh_wm_set_last_session_local session=41
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/antennapod/hilog.txt:38628` — BBQ.create name=VRI[MainActivity] ptr=0000007F2E46BD30
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/antennapod/hilog.txt:38630` — getOhNativeWindow: unknown sessionId=41
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/antennapod/hilog.txt:38632` — BBQ.update: sessionId=41 → OHNativeWindow=0000007F396982D0 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/antennapod/hilog.txt:38633` — BBQ.getSurface: returning Surface with mNativeObject=0000007F396982D0 (sessionId=41)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/antennapod/hilog.txt:39642` — getOhNativeWindow: unknown sessionId=41
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/antennapod/hilog.txt:39644` — BBQ.update: sessionId=41 → OHNativeWindow=0000007F396982D0 (1200x1920 fmt=-1)

### fd-AppManager

PID [15675]; signed **white** at `2026-10-01T06:33:44+0800`; hilog SHA `291cb204b30f8f5f43134c915665e4e03f03a83e355174a55d7c4fa6c73b7458`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-AppManager/hilog.txt:40701` — createSession: bundle=io.github.muntashirakon.AppManager ability=SplashActivity name=io.github.muntashirakon.AppManager/io.github.muntashirakon.AppManager.main.SplashActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3beb8140 token=0000007F3BEB8140
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-AppManager/hilog.txt:40794` — createSession: success, sessionId=48, surfaceNodeId=67323612364801
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-AppManager/hilog.txt:40795` — [IPC] ENTER oh_wm_set_last_session_local session=48
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-AppManager/hilog.txt:41844` — BBQ.create name=VRI[SplashActivity] ptr=0000007F39629BC0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-AppManager/hilog.txt:41848` — getOhNativeWindow: unknown sessionId=48
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-AppManager/hilog.txt:41850` — BBQ.update: sessionId=48 → OHNativeWindow=0000007F3B4BB290 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-AppManager/hilog.txt:41851` — BBQ.getSurface: returning Surface with mNativeObject=0000007F3B4BB290 (sessionId=48)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-AppManager/hilog.txt:42294` — getOhNativeWindow: unknown sessionId=48
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-AppManager/hilog.txt:42296` — BBQ.update: sessionId=48 → OHNativeWindow=0000007F3B4BB290 (1200x1920 fmt=-1)

### fd-android

PID [22530, 22571]; signed **own-ui** at `2026-10-01T06:33:44+0800`; hilog SHA `2c6256bdc30bb541eaf252802ceaf94134065ceeac6eecb38d04afe140bee992`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-android/hilog.txt:66009` — createSession: bundle=net.thunderbird.android ability=UpgradeDatabaseActivity name=net.thunderbird.android/com.fsck.k9.activity.UpgradeDatabaseActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3bc6afb0 token=0000007F3BC6AFB0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-android/hilog.txt:66071` — createSession: success, sessionId=66, surfaceNodeId=96941706838017
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-android/hilog.txt:66072` — [IPC] ENTER oh_wm_set_last_session_local session=66
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-android/hilog.txt:66510` — BBQ.create name=VRI[UpgradeDatabaseActivity] ptr=0000007F3A7E6C20
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-android/hilog.txt:66514` — getOhNativeWindow: unknown sessionId=66
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-android/hilog.txt:66516` — BBQ.update: sessionId=66 → OHNativeWindow=0000007F3B759B50 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-android/hilog.txt:66517` — BBQ.getSurface: returning Surface with mNativeObject=0000007F3B759B50 (sessionId=66)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-android/hilog.txt:67391` — getOhNativeWindow: unknown sessionId=66
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-android/hilog.txt:67393` — BBQ.update: sessionId=66 → OHNativeWindow=0000007F3B759B50 (1200x1920 fmt=-1)

### fd-app

PID [24259]; signed **white** at `2026-10-01T06:33:44+0800`; hilog SHA `6a3fc3375646c4e0e37e23f6b4154aeabe953982fd67373b152a8c84c93be4a0`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-app/hilog.txt:52903` — createSession: bundle=com.unciv.app ability=AndroidLauncher name=com.unciv.app/com.unciv.app.AndroidLauncher, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3beb8c30 token=0000007F3BEB8C30
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-app/hilog.txt:52964` — createSession: success, sessionId=69, surfaceNodeId=104191611633665
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-app/hilog.txt:52966` — [IPC] ENTER oh_wm_set_last_session_local session=69
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-app/hilog.txt:53400` — BBQ.create name=VRI[AndroidLauncher] ptr=0000007F33F68460
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-app/hilog.txt:53404` — getOhNativeWindow: unknown sessionId=69
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-app/hilog.txt:53406` — BBQ.update: sessionId=69 → OHNativeWindow=0000007F3B6BF790 (1200x1920 fmt=-2)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-app/hilog.txt:53407` — BBQ.getSurface: returning Surface with mNativeObject=0000007F3B6BF790 (sessionId=69)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-app/hilog.txt:53469` — BBQ.create name=SurfaceView[com.unciv.app/com.unciv.app.AndroidLauncher] ptr=0000007F33F690C0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-app/hilog.txt:53482` — BBQ.update: sessionId=69 → OHNativeWindow=0000007F3A188DD0 (1200x1920 fmt=4)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-app/hilog.txt:53698` — java.lang.IllegalArgumentException: Make sure the SurfaceView or associated SurfaceHolder has a valid Surface
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-app/hilog.txt:53745` — getOhNativeWindow: unknown sessionId=69
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-app/hilog.txt:53773` — BBQ.update: sessionId=69 → OHNativeWindow=0000007F3B6BF790 (1200x1920 fmt=-2)

### fd-auxio

PID [16601]; signed **own-ui** at `2026-10-01T06:33:44+0800`; hilog SHA `7f53e690039d8ca1c5f7a164ca0e429b28ce6d2a823e522d1e44a96c0bedde79`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-auxio/hilog.txt:55154` — createSession: bundle=org.oxycblt.auxio ability=MainActivity name=org.oxycblt.auxio/org.oxycblt.auxio.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3beb8dc0 token=0000007F3BEB8DC0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-auxio/hilog.txt:55216` — createSession: success, sessionId=50, surfaceNodeId=71300752080897
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-auxio/hilog.txt:55217` — [IPC] ENTER oh_wm_set_last_session_local session=50
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-auxio/hilog.txt:55833` — BBQ.create name=VRI[MainActivity] ptr=0000007F32FD8070
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-auxio/hilog.txt:55837` — getOhNativeWindow: unknown sessionId=50
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-auxio/hilog.txt:55839` — BBQ.update: sessionId=50 → OHNativeWindow=0000007F3B4D88D0 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-auxio/hilog.txt:55840` — BBQ.getSurface: returning Surface with mNativeObject=0000007F3B4D88D0 (sessionId=50)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-auxio/hilog.txt:57431` — getOhNativeWindow: unknown sessionId=50
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-auxio/hilog.txt:57433` — BBQ.update: sessionId=50 → OHNativeWindow=0000007F3B4D88D0 (1200x1920 fmt=-1)

### fd-binaryeye

PID [1895, 1943]; signed **own-ui** at `2026-10-01T06:33:44+0800`; hilog SHA `158477546d50eca1baf3c8dde0861af34724edc4bb14cd4f58538cc7eda4a64b`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-binaryeye/hilog.txt:43532` — createSession: bundle=de.markusfisch.android.binaryeye ability=CameraActivity name=de.markusfisch.android.binaryeye/de.markusfisch.android.binaryeye.activity.CameraActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3beb7e20 token=0000007F3BEB7E20
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-binaryeye/hilog.txt:43594` — createSession: success, sessionId=88, surfaceNodeId=8345121456129
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-binaryeye/hilog.txt:43595` — [IPC] ENTER oh_wm_set_last_session_local session=88
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-binaryeye/hilog.txt:43919` — BBQ.create name=VRI[CameraActivity] ptr=0000007F3A5779D0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-binaryeye/hilog.txt:43923` — getOhNativeWindow: unknown sessionId=88
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-binaryeye/hilog.txt:43925` — BBQ.update: sessionId=88 → OHNativeWindow=0000007F3B7578D0 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-binaryeye/hilog.txt:43926` — BBQ.getSurface: returning Surface with mNativeObject=0000007F3B7578D0 (sessionId=88)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-binaryeye/hilog.txt:44274` — getOhNativeWindow: unknown sessionId=88
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-binaryeye/hilog.txt:44302` — BBQ.update: sessionId=88 → OHNativeWindow=0000007F3B7578D0 (1200x1920 fmt=-1)

### fd-calendar

PID [26140]; signed **own-ui** at `2026-10-01T06:33:44+0800`; hilog SHA `95ffa211cdeec24b144efcc8a7e53a149d9122a9e0225dbd197098ad3f31905b`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-calendar/hilog.txt:52988` — createSession: bundle=org.fossify.calendar ability=SplashActivity name=org.fossify.calendar/org.fossify.calendar.activities.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3b80c140 token=0000007F3B80C140
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-calendar/hilog.txt:53052` — createSession: success, sessionId=73, surfaceNodeId=112270445117441
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-calendar/hilog.txt:53053` — [IPC] ENTER oh_wm_set_last_session_local session=73
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-calendar/hilog.txt:53817` — BBQ.create name=VRI[MainActivity] ptr=0000007F32F29890
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-calendar/hilog.txt:53824` — getOhNativeWindow: unknown sessionId=73
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-calendar/hilog.txt:53826` — BBQ.update: sessionId=73 → OHNativeWindow=0000007F3B48A510 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-calendar/hilog.txt:53827` — BBQ.getSurface: returning Surface with mNativeObject=0000007F3B48A510 (sessionId=73)

### fd-catima

PID [27094]; signed **own-ui** at `2026-10-01T06:33:44+0800`; hilog SHA `d5a2745be757e643856a0872bdfa16387e29db074efcf3ba87f1dd3f8704d382`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-catima/hilog.txt:62724` — createSession: bundle=me.hackerchick.catima ability=MainActivity name=me.hackerchick.catima/protect.card_locker.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3beb7e20 token=0000007F3BEB7E20
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-catima/hilog.txt:62787` — createSession: success, sessionId=75, surfaceNodeId=116367843917825
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-catima/hilog.txt:62788` — [IPC] ENTER oh_wm_set_last_session_local session=75
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-catima/hilog.txt:63165` — BBQ.create name=VRI[MainActivity] ptr=0000007F3A228E10
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-catima/hilog.txt:63169` — getOhNativeWindow: unknown sessionId=75
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-catima/hilog.txt:63171` — BBQ.update: sessionId=75 → OHNativeWindow=0000007F3B3FF8D0 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-catima/hilog.txt:63172` — BBQ.getSurface: returning Surface with mNativeObject=0000007F3B3FF8D0 (sessionId=75)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-catima/hilog.txt:63622` — getOhNativeWindow: unknown sessionId=75
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-catima/hilog.txt:63655` — BBQ.update: sessionId=75 → OHNativeWindow=0000007F3B3FF8D0 (1200x1920 fmt=-1)

### fd-com-amaze-filemanager

PID [17500]; signed **own-ui** at `2026-10-01T06:33:44+0800`; hilog SHA `4d67962994a0475d2f2caecb72b675743c8f12a8bbca6293fd4357c4e4fb0fb1`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-com-amaze-filemanager/hilog.txt:94687` — createSession: bundle=com.amaze.filemanager ability=MainActivity name=com.amaze.filemanager/com.amaze.filemanager.ui.activities.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3beb8140 token=0000007F3BEB8140
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-com-amaze-filemanager/hilog.txt:94754` — createSession: success, sessionId=52, surfaceNodeId=75161927680001
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-com-amaze-filemanager/hilog.txt:94755` — [IPC] ENTER oh_wm_set_last_session_local session=52
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-com-amaze-filemanager/hilog.txt:95595` — BBQ.create name=VRI[MainActivity] ptr=0000007F32FA6EA0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-com-amaze-filemanager/hilog.txt:95599` — getOhNativeWindow: unknown sessionId=52
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-com-amaze-filemanager/hilog.txt:95601` — BBQ.update: sessionId=52 → OHNativeWindow=0000007F39656790 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-com-amaze-filemanager/hilog.txt:95603` — BBQ.getSurface: returning Surface with mNativeObject=0000007F39656790 (sessionId=52)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-com-amaze-filemanager/hilog.txt:97415` — getOhNativeWindow: unknown sessionId=52
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-com-amaze-filemanager/hilog.txt:97417` — BBQ.update: sessionId=52 → OHNativeWindow=0000007F39656790 (1200x1920 fmt=-1)

### fd-com-kunzisoft-keepass-libre

PID [18460]; signed **own-ui** at `2026-10-01T06:33:44+0800`; hilog SHA `076e6ab9fa6c73f2fc61c22ff91f859c901939d53245aae61a1a4b4d73ebc57a`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-com-kunzisoft-keepass-libre/hilog.txt:45537` — createSession: bundle=com.kunzisoft.keepass.libre ability=FileDatabaseSelectActivity name=com.kunzisoft.keepass.libre/com.kunzisoft.keepass.activities.FileDatabaseSelectActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3beb7e20 token=0000007F3BEB7E20
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-com-kunzisoft-keepass-libre/hilog.txt:45602` — createSession: success, sessionId=54, surfaceNodeId=79285096284161
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-com-kunzisoft-keepass-libre/hilog.txt:45603` — [IPC] ENTER oh_wm_set_last_session_local session=54
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-com-kunzisoft-keepass-libre/hilog.txt:46656` — BBQ.create name=VRI[FileDatabaseSelectActivity] ptr=0000007F32F31000
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-com-kunzisoft-keepass-libre/hilog.txt:46660` — getOhNativeWindow: unknown sessionId=54
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-com-kunzisoft-keepass-libre/hilog.txt:46662` — BBQ.update: sessionId=54 → OHNativeWindow=0000007F3AB3AC90 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-com-kunzisoft-keepass-libre/hilog.txt:46663` — BBQ.getSurface: returning Surface with mNativeObject=0000007F3AB3AC90 (sessionId=54)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-com-kunzisoft-keepass-libre/hilog.txt:47072` — getOhNativeWindow: unknown sessionId=54
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-com-kunzisoft-keepass-libre/hilog.txt:47074` — BBQ.update: sessionId=54 → OHNativeWindow=0000007F3AB3AC90 (1200x1920 fmt=-1)

### fd-droidify

PID [19478]; signed **own-ui** at `2026-10-01T06:33:44+0800`; hilog SHA `a8b4eae64358e25eafaf43924deed5f487ec1ce7d8fcc87e5157222e6e2631aa`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-droidify/hilog.txt:65663` — createSession: bundle=com.looker.droidify ability=MainActivity name=com.looker.droidify/com.looker.droidify.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3beb8460 token=0000007F3BEB8460
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-droidify/hilog.txt:65729` — createSession: success, sessionId=56, surfaceNodeId=83657372991489
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-droidify/hilog.txt:65730` — [IPC] ENTER oh_wm_set_last_session_local session=56
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-droidify/hilog.txt:66171` — BBQ.create name=VRI[MainActivity] ptr=0000007F32F64A10
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-droidify/hilog.txt:66175` — getOhNativeWindow: unknown sessionId=56
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-droidify/hilog.txt:66177` — BBQ.update: sessionId=56 → OHNativeWindow=0000007F3A5BE290 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-droidify/hilog.txt:66178` — BBQ.getSurface: returning Surface with mNativeObject=0000007F3A5BE290 (sessionId=56)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-droidify/hilog.txt:67067` — getOhNativeWindow: unknown sessionId=56
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-droidify/hilog.txt:67069` — BBQ.update: sessionId=56 → OHNativeWindow=0000007F3A5BE290 (1200x1920 fmt=-1)

### fd-etar

PID [27972]; signed **own-ui** at `2026-10-01T06:33:44+0800`; hilog SHA `7662e6e94f4394077556714aac661eed62514d0ee54a974fc0477859dd20e309`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-etar/hilog.txt:48892` — createSession: bundle=ws.xsoh.etar ability=AllInOneActivity name=ws.xsoh.etar/com.android.calendar.AllInOneActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3beb8dc0 token=0000007F3BEB8DC0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-etar/hilog.txt:48958` — createSession: success, sessionId=77, surfaceNodeId=120138825203713
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-etar/hilog.txt:48959` — [IPC] ENTER oh_wm_set_last_session_local session=77
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-etar/hilog.txt:49571` — BBQ.create name=VRI[AllInOneActivity] ptr=0000007F33EF8D30
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-etar/hilog.txt:49575` — getOhNativeWindow: unknown sessionId=77
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-etar/hilog.txt:49577` — BBQ.update: sessionId=77 → OHNativeWindow=0000007F3A443B50 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-etar/hilog.txt:49578` — BBQ.getSurface: returning Surface with mNativeObject=0000007F3A443B50 (sessionId=77)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-etar/hilog.txt:50100` — getOhNativeWindow: unknown sessionId=77
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-etar/hilog.txt:50130` — BBQ.update: sessionId=77 → OHNativeWindow=0000007F3A443B50 (1200x1920 fmt=-1)

### fd-feeder

PID [28904]; signed **own-ui** at `2026-10-01T06:33:44+0800`; hilog SHA `b253184122c38c15b75829031a7f3da87ba1294db002c2a9a0297a3d8d882450`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-feeder/hilog.txt:44666` — createSession: bundle=com.nononsenseapps.feeder ability=MainActivity name=com.nononsenseapps.feeder/com.nononsenseapps.feeder.ui.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3beb7e20 token=0000007F3BEB7E20
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-feeder/hilog.txt:44752` — createSession: success, sessionId=80, surfaceNodeId=124141734723585
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-feeder/hilog.txt:44754` — [IPC] ENTER oh_wm_set_last_session_local session=80
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-feeder/hilog.txt:55125` — BBQ.create name=VRI[MainActivity] ptr=0000007F33DB36C0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-feeder/hilog.txt:55129` — getOhNativeWindow: unknown sessionId=80
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-feeder/hilog.txt:55131` — BBQ.update: sessionId=80 → OHNativeWindow=0000007F3AB07DD0 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-feeder/hilog.txt:55132` — BBQ.getSurface: returning Surface with mNativeObject=0000007F3AB07DD0 (sessionId=80)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-feeder/hilog.txt:55878` — getOhNativeWindow: unknown sessionId=80
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-feeder/hilog.txt:55880` — BBQ.update: sessionId=80 → OHNativeWindow=0000007F3AB07DD0 (1200x1920 fmt=-1)

### fd-filemanager

PID [31348, 31385, 31409]; signed **own-ui** at `2026-10-01T06:33:44+0800`; hilog SHA `4ee160bcad5952a9ebef6ec50a74311f5922edc29434c2f83dbf30690d4db37a`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-filemanager/hilog.txt:52011` — createSession: bundle=org.fossify.filemanager ability=MainActivity name=org.fossify.filemanager/org.fossify.filemanager.activities.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3beb7e20 token=0000007F3BEB7E20
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-filemanager/hilog.txt:52073` — createSession: success, sessionId=84, surfaceNodeId=134797548584961
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-filemanager/hilog.txt:52074` — [IPC] ENTER oh_wm_set_last_session_local session=84
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-filemanager/hilog.txt:54673` — BBQ.create name=VRI[MainActivity] ptr=0000007F33DB1540
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-filemanager/hilog.txt:54677` — getOhNativeWindow: unknown sessionId=84
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-filemanager/hilog.txt:54679` — BBQ.update: sessionId=84 → OHNativeWindow=0000007F3A227DD0 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-filemanager/hilog.txt:54680` — BBQ.getSurface: returning Surface with mNativeObject=0000007F3A227DD0 (sessionId=84)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-filemanager/hilog.txt:55352` — getOhNativeWindow: unknown sessionId=84
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-filemanager/hilog.txt:55354` — BBQ.update: sessionId=84 → OHNativeWindow=0000007F3A227DD0 (1200x1920 fmt=-1)

### fd-fitness

PID [20460]; signed **own-ui** at `2026-10-01T06:33:44+0800`; hilog SHA `7613e85760cdebc9ddf0d35c3b3f29ff1f412d75922006793244293c4b213e6d`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-fitness/hilog.txt:63091` — createSession: bundle=de.tadris.fitness ability=MainActivity name=de.tadris.fitness/de.tadris.fitness.ui.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3b8bee20 token=0000007F3B8BEE20
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-fitness/hilog.txt:63243` — createSession: success, sessionId=58, surfaceNodeId=87875030876161
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-fitness/hilog.txt:63244` — [IPC] ENTER oh_wm_set_last_session_local session=58
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-fitness/hilog.txt:69741` — BBQ.create name=VRI[MainActivity] ptr=0000007F3A17D830
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-fitness/hilog.txt:69746` — getOhNativeWindow: unknown sessionId=58
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-fitness/hilog.txt:69748` — BBQ.update: sessionId=58 → OHNativeWindow=0000007F3B62CDD0 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-fitness/hilog.txt:69749` — BBQ.getSurface: returning Surface with mNativeObject=0000007F3B62CDD0 (sessionId=58)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-fitness/hilog.txt:70951` — getOhNativeWindow: unknown sessionId=58
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-fitness/hilog.txt:70953` — BBQ.update: sessionId=58 → OHNativeWindow=0000007F3B62CDD0 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-fitness/hilog.txt:74945` — createSession: bundle=de.tadris.fitness ability=MainActivity name=de.tadris.fitness/de.tadris.fitness.ui.MainActivity, androidType=2 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3b8bee20 token=0000007F3B8BEE20
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-fitness/hilog.txt:75024` — createSession: success, sessionId=59, surfaceNodeId=87875030876164
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-fitness/hilog.txt:75025` — [IPC] ENTER oh_wm_set_last_session_local session=59
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-fitness/hilog.txt:76781` — BBQ.create name=VRI[MainActivity] ptr=0000007F312F13F0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-fitness/hilog.txt:76783` — getOhNativeWindow: unknown sessionId=59
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-fitness/hilog.txt:76786` — BBQ.update: sessionId=59 → OHNativeWindow=0000007F3B410790 (864x612 fmt=-2)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-fitness/hilog.txt:76787` — BBQ.getSurface: returning Surface with mNativeObject=0000007F3B410790 (sessionId=59)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-fitness/hilog.txt:77299` — getOhNativeWindow: unknown sessionId=59
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/5ea34a4500000000000000001123012c/fd-fitness/hilog.txt:77303` — BBQ.update: sessionId=59 → OHNativeWindow=0000007F3B410790 (864x612 fmt=-2)

### fd-gallery

PID [26093, 26126]; signed **own-ui** at `2026-10-01T06:25:18+0800`; hilog SHA `e506091039e14d4ee9182d431a7d141a7964f430016a0f9fcf5fca79da9c0658`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-gallery/hilog.txt:64414` — createSession: bundle=org.fossify.gallery ability=MainActivity name=org.fossify.gallery/org.fossify.gallery.activities.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3566be20 token=0000007F3566BE20
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-gallery/hilog.txt:64700` — createSession: success, sessionId=360, surfaceNodeId=112210315575297
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-gallery/hilog.txt:64701` — [IPC] ENTER oh_wm_set_last_session_local session=360
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-gallery/hilog.txt:66019` — BBQ.create name=VRI[MainActivity] ptr=0000007F2FAF04F0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-gallery/hilog.txt:66024` — getOhNativeWindow: unknown sessionId=360
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-gallery/hilog.txt:66026` — BBQ.update: sessionId=360 → OHNativeWindow=0000007F33F903D0 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-gallery/hilog.txt:66027` — BBQ.getSurface: returning Surface with mNativeObject=0000007F33F903D0 (sessionId=360)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-gallery/hilog.txt:67338` — getOhNativeWindow: unknown sessionId=360
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-gallery/hilog.txt:67403` — BBQ.update: sessionId=360 → OHNativeWindow=0000007F33F903D0 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-gallery/hilog.txt:68075` — getOhNativeWindow: unknown sessionId=360
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-gallery/hilog.txt:68077` — BBQ.update: sessionId=360 → OHNativeWindow=0000007F33F903D0 (1200x1920 fmt=-1)

### fd-k9

PID [30155, 30195]; signed **own-ui** at `2026-10-01T06:25:18+0800`; hilog SHA `756b91949e014e80beb26455eb43164b2a235c2a2710b5c6a25d4c7ecdc606b1`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-k9/hilog.txt:65416` — createSession: bundle=com.fsck.k9 ability=UpgradeDatabaseActivity name=com.fsck.k9/com.fsck.k9.activity.UpgradeDatabaseActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f355ece20 token=0000007F355ECE20
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-k9/hilog.txt:65479` — createSession: success, sessionId=365, surfaceNodeId=129686537502721
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-k9/hilog.txt:65480` — [IPC] ENTER oh_wm_set_last_session_local session=365
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-k9/hilog.txt:65926` — BBQ.create name=VRI[UpgradeDatabaseActivity] ptr=0000007F33F981C0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-k9/hilog.txt:65948` — getOhNativeWindow: unknown sessionId=365
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-k9/hilog.txt:65950` — BBQ.update: sessionId=365 → OHNativeWindow=0000007F353293D0 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-k9/hilog.txt:65951` — BBQ.getSurface: returning Surface with mNativeObject=0000007F353293D0 (sessionId=365)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-k9/hilog.txt:66730` — getOhNativeWindow: unknown sessionId=365
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-k9/hilog.txt:66732` — BBQ.update: sessionId=365 → OHNativeWindow=0000007F353293D0 (1200x1920 fmt=-1)

### fd-libretube

PID [1582]; signed **own-ui** at `2026-10-01T06:25:18+0800`; hilog SHA `72769292924280da10b7911fbcb201d6bd6c252130cd0ff1f46f1893dbaecdf0`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-libretube/hilog.txt:52369` — createSession: bundle=com.github.libretube ability=MainActivity name=com.github.libretube/com.github.libretube.Default, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f355ece20 token=0000007F355ECE20
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-libretube/hilog.txt:52431` — createSession: success, sessionId=369, surfaceNodeId=6794638262273
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-libretube/hilog.txt:52432` — [IPC] ENTER oh_wm_set_last_session_local session=369
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-libretube/hilog.txt:52934` — BBQ.create name=VRI[Default] ptr=0000007F2A7F0E30
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-libretube/hilog.txt:52938` — getOhNativeWindow: unknown sessionId=369
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-libretube/hilog.txt:52940` — BBQ.update: sessionId=369 → OHNativeWindow=0000007F34C26650 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-libretube/hilog.txt:52941` — BBQ.getSurface: returning Surface with mNativeObject=0000007F34C26650 (sessionId=369)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-libretube/hilog.txt:53342` — getOhNativeWindow: unknown sessionId=369
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-libretube/hilog.txt:53344` — BBQ.update: sessionId=369 → OHNativeWindow=0000007F34C26650 (1200x1920 fmt=-1)

### fd-minetest

PID [4327]; signed **own-ui** at `2026-10-01T06:25:18+0800`; hilog SHA `a1a158c1fd73be4a017dbcd87ce1aea03706f32a300c6d7d6ad0932698155560`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-minetest/hilog.txt:32496` — createSession: bundle=net.minetest.minetest ability=MainActivity name=net.minetest.minetest/net.minetest.minetest.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3566c140 token=0000007F3566C140
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-minetest/hilog.txt:32566` — createSession: success, sessionId=373, surfaceNodeId=18584323489793
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-minetest/hilog.txt:32567` — [IPC] ENTER oh_wm_set_last_session_local session=373
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-minetest/hilog.txt:32763` — BBQ.create name=VRI[MainActivity] ptr=0000007F33EAC220
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-minetest/hilog.txt:32767` — getOhNativeWindow: unknown sessionId=373
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-minetest/hilog.txt:32769` — BBQ.update: sessionId=373 → OHNativeWindow=0000007F3530C8D0 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-minetest/hilog.txt:32770` — BBQ.getSurface: returning Surface with mNativeObject=0000007F3530C8D0 (sessionId=373)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-minetest/hilog.txt:33119` — getOhNativeWindow: unknown sessionId=373
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-minetest/hilog.txt:33121` — BBQ.update: sessionId=373 → OHNativeWindow=0000007F3530C8D0 (1200x1920 fmt=-1)

### fd-mobile

PID [15199]; signed **black** at `2026-10-01T06:25:18+0800`; hilog SHA `23f843aa0be4c05e78e159dbbb29c5b030c185d6d73b5c385f01ba7c9e7bf9df`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-mobile/hilog.txt:51937` — createSession: bundle=org.jellyfin.mobile ability=MainActivity name=org.jellyfin.mobile/org.jellyfin.mobile.MainActivity, androidType=2 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f36ed4aa0 token=0000007F36ED4AA0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-mobile/hilog.txt:52000` — createSession: success, sessionId=401, surfaceNodeId=65279207931905
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-mobile/hilog.txt:52001` — [IPC] ENTER oh_wm_set_last_session_local session=401
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-mobile/hilog.txt:52354` — BBQ.create name=VRI[MainActivity] ptr=0000007F34EAF650
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-mobile/hilog.txt:52358` — getOhNativeWindow: unknown sessionId=401
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-mobile/hilog.txt:52360` — BBQ.update: sessionId=401 → OHNativeWindow=0000007F3678DB50 (1283x2064 fmt=-3)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-mobile/hilog.txt:52361` — BBQ.getSurface: returning Surface with mNativeObject=0000007F3678DB50 (sessionId=401)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-mobile/hilog.txt:52899` — getOhNativeWindow: unknown sessionId=401
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-mobile/hilog.txt:52902` — BBQ.update: sessionId=401 → OHNativeWindow=0000007F3678DB50 (1283x2064 fmt=-3)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-mobile/hilog.txt:53033` — createSession: bundle=org.jellyfin.mobile ability=MainActivity name=org.jellyfin.mobile/org.jellyfin.mobile.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f36ed4aa0 token=0000007F36ED4AA0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-mobile/hilog.txt:53109` — createSession: success, sessionId=402, surfaceNodeId=65279207931908
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-mobile/hilog.txt:53110` — [IPC] ENTER oh_wm_set_last_session_local session=402
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-mobile/hilog.txt:53396` — BBQ.create name=VRI[MainActivity] ptr=0000007F2B8DA1F0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-mobile/hilog.txt:53398` — getOhNativeWindow: unknown sessionId=402
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-mobile/hilog.txt:53400` — BBQ.update: sessionId=402 → OHNativeWindow=0000007F354867D0 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-mobile/hilog.txt:53401` — BBQ.getSurface: returning Surface with mNativeObject=0000007F354867D0 (sessionId=402)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-mobile/hilog.txt:53687` — getOhNativeWindow: unknown sessionId=402
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-mobile/hilog.txt:53689` — BBQ.update: sessionId=402 → OHNativeWindow=0000007F354867D0 (1200x1920 fmt=-1)

### fd-mpv

PID [5657]; signed **own-ui** at `2026-10-01T06:25:18+0800`; hilog SHA `c47fc40fa84a3ade4a18922e6a6a8f64c54d3d918c4f01a006dc661d762b8683`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-mpv/hilog.txt:32417` — createSession: bundle=is.xyz.mpv ability=MainActivity name=is.xyz.mpv/is.xyz.mpv.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3566be20 token=0000007F3566BE20
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-mpv/hilog.txt:32480` — createSession: success, sessionId=375, surfaceNodeId=24296629993473
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-mpv/hilog.txt:32481` — [IPC] ENTER oh_wm_set_last_session_local session=375
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-mpv/hilog.txt:32725` — BBQ.create name=VRI[MainActivity] ptr=0000007F33F28E80
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-mpv/hilog.txt:32732` — getOhNativeWindow: unknown sessionId=375
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-mpv/hilog.txt:32734` — BBQ.update: sessionId=375 → OHNativeWindow=0000007F34DA6790 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-mpv/hilog.txt:32737` — BBQ.getSurface: returning Surface with mNativeObject=0000007F34DA6790 (sessionId=375)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-mpv/hilog.txt:33198` — getOhNativeWindow: unknown sessionId=375
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-mpv/hilog.txt:33200` — BBQ.update: sessionId=375 → OHNativeWindow=0000007F34DA6790 (1200x1920 fmt=-1)

### fd-musicplayer

PID [6521]; signed **desktop** at `2026-10-01T06:25:18+0800`; hilog SHA `1b4d8614661e7017820cabddd617afe50b28743e1a9df6b7a7a8cad357d300b7`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-musicplayer/hilog.txt:38735` — createSession: bundle=org.fossify.musicplayer ability=SplashActivity name=org.fossify.musicplayer/org.fossify.musicplayer.activities.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f34352dc0 token=0000007F34352DC0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-musicplayer/hilog.txt:38805` — createSession: success, sessionId=378, surfaceNodeId=28007481737217
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-musicplayer/hilog.txt:38806` — [IPC] ENTER oh_wm_set_last_session_local session=378
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-musicplayer/hilog.txt:41211` — BBQ.create name=VRI[MainActivity] ptr=0000007F2D74D750
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-musicplayer/hilog.txt:41224` — getOhNativeWindow: unknown sessionId=378
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-musicplayer/hilog.txt:41231` — BBQ.update: sessionId=378 → OHNativeWindow=0000007F339C8150 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-musicplayer/hilog.txt:41235` — BBQ.getSurface: returning Surface with mNativeObject=0000007F339C8150 (sessionId=378)

### fd-netguard

PID [22571]; signed **own-ui** at `2026-10-01T06:25:18+0800`; hilog SHA `f77b5613366a60bd446b0e1d006f30d5a7b79ff364191351c8c2113b861008ba`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-netguard/hilog.txt:25778` — createSession: bundle=eu.faircode.netguard ability=ActivityMain name=eu.faircode.netguard/eu.faircode.netguard.ActivityMain, androidType=2 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3566c140 token=0000007F3566C140
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-netguard/hilog.txt:25845` — createSession: success, sessionId=351, surfaceNodeId=96941706838017
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-netguard/hilog.txt:25846` — [IPC] ENTER oh_wm_set_last_session_local session=351
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-netguard/hilog.txt:26552` — BBQ.create name=VRI[ActivityMain] ptr=0000007F33965550
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-netguard/hilog.txt:26556` — getOhNativeWindow: unknown sessionId=351
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-netguard/hilog.txt:26558` — BBQ.update: sessionId=351 → OHNativeWindow=0000007F33E19010 (1283x2064 fmt=-3)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-netguard/hilog.txt:26559` — BBQ.getSurface: returning Surface with mNativeObject=0000007F33E19010 (sessionId=351)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-netguard/hilog.txt:27077` — getOhNativeWindow: unknown sessionId=351
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-netguard/hilog.txt:27080` — BBQ.update: sessionId=351 → OHNativeWindow=0000007F33E19010 (1283x2064 fmt=-3)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-netguard/hilog.txt:27203` — createSession: bundle=eu.faircode.netguard ability=ActivityMain name=eu.faircode.netguard/eu.faircode.netguard.ActivityMain, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3566c140 token=0000007F3566C140
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-netguard/hilog.txt:27267` — createSession: success, sessionId=352, surfaceNodeId=96941706838020
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-netguard/hilog.txt:27268` — [IPC] ENTER oh_wm_set_last_session_local session=352
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-netguard/hilog.txt:27538` — BBQ.create name=VRI[ActivityMain] ptr=0000007F2A0FE2C0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-netguard/hilog.txt:27540` — getOhNativeWindow: unknown sessionId=352
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-netguard/hilog.txt:27542` — BBQ.update: sessionId=352 → OHNativeWindow=0000007F2BFA6050 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-netguard/hilog.txt:27543` — BBQ.getSurface: returning Surface with mNativeObject=0000007F2BFA6050 (sessionId=352)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-netguard/hilog.txt:28012` — getOhNativeWindow: unknown sessionId=352
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-netguard/hilog.txt:28014` — BBQ.update: sessionId=352 → OHNativeWindow=0000007F2BFA6050 (1200x1920 fmt=-1)

### fd-noice

PID [23406]; signed **own-ui** at `2026-10-01T06:25:18+0800`; hilog SHA `4d6d349f1862c80300a3f67975a7e89c90946b453a95f95653f7c318468b3548`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-noice/hilog.txt:43405` — createSession: bundle=com.github.ashutoshgngwr.noice ability=MainActivity name=com.github.ashutoshgngwr.noice/com.github.ashutoshgngwr.noice.activity.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3566c910 token=0000007F3566C910
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-noice/hilog.txt:43479` — createSession: success, sessionId=355, surfaceNodeId=100528004530177
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-noice/hilog.txt:43480` — [IPC] ENTER oh_wm_set_last_session_local session=355
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-noice/hilog.txt:43981` — BBQ.create name=VRI[MainActivity] ptr=0000007F2C8539B0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-noice/hilog.txt:43985` — getOhNativeWindow: unknown sessionId=355
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-noice/hilog.txt:43987` — BBQ.update: sessionId=355 → OHNativeWindow=0000007F34C5AB50 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-noice/hilog.txt:43988` — BBQ.getSurface: returning Surface with mNativeObject=0000007F34C5AB50 (sessionId=355)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-noice/hilog.txt:46970` — createSession: bundle=com.github.ashutoshgngwr.noice ability=AppIntroActivity name=com.github.ashutoshgngwr.noice/com.github.ashutoshgngwr.noice.activity.AppIntroActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f356662d0 token=0000007F356662D0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-noice/hilog.txt:47028` — createSession: success, sessionId=356, surfaceNodeId=100528004530180
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-noice/hilog.txt:47029` — [IPC] ENTER oh_wm_set_last_session_local session=356
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-noice/hilog.txt:47330` — getOhNativeWindow: unknown sessionId=355
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-noice/hilog.txt:47331` — BBQ.update: getOhNativeWindow(sessionId=355) returned null
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-noice/hilog.txt:47449` — BBQ.create name=VRI[AppIntroActivity] ptr=0000007F26BF54C0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-noice/hilog.txt:47451` — getOhNativeWindow: unknown sessionId=356
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-noice/hilog.txt:47453` — BBQ.update: sessionId=356 → OHNativeWindow=0000007F282523D0 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-noice/hilog.txt:47454` — BBQ.getSurface: returning Surface with mNativeObject=0000007F282523D0 (sessionId=356)

### fd-notes

PID [7463]; signed **own-ui** at `2026-10-01T06:25:18+0800`; hilog SHA `8fbe3efb18773a07b0f71a9c49940f38a74149351895b1de8c208f9d3e252f7d`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-notes/hilog.txt:43999` — createSession: bundle=org.fossify.notes ability=SplashActivity name=org.fossify.notes/org.fossify.notes.activities.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f34337780 token=0000007F34337780
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-notes/hilog.txt:44064` — createSession: success, sessionId=381, surfaceNodeId=32053340930049
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-notes/hilog.txt:44065` — [IPC] ENTER oh_wm_set_last_session_local session=381
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-notes/hilog.txt:44782` — BBQ.create name=VRI[MainActivity] ptr=0000007F2D762E80
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-notes/hilog.txt:44786` — getOhNativeWindow: unknown sessionId=381
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-notes/hilog.txt:44788` — BBQ.update: sessionId=381 → OHNativeWindow=0000007F34C4A8D0 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-notes/hilog.txt:44790` — BBQ.getSurface: returning Surface with mNativeObject=0000007F34C4A8D0 (sessionId=381)

### fd-organicmaps

PID [8414, 8483, 8508, 8631, 8688, 8748, 8773, 8832, 8866, 8986, 9045]; signed **own-ui** at `2026-10-01T06:25:18+0800`; hilog SHA `699011b5ab78a0718fb66dce188de1c792bb0ded5094113f404d93f55f5a96dc`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-organicmaps/hilog.txt:27295` — createSession: bundle=app.organicmaps ability=SplashActivity name=app.organicmaps/app.organicmaps.SplashActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f355ed2d0 token=0000007F355ED2D0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-organicmaps/hilog.txt:27359` — createSession: success, sessionId=388, surfaceNodeId=37679748087809
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-organicmaps/hilog.txt:27360` — [IPC] ENTER oh_wm_set_last_session_local session=388
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-organicmaps/hilog.txt:27703` — BBQ.create name=VRI[SplashActivity] ptr=0000007F339F0380
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-organicmaps/hilog.txt:27710` — getOhNativeWindow: unknown sessionId=388
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-organicmaps/hilog.txt:27713` — BBQ.update: sessionId=388 → OHNativeWindow=0000007F34C5F790 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-organicmaps/hilog.txt:27714` — BBQ.getSurface: returning Surface with mNativeObject=0000007F34C5F790 (sessionId=388)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-organicmaps/hilog.txt:29739` — getOhNativeWindow: unknown sessionId=388
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-organicmaps/hilog.txt:29741` — BBQ.update: sessionId=388 → OHNativeWindow=0000007F34C5F790 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-organicmaps/hilog.txt:65700` — createSession: bundle=app.organicmaps ability=SplashActivity name=app.organicmaps/app.organicmaps.SplashActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f3551f460 token=0000007F3551F460
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-organicmaps/hilog.txt:65777` — createSession: success, sessionId=389, surfaceNodeId=38079180046337
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-organicmaps/hilog.txt:65778` — [IPC] ENTER oh_wm_set_last_session_local session=389
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-organicmaps/hilog.txt:66090` — BBQ.create name=VRI[SplashActivity] ptr=0000007F339D8150
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-organicmaps/hilog.txt:66094` — getOhNativeWindow: unknown sessionId=389
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-organicmaps/hilog.txt:66096` — BBQ.update: sessionId=389 → OHNativeWindow=0000007F34C1FC90 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-organicmaps/hilog.txt:66097` — BBQ.getSurface: returning Surface with mNativeObject=0000007F34C1FC90 (sessionId=389)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-organicmaps/hilog.txt:68340` — getOhNativeWindow: unknown sessionId=389
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c/fd-organicmaps/hilog.txt:68342` — BBQ.update: sessionId=389 → OHNativeWindow=0000007F34C1FC90 (1200x1920 fmt=-1)

### fd-reader

PID [11994]; signed **own-ui** at `2026-10-01T06:25:18+0800`; hilog SHA `570240d894b46c4bf1c21626382468d233ba95fb45f6da780048d19cb85e96c0`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-reader/hilog.txt:49027` — createSession: bundle=me.ash.reader ability=MainActivity name=me.ash.reader/me.ash.reader.infrastructure.android.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f36ed8140 token=0000007F36ED8140
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-reader/hilog.txt:49090` — createSession: success, sessionId=396, surfaceNodeId=51513837748225
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-reader/hilog.txt:49091` — [IPC] ENTER oh_wm_set_last_session_local session=396
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-reader/hilog.txt:69122` — BBQ.create name=VRI[MainActivity] ptr=0000007F2CC99460
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-reader/hilog.txt:69126` — getOhNativeWindow: unknown sessionId=396
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-reader/hilog.txt:69128` — BBQ.update: sessionId=396 → OHNativeWindow=0000007F363A2010 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-reader/hilog.txt:69129` — BBQ.getSurface: returning Surface with mNativeObject=0000007F363A2010 (sessionId=396)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-reader/hilog.txt:71961` — getOhNativeWindow: unknown sessionId=396
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-reader/hilog.txt:71963` — BBQ.update: sessionId=396 → OHNativeWindow=0000007F363A2010 (1200x1920 fmt=-1)

### fd-shatteredpixeldungeon

PID [14207]; signed **white** at `2026-10-01T06:25:18+0800`; hilog SHA `0c800e558e090517d0719a9d0bf5344212ffb52f57c6a436262603404037a0b8`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-shatteredpixeldungeon/hilog.txt:29407` — createSession: bundle=com.shatteredpixel.shatteredpixeldungeon ability=AndroidLauncher name=com.shatteredpixel.shatteredpixeldungeon/com.shatteredpixel.shatteredpixeldungeon.android.AndroidLauncher, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f36ed3fb0 token=0000007F36ED3FB0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-shatteredpixeldungeon/hilog.txt:29487` — createSession: success, sessionId=399, surfaceNodeId=61018600374273
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-shatteredpixeldungeon/hilog.txt:29489` — [IPC] ENTER oh_wm_set_last_session_local session=399
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-shatteredpixeldungeon/hilog.txt:29697` — BBQ.create name=VRI[AndroidLauncher] ptr=0000007F36BD4C60
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-shatteredpixeldungeon/hilog.txt:29704` — getOhNativeWindow: unknown sessionId=399
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-shatteredpixeldungeon/hilog.txt:29707` — BBQ.update: sessionId=399 → OHNativeWindow=0000007F35461010 (1200x1920 fmt=-3)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-shatteredpixeldungeon/hilog.txt:29708` — BBQ.getSurface: returning Surface with mNativeObject=0000007F35461010 (sessionId=399)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-shatteredpixeldungeon/hilog.txt:29806` — BBQ.create name=SurfaceView[com.shatteredpixel.shatteredpixeldungeon/com.shatte ptr=0000007F350204F0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-shatteredpixeldungeon/hilog.txt:29817` — BBQ.update: sessionId=399 → OHNativeWindow=0000007F35461B50 (1200x1920 fmt=4)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-shatteredpixeldungeon/hilog.txt:29999` — java.lang.IllegalArgumentException: Make sure the SurfaceView or associated SurfaceHolder has a valid Surface
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-shatteredpixeldungeon/hilog.txt:30159` — getOhNativeWindow: unknown sessionId=399
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-shatteredpixeldungeon/hilog.txt:30189` — BBQ.update: sessionId=399 → OHNativeWindow=0000007F35461010 (1200x1920 fmt=-3)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-shatteredpixeldungeon/hilog.txt:30361` — getOhNativeWindow: unknown sessionId=399
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c/fd-shatteredpixeldungeon/hilog.txt:30363` — BBQ.update: sessionId=399 → OHNativeWindow=0000007F35461010 (1200x1920 fmt=-3)

### fd-stk

PID [28999]; signed **own-ui** at `2026-10-01T06:39:59+0800`; hilog SHA `8bcfa90008c768f32551a557f74a4c522afa866e794defcc41fe77353d7daaec`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-stk/hilog.txt:34338` — createSession: bundle=org.supertuxkart.stk ability=SuperTuxKartActivity name=org.supertuxkart.stk/org.supertuxkart.stk.SuperTuxKartActivity, androidType=2 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7fa6121150 token=0000007FA6121150
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-stk/hilog.txt:34403` — createSession: success, sessionId=406, surfaceNodeId=124549756616705
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-stk/hilog.txt:34404` — [IPC] ENTER oh_wm_set_last_session_local session=406
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-stk/hilog.txt:34763` — BBQ.create name=VRI[SuperTuxKartActivity] ptr=0000007F22BEA670
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-stk/hilog.txt:34767` — getOhNativeWindow: unknown sessionId=406
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-stk/hilog.txt:34769` — BBQ.update: sessionId=406 → OHNativeWindow=0000007F2408FDD0 (1139x1920 fmt=-2)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-stk/hilog.txt:34771` — BBQ.getSurface: returning Surface with mNativeObject=0000007F2408FDD0 (sessionId=406)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-stk/hilog.txt:35129` — getOhNativeWindow: unknown sessionId=406
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-stk/hilog.txt:35131` — BBQ.update: sessionId=406 → OHNativeWindow=0000007F2408FDD0 (1139x1920 fmt=-2)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-stk/hilog.txt:35339` — createSession: bundle=org.supertuxkart.stk ability=SuperTuxKartActivity name=org.supertuxkart.stk/org.supertuxkart.stk.SuperTuxKartActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7fa6121150 token=0000007FA6121150
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-stk/hilog.txt:35420` — createSession: success, sessionId=408, surfaceNodeId=124549756616708
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-stk/hilog.txt:35421` — [IPC] ENTER oh_wm_set_last_session_local session=408
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-stk/hilog.txt:35614` — BBQ.create name=VRI[SuperTuxKartActivity] ptr=0000007F18B64E90
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-stk/hilog.txt:35616` — getOhNativeWindow: unknown sessionId=408
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-stk/hilog.txt:35618` — BBQ.update: sessionId=408 → OHNativeWindow=0000007F227E7150 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-stk/hilog.txt:35620` — BBQ.getSurface: returning Surface with mNativeObject=0000007F227E7150 (sessionId=408)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-stk/hilog.txt:35908` — getOhNativeWindow: unknown sessionId=408
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-stk/hilog.txt:35910` — BBQ.update: sessionId=408 → OHNativeWindow=0000007F227E7150 (1200x1920 fmt=-1)

### fd-tasks

PID [23875]; signed **own-ui** at `2026-10-01T06:39:59+0800`; hilog SHA `4bffeb81347505ead7cb18912838d7d6cb0fb6f76e09ccd98d4e350d84b3bb61`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-tasks/hilog.txt:57076` — createSession: bundle=org.tasks ability=MainActivity name=org.tasks/com.todoroo.astrid.activity.TaskListActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f24478140 token=0000007F24478140
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-tasks/hilog.txt:57138` — createSession: success, sessionId=391, surfaceNodeId=102542344192001
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-tasks/hilog.txt:57139` — [IPC] ENTER oh_wm_set_last_session_local session=391
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-tasks/hilog.txt:72741` — BBQ.create name=VRI[TaskListActivity] ptr=0000007F1B55F310
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-tasks/hilog.txt:72745` — getOhNativeWindow: unknown sessionId=391
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-tasks/hilog.txt:72747` — BBQ.update: sessionId=391 → OHNativeWindow=0000007F23A20A10 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-tasks/hilog.txt:72748` — BBQ.getSurface: returning Surface with mNativeObject=0000007F23A20A10 (sessionId=391)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-tasks/hilog.txt:73492` — getOhNativeWindow: unknown sessionId=391
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-tasks/hilog.txt:73494` — BBQ.update: sessionId=391 → OHNativeWindow=0000007F23A20A10 (1200x1920 fmt=-1)

### fd-tusky

PID [24987, 25031]; signed **own-ui** at `2026-10-01T06:39:59+0800`; hilog SHA `bcf60d5fcf7031bbbf321a597056d24cf93412feaacdff9b482cc28514db1ac3`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-tusky/hilog.txt:85067` — createSession: bundle=com.keylesspalace.tusky ability=LoginActivity name=com.keylesspalace.tusky/com.keylesspalace.tusky.components.login.LoginActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f24478140 token=0000007F24478140
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-tusky/hilog.txt:85130` — createSession: success, sessionId=394, surfaceNodeId=107507326386177
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-tusky/hilog.txt:85131` — [IPC] ENTER oh_wm_set_last_session_local session=394
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-tusky/hilog.txt:85422` — BBQ.create name=VRI[LoginActivity] ptr=0000007F1C370720
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-tusky/hilog.txt:85426` — getOhNativeWindow: unknown sessionId=394
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-tusky/hilog.txt:85428` — BBQ.update: sessionId=394 → OHNativeWindow=0000007F22BC5910 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-tusky/hilog.txt:85429` — BBQ.getSurface: returning Surface with mNativeObject=0000007F22BC5910 (sessionId=394)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-tusky/hilog.txt:86032` — getOhNativeWindow: unknown sessionId=394
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-tusky/hilog.txt:86034` — BBQ.update: sessionId=394 → OHNativeWindow=0000007F22BC5910 (1200x1920 fmt=-1)

### fd-uhabits

PID [27057]; signed **own-ui** at `2026-10-01T06:39:59+0800`; hilog SHA `515df488950971ef3d9f9c98bdecad494ccc2be487c86556be8fba045f3989f2`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-uhabits/hilog.txt:34106` — createSession: bundle=org.isoron.uhabits ability=ListHabitsActivity name=org.isoron.uhabits/org.isoron.uhabits.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f24478140 token=0000007F24478140
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-uhabits/hilog.txt:34203` — createSession: success, sessionId=400, surfaceNodeId=116208930127873
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-uhabits/hilog.txt:34204` — [IPC] ENTER oh_wm_set_last_session_local session=400
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-uhabits/hilog.txt:37199` — BBQ.create name=VRI[MainActivity] ptr=0000007F2276EB90
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-uhabits/hilog.txt:37205` — getOhNativeWindow: unknown sessionId=400
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-uhabits/hilog.txt:37207` — BBQ.update: sessionId=400 → OHNativeWindow=0000007F23DD4510 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-uhabits/hilog.txt:37208` — BBQ.getSurface: returning Surface with mNativeObject=0000007F23DD4510 (sessionId=400)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-uhabits/hilog.txt:37866` — createSession: bundle=org.isoron.uhabits ability=ListHabitsActivity name=org.isoron.uhabits/org.isoron.uhabits.activities.intro.IntroActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f24478460 token=0000007F24478460
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-uhabits/hilog.txt:37971` — createSession: success, sessionId=401, surfaceNodeId=116208930127876
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-uhabits/hilog.txt:37972` — [IPC] ENTER oh_wm_set_last_session_local session=401
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-uhabits/hilog.txt:38434` — getOhNativeWindow: unknown sessionId=400
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-uhabits/hilog.txt:38435` — BBQ.update: getOhNativeWindow(sessionId=400) returned null
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-uhabits/hilog.txt:38896` — BBQ.create name=VRI[IntroActivity] ptr=0000007F166B15B0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-uhabits/hilog.txt:38898` — getOhNativeWindow: unknown sessionId=401
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-uhabits/hilog.txt:38900` — BBQ.update: sessionId=401 → OHNativeWindow=0000007F1C392790 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/fd-uhabits/hilog.txt:38901` — BBQ.getSurface: returning Surface with mNativeObject=0000007F1C392790 (sessionId=401)

### markor

PID [21942]; signed **own-ui** at `2026-10-01T06:39:59+0800`; hilog SHA `2422edbb78bcfecc437975355b35b3da5dfc29d4f71d317a3a5b8214832d669c`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/markor/hilog.txt:36960` — createSession: bundle=net.gsantner.markor ability=MainActivity name=net.gsantner.markor/net.gsantner.markor.activity.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f24477e20 token=0000007F24477E20
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/markor/hilog.txt:37020` — createSession: success, sessionId=385, surfaceNodeId=94240172408833
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/markor/hilog.txt:37021` — [IPC] ENTER oh_wm_set_last_session_local session=385
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/markor/hilog.txt:38480` — BBQ.create name=VRI[MainActivity] ptr=0000007F226F4470
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/markor/hilog.txt:38485` — getOhNativeWindow: unknown sessionId=385
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/markor/hilog.txt:38487` — BBQ.update: sessionId=385 → OHNativeWindow=0000007F22CCA010 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/markor/hilog.txt:38488` — BBQ.getSurface: returning Surface with mNativeObject=0000007F22CCA010 (sessionId=385)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/markor/hilog.txt:39948` — createSession: bundle=net.gsantner.markor ability=IntroActivity name=net.gsantner.markor/net.gsantner.markor.activity.IntroActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f23c56010 token=0000007F23C56010
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/markor/hilog.txt:40011` — createSession: success, sessionId=386, surfaceNodeId=94240172408836
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/markor/hilog.txt:40013` — [IPC] ENTER oh_wm_set_last_session_local session=386
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/markor/hilog.txt:40504` — getOhNativeWindow: unknown sessionId=385
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/markor/hilog.txt:40505` — BBQ.update: getOhNativeWindow(sessionId=385) returned null
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/markor/hilog.txt:41013` — BBQ.create name=VRI[IntroActivity] ptr=0000007F18B74320
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/markor/hilog.txt:41015` — getOhNativeWindow: unknown sessionId=386
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/markor/hilog.txt:41017` — BBQ.update: sessionId=386 → OHNativeWindow=0000007F1A3FA3D0 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/markor/hilog.txt:41018` — BBQ.getSurface: returning Surface with mNativeObject=0000007F1A3FA3D0 (sessionId=386)

### newpipe

PID [21050]; signed **own-ui** at `2026-10-01T06:39:59+0800`; hilog SHA `40541174c29c0d4ec748ed5faa7088d23ddead9735efd8c88d3827624020afee`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/newpipe/hilog.txt:53905` — createSession: bundle=org.schabi.newpipe ability=MainActivity name=org.schabi.newpipe/org.schabi.newpipe.MainActivity, androidType=2 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f2437f910 token=0000007F2437F910
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/newpipe/hilog.txt:53967` — createSession: success, sessionId=381, surfaceNodeId=90409061580801
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/newpipe/hilog.txt:53968` — [IPC] ENTER oh_wm_set_last_session_local session=381
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/newpipe/hilog.txt:54336` — BBQ.create name=VRI[MainActivity] ptr=0000007F1EAE59E0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/newpipe/hilog.txt:54340` — getOhNativeWindow: unknown sessionId=381
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/newpipe/hilog.txt:54342` — BBQ.update: sessionId=381 → OHNativeWindow=0000007F2424E510 (1283x2064 fmt=-3)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/newpipe/hilog.txt:54343` — BBQ.getSurface: returning Surface with mNativeObject=0000007F2424E510 (sessionId=381)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/newpipe/hilog.txt:57943` — getOhNativeWindow: unknown sessionId=381
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/newpipe/hilog.txt:57945` — BBQ.update: sessionId=381 → OHNativeWindow=0000007F2424E510 (1283x2064 fmt=-3)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/newpipe/hilog.txt:58444` — createSession: bundle=org.schabi.newpipe ability=MainActivity name=org.schabi.newpipe/org.schabi.newpipe.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f2437f910 token=0000007F2437F910
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/newpipe/hilog.txt:58510` — createSession: success, sessionId=382, surfaceNodeId=90409061580804
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/newpipe/hilog.txt:58511` — [IPC] ENTER oh_wm_set_last_session_local session=382
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/newpipe/hilog.txt:61526` — BBQ.create name=VRI[MainActivity] ptr=0000007F17F34F00
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/newpipe/hilog.txt:61529` — getOhNativeWindow: unknown sessionId=382
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/newpipe/hilog.txt:61531` — BBQ.update: sessionId=382 → OHNativeWindow=0000007F1A1EA790 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/newpipe/hilog.txt:61532` — BBQ.getSurface: returning Surface with mNativeObject=0000007F1A1EA790 (sessionId=382)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/newpipe/hilog.txt:62477` — getOhNativeWindow: unknown sessionId=382
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/newpipe/hilog.txt:62479` — BBQ.update: sessionId=382 → OHNativeWindow=0000007F1A1EA790 (1200x1920 fmt=-1)

### noice

PID [14154]; signed **own-ui** at `2026-10-01T06:39:59+0800`; hilog SHA `6890b510f196472925adced66a8cbb9badac662d707349413767cd4527a291cf`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/noice/hilog.txt:53863` — createSession: bundle=com.github.ashutoshgngwr.noice ability=MainActivity name=com.github.ashutoshgngwr.noice/com.github.ashutoshgngwr.noice.activity.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f24478460 token=0000007F24478460
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/noice/hilog.txt:53925` — createSession: success, sessionId=423, surfaceNodeId=60790967107585
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/noice/hilog.txt:53926` — [IPC] ENTER oh_wm_set_last_session_local session=423
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/noice/hilog.txt:54564` — BBQ.create name=VRI[MainActivity] ptr=0000007F1C3AC650
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/noice/hilog.txt:54568` — getOhNativeWindow: unknown sessionId=423
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/noice/hilog.txt:54570` — BBQ.update: sessionId=423 → OHNativeWindow=0000007F22DADA10 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/noice/hilog.txt:54571` — BBQ.getSurface: returning Surface with mNativeObject=0000007F22DADA10 (sessionId=423)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/noice/hilog.txt:57881` — createSession: bundle=com.github.ashutoshgngwr.noice ability=AppIntroActivity name=com.github.ashutoshgngwr.noice/com.github.ashutoshgngwr.noice.activity.AppIntroActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f23cda4c0 token=0000007F23CDA4C0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/noice/hilog.txt:57940` — createSession: success, sessionId=424, surfaceNodeId=60790967107588
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/noice/hilog.txt:57941` — [IPC] ENTER oh_wm_set_last_session_local session=424
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/noice/hilog.txt:58283` — getOhNativeWindow: unknown sessionId=423
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/noice/hilog.txt:58284` — BBQ.update: getOhNativeWindow(sessionId=423) returned null
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/noice/hilog.txt:58585` — BBQ.create name=VRI[AppIntroActivity] ptr=0000007F179F6AD0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/noice/hilog.txt:58587` — getOhNativeWindow: unknown sessionId=424
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/noice/hilog.txt:58589` — BBQ.update: sessionId=424 → OHNativeWindow=0000007F1984D410 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/noice/hilog.txt:58590` — BBQ.getSurface: returning Surface with mNativeObject=0000007F1984D410 (sessionId=424)

### ooniprobe

PID [20066]; signed **own-ui** at `2026-10-01T06:39:59+0800`; hilog SHA `3483b292fbea4bb34101f588bdcfd3d95e4468c614d8bf480edd33696c7a7653`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/ooniprobe/hilog.txt:53959` — createSession: bundle=org.openobservatory.ooniprobe ability=MainActivity name=org.openobservatory.ooniprobe/org.ooni.probe.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f24477fb0 token=0000007F24477FB0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/ooniprobe/hilog.txt:54022` — createSession: success, sessionId=379, surfaceNodeId=86182813761537
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/ooniprobe/hilog.txt:54023` — [IPC] ENTER oh_wm_set_last_session_local session=379
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/ooniprobe/hilog.txt:59366` — BBQ.create name=VRI[MainActivity] ptr=0000007F226DEB20
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/ooniprobe/hilog.txt:59370` — getOhNativeWindow: unknown sessionId=379
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/ooniprobe/hilog.txt:59379` — BBQ.update: sessionId=379 → OHNativeWindow=0000007F22DA7B50 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/ooniprobe/hilog.txt:59380` — BBQ.getSurface: returning Surface with mNativeObject=0000007F22DA7B50 (sessionId=379)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/ooniprobe/hilog.txt:62886` — getOhNativeWindow: unknown sessionId=379
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/ooniprobe/hilog.txt:62888` — BBQ.update: sessionId=379 → OHNativeWindow=0000007F22DA7B50 (1200x1920 fmt=-1)

### opencamera

PID [22784]; signed **own-ui** at `2026-10-01T06:39:59+0800`; hilog SHA `b0a170850479a99b89598d294a11ec4efb600cd22a15f38a2f7bc98071ba77b6`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/opencamera/hilog.txt:28056` — createSession: bundle=net.sourceforge.opencamera ability=MainActivity name=net.sourceforge.opencamera/net.sourceforge.opencamera.MainActivity, androidType=2 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f24477e20 token=0000007F24477E20
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/opencamera/hilog.txt:28118` — createSession: success, sessionId=388, surfaceNodeId=97856534872065
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/opencamera/hilog.txt:28119` — [IPC] ENTER oh_wm_set_last_session_local session=388
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/opencamera/hilog.txt:29265` — BBQ.create name=VRI[MainActivity] ptr=0000007F1B525290
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/opencamera/hilog.txt:29269` — getOhNativeWindow: unknown sessionId=388
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/opencamera/hilog.txt:29271` — BBQ.update: sessionId=388 → OHNativeWindow=0000007F227EB3D0 (1283x2064 fmt=-3)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/opencamera/hilog.txt:29272` — BBQ.getSurface: returning Surface with mNativeObject=0000007F227EB3D0 (sessionId=388)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/opencamera/hilog.txt:29767` — getOhNativeWindow: unknown sessionId=388
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/opencamera/hilog.txt:29770` — BBQ.update: sessionId=388 → OHNativeWindow=0000007F227EB3D0 (1283x2064 fmt=-3)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/opencamera/hilog.txt:31628` — createSession: bundle=net.sourceforge.opencamera ability=MainActivity name=net.sourceforge.opencamera/net.sourceforge.opencamera.MainActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f24477e20 token=0000007F24477E20
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/opencamera/hilog.txt:31686` — createSession: success, sessionId=389, surfaceNodeId=97856534872068
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/opencamera/hilog.txt:31687` — [IPC] ENTER oh_wm_set_last_session_local session=389
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/opencamera/hilog.txt:31835` — BBQ.create name=VRI[MainActivity] ptr=0000007F1B525220
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/opencamera/hilog.txt:31837` — getOhNativeWindow: unknown sessionId=389
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/opencamera/hilog.txt:31839` — BBQ.update: sessionId=389 → OHNativeWindow=0000007F180E6B50 (1200x1920 fmt=-3)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/opencamera/hilog.txt:31840` — BBQ.getSurface: returning Surface with mNativeObject=0000007F180E6B50 (sessionId=389)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/opencamera/hilog.txt:31982` — BBQ.create name=SurfaceView[net.sourceforge.opencamera/net.sourceforge.opencame ptr=0000007F174257C0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/opencamera/hilog.txt:31994` — BBQ.update: sessionId=389 → OHNativeWindow=0000007F180E6DD0 (1200x1920 fmt=4)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/opencamera/hilog.txt:32313` — getOhNativeWindow: unknown sessionId=389
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/opencamera/hilog.txt:32315` — BBQ.update: sessionId=389 → OHNativeWindow=0000007F180E6B50 (1200x1920 fmt=-3)

### ppsspp

PID [11237]; signed **desktop** at `2026-10-01T06:39:59+0800`; hilog SHA `b21a28512e7e20ea4c32e832c95a0f1377122781763f730bff839b998429e03f`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/ppsspp/hilog.txt:33763` — createSession: bundle=org.ppsspp.ppsspp ability=PpssppActivity name=org.ppsspp.ppsspp/org.ppsspp.ppsspp.PpssppActivity, androidType=2 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f24477e20 token=0000007F24477E20
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/ppsspp/hilog.txt:33828` — createSession: success, sessionId=417, surfaceNodeId=48262547505153
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/ppsspp/hilog.txt:33829` — [IPC] ENTER oh_wm_set_last_session_local session=417
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/ppsspp/hilog.txt:34102` — BBQ.create name=VRI[PpssppActivity] ptr=0000007F22CF09D0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/ppsspp/hilog.txt:34106` — getOhNativeWindow: unknown sessionId=417
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/ppsspp/hilog.txt:34108` — BBQ.update: sessionId=417 → OHNativeWindow=0000007F24092A10 (1283x2064 fmt=-3)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/ppsspp/hilog.txt:34109` — BBQ.getSurface: returning Surface with mNativeObject=0000007F24092A10 (sessionId=417)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/ppsspp/hilog.txt:34452` — getOhNativeWindow: unknown sessionId=417
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/ppsspp/hilog.txt:34454` — BBQ.update: sessionId=417 → OHNativeWindow=0000007F24092A10 (1283x2064 fmt=-3)

### wikipedia

PID [18065]; signed **white** at `2026-10-01T06:39:59+0800`; hilog SHA `e876776e613f61453b8c8e3efb3f762a0979f8338162a96f5820e1cf19bfa5a3`.

- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/wikipedia/hilog.txt:56607` — createSession: bundle=org.wikipedia ability=InitialOnboardingActivity name=org.wikipedia/org.wikipedia.onboarding.InitialOnboardingActivity, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f230c8910 token=0000007F230C8910
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/wikipedia/hilog.txt:56673` — createSession: success, sessionId=375, surfaceNodeId=77588584202241
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/wikipedia/hilog.txt:56674` — [IPC] ENTER oh_wm_set_last_session_local session=375
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/wikipedia/hilog.txt:58569` — createSession: bundle=org.wikipedia ability=InitialOnboardingActivity name=org.wikipedia/org.wikipedia.DefaultIcon, androidType=1 -> ohType=1001, display=0, size=1200x1920, ohTokenAddr=0x7f24478140 token=0000007F24478140
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/wikipedia/hilog.txt:58631` — createSession: success, sessionId=376, surfaceNodeId=77588584202244
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/wikipedia/hilog.txt:58632` — [IPC] ENTER oh_wm_set_last_session_local session=376
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/wikipedia/hilog.txt:65612` — BBQ.create name=VRI[InitialOnboardingActivity] ptr=0000007F1A82F4E0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/wikipedia/hilog.txt:65616` — getOhNativeWindow: unknown sessionId=375
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/wikipedia/hilog.txt:65617` — BBQ.update: getOhNativeWindow(sessionId=375) returned null
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/wikipedia/hilog.txt:65619` — getOhNativeWindow: unknown sessionId=375
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/wikipedia/hilog.txt:65620` — BBQ.getSurface: ohNativeWindow null (sessionId=375 not attached or BBQ.update not yet called) — returning empty Surface so ViewRoot.mSurface.transferFrom doesn't NPE
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/wikipedia/hilog.txt:65883` — BBQ.create name=VRI[DefaultIcon] ptr=0000007F1A8338D0
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/wikipedia/hilog.txt:65885` — getOhNativeWindow: unknown sessionId=376
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/wikipedia/hilog.txt:65888` — BBQ.update: sessionId=376 → OHNativeWindow=0000007F23C91DD0 (1200x1920 fmt=-1)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/wikipedia/hilog.txt:65892` — BBQ.getSurface: returning Surface with mNativeObject=0000007F23C91DD0 (sessionId=376)
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/wikipedia/hilog.txt:70986` — getOhNativeWindow: unknown sessionId=376
- `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/61b0657200000000000000000324012c/wikipedia/hilog.txt:70988` — BBQ.update: sessionId=376 → OHNativeWindow=0000007F23C91DD0 (1200x1920 fmt=-1)

## Replay

```sh
python3 benchmark/2026-10-01-last-session-scan/scan.py collect > /tmp/last-session-intake.json
python3 benchmark/2026-10-01-last-session-scan/scan.py report > /tmp/last-session-results.json
python3 benchmark/2026-10-01-last-session-scan/test_scan.py
```

See `results.json` for every queue/session/event and evidence pin, `authority.json` for Activity-level sign-offs, and `validation.json` plus `landing-paths.txt` for scoped delivery. No runtime change, board command or frozen score edit.
