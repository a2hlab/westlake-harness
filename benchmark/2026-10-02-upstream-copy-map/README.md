# What to copy from upstream (A2OH/westlake-harness origin/master, framework 68) — overlap with our 166 signed keys

Offline. Upstream reports **154/201 draw** (`benchmark/loop-outcomes.json`, after = draws: 92 drew first time + 62
after fixes) plus **82/100** (`benchmark/2026-09-28-batch16-20-blind/`) and 2/29 top apps. A "draw" means the app's
own UI at 30 s, splash included, which is close to our t20 "lit". `build_map.py` joins those outcomes and the
102-row `blockers-ledger.json` with our U9 sign-off by **package**; nothing is copied by hand.

## What was wrong first

- **"The fixed_in commits are not public, so their fixes cannot be copied" is not true for us.** The commits are
  absent from public A2OH/westlake (and from the local clone `~/orca/westlake`). But **26 of the 28** are in our own
  `vm-copies/westlake-current`, the a2hlab/westlake remote, on remote-tracking `origin/main` (297a723, 09-26) and
  `origin/corpus2-fixes` (2c46770, 09-30, which also carries the framework-68 shim b24a118 + 432c000). Subjects match
  the ledger exactly, for example:
  - 03678da "Build Android native code with zero-initialized locals, as AOSP does";
  - 1c883ad `WlSettingsProvider` and service answers;
  - fe9c40a EGL14/EGL15/EGLExt port.

  Missing locally: `886b89b` (AlarmManager null PendingIntent) and `ef348a1` (a manifest commit). Full list:
  `fixed-in-availability.csv`. Outer loop: the "422" check was against the wrong repo.
- **Their 154/201 is mostly not our apps.** Only **51 of our 166 keys** match an upstream app by package (our cv2 corpus
  is a different 100). Same package is not always the same APK: 21 confirmed same sha256, **3 differ** (fd-stk, noice, x),
  27 unknown (upstream did not record a sha).
- **Their ledger row is often not our wall for the same app.** For 4 of the 7 walls below we die earlier than the row
  they fixed. Their row then predicts our *next* wall, not this one.

## Overlap (51 matched keys, `overlap.csv`)

| ours (U9) \ theirs (after) | draws | blocked |
|---|---|---|
| lit | 25 | 3 (fd-libretube, fd-stk, opencamera; ours ahead) |
| not lit | **13** | 10 |

**They draw, we are not lit (13)**, with our first fatal (U9 hilog / first-wall tables) against their row:

| our key | ours | theirs (ledger / fixed_in) | same wall? |
|---|---|---|---|
| fd-AppManager, fd-noice, noice, fd-uhabits, termux | white window (no fatal) | no row (termux: own-service bind 8357a07, already in ours via B8-AMB) | no: our N11 double-copy architecture |
| fd-mobile (jellyfin) | black window | Settings.Secure.ANDROID_ID null (1c883ad) | partly: same null in ours (settings authority not connected), but its WebView UI is also unavailable |
| fd-wifianalyzer | NPE in CountryPreference: `wb0.H` = `toUpperCase(Locale)` → null | Locale.getDisplayName NPE, libicu_jni without zero-initialized locals (03678da) | **yes** (dex-verified: libicu_jni path) |
| fd-breezyweather | NPE in `pa0.G` = `Locale.Builder…getDisplayCountry()` → null | R8 null check after getApplicationLocales (their env) | **yes in our env**: same ICU wall as wifianalyzer |
| fd-fluffychat, localsend | SIGABRT at load / Flutter preload libandroid → libsurface.z.so | raster thread calls address 0 (open); Dart cacerts path (576fa43) | no: we die earlier |
| fd-im-vector-app | realm librealm-jni dlopen_ns failed | EGL14._nativeClassInit (fe9c40a), AlarmManager.cancel(null) (886b89b) | no: earlier; theirs are our next walls |
| fd-musicplayer | Bitmap without ColorSpace (libhwui) | Media3 SessionToken via queryIntentServices (1c883ad), AudioEffect JNI (e2524b1) | no: earlier |
| cv2-com-lcdcode-moodcairns | KeyStoreException: master key exists but unusable | no row (draws) | unknown |

## Walls they solved that block us, ranked by our keys blocked (`walls.csv`)

1. **White/black window, 17 keys** (6 drawn upstream). This is our own N11 architecture, not a ledger fix; nothing
   to cherry-pick. Keep N11h.
2. **Flutter load, 6 keys** (fluffychat, immich, kitchenowl, libre, saber, localsend; 2 drawn upstream). Copy now:
   576fa43 (CA store in the app namespace). The load and raster stage is the framework-68 shim (b24a118 + 432c000,
   local on `corpus2-fixes`); it needs porting, not a cherry-pick.
3. **ICU null from libicu_jni, 2 keys** (wifianalyzer, breezyweather): **cheapest and same wall.** 03678da adds
   zero-initialized locals (`-ftrivial-auto-var-init=zero`, the AOSP default) to their native build. Check our
   deployed libicu_jni's build flags and rebuild it with that flag.
4. **Settings provider not connected, 1 key named (jellyfin)** but generic: 161 of 165 U9 hilogs show
   `OH_CPBridge: query: not connected, authority=settings`, including all 114 lit keys. Any Settings key outside our
   primed cache reads null (ANDROID_ID, …). Copy 1c883ad `WlSettingsProvider` (JAR layer).
5. **Keystore, 1 key**: no ledger commit; look in westlake-current's keystore code.
6. **App native lib namespace load, 1 key** (element): our fix first. Then copy fe9c40a (EGL14/EGL15/EGLExt JNI on
   OH EGL). The AlarmManager null guard (886b89b) is not local and is trivial to write.
7. **Bitmap ColorSpace, 1 key** (musicplayer): blocked on a reproducible libhwui (DIGEST). Next walls: 1c883ad
   queryIntentServices, e2524b1 libaudioeffect_jni.

Also copyable for walls outside the 13:
- **OpenSL ES**: 0b5c9af "Translate Android's OpenSL ES ABI onto OH's" + 1e98162 + c7d2992 (mindustry's row:
  OH SLuint32 is 64-bit). This is our U10.1 OpenSLES FEATURE_UNSUPPORTED wall.
- **media natives**: 5ae6b75, android.media natives never registered (1088 lines); relevant to our media_jni gap.

## Files

- `build_map.py`: the join, reproducible from `git show origin/master:…` and our signed files. It writes
  `overlap.csv` (one row per our key, with the upstream match, first/after, same_apk, our first fatal and their
  ledger rows / fixed_in) and `match.json` (the joined records).
- `walls.csv`: the 7 walls with our blocked keys, the upstream draws among them, their row, the same-wall
  judgment with evidence, the copy route and the local source commit/path.
- `fixed-in-availability.csv`: every ledger `fixed_in` commit, whether it exists in `~/orca/westlake` and in
  `vm-copies/westlake-current`, the refs that contain it, and its subject.

Upstream ref read: `origin/master` f673d1f2f1 (PR #21 merge), 32 commits ahead of our master.
