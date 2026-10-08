# U14 first-fatal clusters (cc-t3) — 40 non-lit keys, by effective-deployed artifact

#90, offline, no board. Per-key first-fatal from the **actual U14 window1–6 candidate-runner hilogs** (non-smoke:
`movers-/lit-regression-/lottery-/unlit-<key>` → `<key>/hilog.txt`), NOT recovery-smoke and NOT a U13 comparison.
Signature = `cluster_first_cause.cluster_key(compare.first_fatal(run))`; SIGSEGV normalised by the fault-frame library.
Clustered by the **effective deployed artifact** (`westlake-harness-bms/benchmark/2026-10-03-u14-effective-rebind/
common-diagnostic/composition.json`), not the stale u13-cluster candidate SHA (DIGEST). Repro: `python3 collect_u14.py`
→ `clusters.json`.

Population: the **40 non-lit keys** of the U14 166-key reference (`inputs/reference.json`, 126 lit + 4 gains + fd-seal
refresh = lit). **11 have an actual U14 non-smoke candidate run; 29 do not** (no U14 observation — listed separately with
their last-observation path, not inferred).

## Clusters (observed in U14), ranked by keys blocked
| # | cluster | keys | representative stack / exception | effective deployed artifact (U14 composition) | in-flight fix | predicted first-fatal move |
|---|---|---|---|---|---|---|
| 1 | **Flutter raster SIGSEGV (libflutter.so)** | 3: fd-fluffychat, fd-kitchenowl, localsend | `#01 pc …4c367c/…4b655c libflutter.so` (SIGSEGV in Flutter's own raster; Flutter's libandroid/ANativeWindow path) | westlake_flutter `libandroid.so` = **fff9be31** (the Flutter interposer, ALREADY deployed); `libwestlake_native_abi.so` d2053066 | Flutter libandroid interposer `fff9be31` — **already deployed yet these keys still crash in libflutter** | **0 with current** — fff9be31 is insufficient for them; needs re-eval / a newer Flutter fix (U16 pending?). **搁置** pending a fix that actually clears libflutter |
| 2 | **no-observed-termination** | 2: cv2-org-andresoviedo-dddmodel2, vlc | alive, no captured terminal (white/black window, process stays up) | runtime `18763dd4`/`ac59dec0`; bridge `84695d62`/`7daa5435` | none specific (bridge M5/M6 is for other walls) | **0** — no crash to move; needs a rendering/behavior fix, not a first-fatal clear. **搁置** |
| 3 | **process-disappeared (cause unknown)** | 2: mcdonalds, toutiao | process vanished without a captured fault/exception | mcdonalds: Realm family (librealmc); toutiao: — | mcdonalds likely the Realm **sysconf** crash (no backtrace captured); toutiao unknown | mcdonalds: contingent on **sysconf** (user decision); toutiao **搁置** (no cause) |
| 4 | **SIGSEGV libmozglue.so (mozjemalloc sysconf)** | 1: fd-fennec_fdroid | `#00 …77d44 libmozglue.so(6a348a8e)` — MOZ_CRASH, page size not pow2 (`sysconf(0x27)=1000`) | native_abi `f8619ad5` (lets it load past `__gnu_strerror_r`); libbionic_compat `b8a87f6f`/`015aa3a6` (no sysconf) | **sysconf** translation (U17, user-deferred, frozen ns-order) | **+1 with sysconf** (user decision) |
| 5 | **SIGSEGV librealm-jni.so (Realm sysconf)** | 1: fd-im-vector-app | `#00 …7738e0 librealm-jni.so(ea0a5d90)` — SlabAlloc m_translations NULL (sysconf page size) | native_abi `f8619ad5` (`_ctype_` already cleared the bind wall) | **sysconf** translation (U17, user-deferred) | **+1 with sysconf** (user decision) |
| 6 | **SIGSEGV libnativewindow.z.so** | 1: fd-libre | `#0x pc … libnativewindow.z.so` (native-window path; distinct from Flutter) | runtime `18763dd4`; libnativewindow (deployed) | none owned yet | **0** — no owned fix. **搁置** (investigate the libnativewindow frame) |
| 7 | **java-cause: `IllegalStateException: Surface was not locked`** | 1: fd-plus | `main_threw` → `Surface.unlockSwCanvasAndPost(Surface.java:507)` | runtime `18763dd4`/`ac59dec0` | **fd-plus lockCanvas `35c36d00`** (U17, built; the two Surface JNI natives) | **+1** (clears the lockCanvas fatal) |

**Observed total 11.** Buildable/decided in-flight moves: **fd-plus +1** (lockCanvas 35c36d00, ready); **+2 or +3 gated on
the user's sysconf decision** (fennec, im-vector, and mcdonalds if its disappearance is the Realm sysconf). Flutter (3),
no-termination (2), fd-libre (1), toutiao (1) have **no current moving fix → 搁置**.

## No U14 observation (29 keys) — not inferred; last-observation source only
These non-lit keys have no U14 window1–6 non-smoke candidate run (not re-run in U14, or ran only recovery-smoke). Their
last observation is the U14 reference's `t20` (mostly the `2026-10-02-u10-1-t8-rerun` baseline — "window5-gains(no_change)")
— see `clusters.json → no_u14_observation` for each key's exact path. **No first-fatal is assigned to them here.**
Keys: burgerking, cv2-ca-vaults-randomlydie, cv2-com-bytehamster-flowitgame, cv2-com-chessclock-android,
cv2-com-degeder-yam, cv2-com-frequent-habits, cv2-com-paultirk-yatoo, cv2-com-stoutner-privacybrowser-standard,
cv2-dev-obfusk-jiten-webview, cv2-org-linaro-glmark2, cv2-timur-webrtc-check, fd-AppManager, fd-api, fd-app,
fd-breezyweather, fd-immich, fd-meet, fd-mobile, fd-musicplayer, fd-saber, fd-shatteredpixeldungeon, fd-tutanota,
fd-wifianalyzer, firefox, mindustry, ppsspp, subwaysurfers, termux, x.

## Notes
- `fff9be31` (Flutter libandroid) is deployed in U14 yet fluffychat/kitchenowl/localsend still SIGSEGV in libflutter —
  the u13-cluster "C1 fff9be31 moves 4 (high)" prediction did NOT hold in U14; the Flutter wall needs re-eval (do not
  count it as moving).
- Judge the effective artifact by `composition.json`, not the candidate SHA in an old cluster table (e.g. native_abi is
  the deployed `f8619ad5` with `_ctype_`, not `7605812c`).
