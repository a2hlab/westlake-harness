# U12 stage A: predicted vs actual first-fatal moves — 10/22 predicted moves happened, plus 2 unpredicted; the JAR fixes hit 6/6, the SIGABRT and disappeared groups mostly missed. One JAR fix (GcmDefaultNonce) is broken on Android.

#90, offline. Nothing was deployed to a board. This is the evidence table for U12 promotion and the frozen register.

**Scope.** All 51 keys of `2026-10-02-u12-prediction-table/u12-predictions.csv`, the U9 non-lit keys that stage A
re-measured.

**Sides compared.**
- U12 side: every U12 run of each key in windows 1–4. 51/51 keys ran, one run each.
- Each run's board fingerprint shows runtime jar `0482c9b1` (U12 r2).
- U10.1T8 side: the stage-A window-5 first fatal of the same key (`2026-10-02-candidate-first-fatal-clusters`).

**Two signatures per run** (`compare.py`). Both are normalised: pids, addresses and numbers are replaced by `#`.
- **terminal**: `first_fatal.py` → `cluster_first_cause.cluster_key()`.
- **wall**: the earliest linker / ULE / abort / missing-class / missing-method line of the app process before the
  terminal. Benign-registry lines and the `[COROUTINE-FIX]` probe are skipped.
- The wall signature is needed because some terminals are only consequences, and they keep their signature while the
  cause underneath moves:
  - mcdonalds' DI NPE: the terminal is unchanged, but the wall moved from libz to `_ctype_`;
  - a bare SIGABRT;
  - "process disappeared".
- A key **moved** if either signature differs in a U12 run.

## Score (`score.json`)

| | keys |
|---|---|
| predicted to move **and moved** | **10** |
| predicted, **did not move** | 12 |
| **not predicted, moved** | 3. Two are U12's doing: fd-im-vector-app and mcdonalds, both the private-libz alias. One is not: toutiao, run variance. |
| not predicted, did not move | 26 |
| not run | 0 |

- **Precision** of "predicted mover": 10/22 = **45 %**.
- **Recall** of the moves U12 actually caused: 10/12 = **83 %** (toutiao excluded, see notes).

**By predictor (owner column of the prediction table).**

| predictor | moved / predicted | keys (* = moved) |
|---|---|---|
| java_fix (U12 r2 JAR: provider authorities, telephony, Predicate, GCM nonce) | **6/6** | notepad*, fd-client*, clipboardeditor*, x*, packlist*, moodcairns* |
| icu (zero-init UErrorCode) | **2/2** | breezyweather*, wifianalyzer* |
| disappeared (private zlib alias etc.) | 2/6 | burgerking*, libresudoku*, fennec, firefox, ppsspp, vlc |
| sigabrt | **0/8** | glmark2, fluffychat, immich, kitchenowl, libre, saber, localsend, subwaysurfers |
| mediandk | 0/1 | subwaysurfers |
| n11h_family | 1/1 | x* |

**How to read the misses.**
- **sigabrt, 0/8.** The abort reason of these 8 (mostly Flutter) apps is not in hilog: no faultlog was captured and no
  FATAL line was logged. Both signatures (signal 6 on the app's main thread, same earliest wall) are unchanged. Every
  observable signal says "not moved". What the abort *was* is unknown, so the miss cannot be proven final.
- **disappeared, 2/6.** fennec and firefox keep `libmozglue.so: Directory separator should not appear in library name`.
  ppsspp and vlc keep their `F02-A12-UNSUPPORTED-SYMBOL` dlopen. Byte-identical walls: these fixes did not reach them.

## Screens (authority order: outer sign-off > `pair_sheet.py` auto > cc-t3 reading)

**Signed so far:** windows 1–3 (`window{1,2,3}-signoff`) and fd-client in window 4 (ACK 00:58:37: new lit).

**Window 4 has no sign-off file yet.** For it this round produced the U10.1T8-paired sheets:
- `pair-w4/pair-sheet-suspects.jpeg`: 43 pairs, 35 auto-same, 8 suspects;
- `pair-w3/pair-sheet-suspects.jpeg`.

From the window-4 suspect tiles, cc-t3's **unsigned** reading is that the app's own UI is on screen for:
- **libresudoku** (start screen);
- **notepad** (task list);
- **packlist** (empty trip list; the class name is the title, the labelRes wall);
- **clipboardeditor** (editor panel);
- uhabits (Loop welcome). uhabits is a lottery key and did not move.

If the outer confirms, U12's new lit keys are **fd-client + up to 4**. x is white (no window). toutiao shows the desktop
(window 3).

## Finding that matters for freezing: `adapter.core.GcmDefaultNonce` (U12 R3) never initialises its delegate on Android

moodcairns did move, but **into our own provider**:
`IllegalStateException: GCM cipher needs to be initialised` at `adapter.core.GcmDefaultNonce$Spi.engineDoFinal`
(window 4, 61b).

**Cause** (AOSP android-14.0.0_r1 `libcore/ojluni/.../javax/crypto/Cipher.java`, hw248):
- `GcmDefaultNonce.newDelegate()` wraps Bouncy Castle's `CipherSpi` in `new Cipher(spi, provider, transformation) {}`.
- On Android that constructor installs `SpiAndProviderUpdater(provider, cipherSpi)`.
- `Cipher.init()` → `chooseProvider()` → `updateAndGetSpiAndProvider()` **returns the specified spi without calling
  `engineInit`** (`if (specifiedSpi != null) return new CipherSpiAndProvider(specifiedSpi, provider);`).
- So the delegate is never initialised, and every `doFinal` hits Bouncy Castle's "needs to be initialised".
- The U12 r2 host test used OpenJDK's `Cipher`, which does call `engineInit`. That is why it passed.

**Reach.**
- The provider is installed at position 1 in every process: 173/174 U12 runs log `[B8-GCM] … installed`.
- The in-process `[WL-KS-PROBE]` AES/GCM self-test fails with the same "GCM cipher needs to be initialised" in 154 of
  174 U12 runs (0 of 133 U10.1T8 runs): every process's default AES/GCM is broken.
- Only moodcairns reaches it in app code before t20 (`GCM … initialised` outside the probe: moodcairns 5 lines, nobody
  else). That is why the window sign-offs show no regression.
- Any app that uses JCE AES/GCM later (e.g. Tink, EncryptedSharedPreferences, app-level encryption) now fails where
  U10.1T8 used Bouncy Castle with a 16-byte nonce.

**Consequences for the U12 freeze.**
- **Do not freeze GcmDefaultNonce** (U12 R3). Its "pass" is not real.
- The fix belongs to its own version: drive the BC `CipherSpi` directly, calling its protected `engineInit` /
  `engineUpdate` / `engineDoFinal` / `engineUpdateAAD` / `engineGetIV` / `engineGetParameters` /
  `engineGetOutputSize` by reflection, instead of wrapping it in a `Cipher`.
- That fix needs an **on-Android** check: the `[WL-KS-PROBE]` self-test must pass, and moodcairns must move on.
- Until fixed, the honest state is: moodcairns' AEADBadTag has become our own IllegalStateException, and the GCM
  default of every process is broken.
- The other five java_fix keys moved through code that does not touch this provider.

## Per key (`table.md` / `table.csv`; full per-run data `per-key.json`; U12 first-fatal results `u12-first-fatal.json`, `u12-clusters.json`)

| key | predicted (by) | actual | U10.1T8 first fatal → U12 first fatal | screen: outer / pair-auto / cc-t3 read (unsigned) | notes |
|---|---|---|---|---|---|
| burgerking | yes (disappeared) | **moved** terminal+wall | process-disappeared: process disappeared without cause → signal: DFX_SignalHandler :: signo(11), si_code(1), pid(6791), tid(6988). | - / w4:same | moved: libNitroMmkv dlopen (libz) gone; now SIGSEGV in librsa_bridge (Go cgo x_cgo_sigaction) on pool-4-thread-1 |
| cv2-com-kaajjo-libresudoku | yes (disappeared) | **moved** terminal | process-disappeared: process disappeared without cause → no-observed-termination:  | - / w4:different / own UI (LibreSudoku start screen: board + 开始 + settings) | moved: no termination, alive at t20 |
| cv2-com-lcdcode-moodcairns | yes (java_fix) | **moved** terminal | java-cause: javax.crypto.AEADBadTagException: mac check in GCM failed → java-cause: java.lang.IllegalStateException: GCM cipher needs to be initialised | - / w4:same | moved INTO OUR FIX: IllegalStateException "GCM cipher needs to be initialised" at adapter.core.GcmDefaultNonce$Spi.engineDoFinal -- see README (GcmDefaultNonce defect) |
| cv2-com-nbossard-packlist | yes (java_fix) | **moved** terminal+wall | java-cause: java.lang.ClassNotFoundException: com.android.internal.util.Predicate → no-observed-termination:  | - / w4:different / own UI (empty trip list, title = class name: labelRes wall) |  |
| cv2-com-nononsenseapps-notepad | yes (java_fix) | **moved** terminal | java-cause: java.lang.NullPointerException: Attempt to invoke interface method 'boolean android.database.Cursor.moveToFirs → no-observed-termination:  | - / w4:different / own UI (task list "欢迎! 打开这个即可开始") |  |
| cv2-com-trianguloy-clipboardeditor | yes (java_fix) | **moved** terminal | java-cause: java.lang.NullPointerException: Attempt to invoke virtual method 'java.lang.String android.telephony.Telephony → no-observed-termination:  | - / w4:different / own UI (clipboard editor panel, top-left, on white) |  |
| fd-breezyweather | yes (icu) | **moved** terminal | java-cause: java.lang.NullPointerException: Attempt to invoke virtual method 'java.lang.Class java.lang.Object.getClass()' → unknown:  | - / w3:same | moved to next wall: lateinit property weatherView has not been initialized (app-level, after the ICU fix) |
| fd-client | yes (java_fix) | **moved** terminal | java-cause: java.lang.NullPointerException: Attempt to invoke interface method 'boolean android.database.Cursor.moveToFirs → no-observed-termination:  | w4:lit (new): own onboarding page; ACK 2026-10-03T00:58:37 (U10.1T8: dead) / w4:different |  |
| fd-wifianalyzer | yes (icu) | **moved** terminal+wall | java-cause: java.lang.NullPointerException: Attempt to invoke virtual method 'java.lang.Class java.lang.Object.getClass()' → java-cause: java.lang.NoSuchMethodError: No virtual method isScanThrottleEnabled()Z in class Landroid/net/wifi/WifiManager (wall: [CHILD_CK] J_invokeStaticMain_main_threw: java.lang.NoSuchMethodError: No virtual method isScanThrottleEnabled) | - / w4:same | moved to next wall: NoSuchMethodError WifiManager.isScanThrottleEnabled() |
| x | yes (java_fix;n11h_family) | **moved** terminal+wall | java-cause: java.lang.IllegalStateException: The application object graph is not defined. Is your Application class callin → java-cause: java.lang.NullPointerException: Attempt to invoke interface method 'void com.android.internal.telephony.ITelep (wall: F02-A12-UNSUPPORTED-SYMBOL: dlopen_ns failed for /data/app/el1/bundle/public/com.twitter.android/android/lib/a) | - / w4:no-window / white (no window) | moved to next wall: NPE ITelephonyRegistry.listenWithEventList (fixed in U13 JAR v2 506abe23) |
| cv2-org-linaro-glmark2 | yes (sigabrt) | **same**  | signal: DFX_SignalHandler :: signo(6), si_code(-6), pid(3139), tid(3163). | - / w4:same |  |
| fd-fennec_fdroid | yes (disappeared) | **same**  | process-disappeared: process disappeared without cause | - / w3:same |  |
| fd-fluffychat | yes (sigabrt) | **same**  | signal: DFX_SignalHandler :: signo(6), si_code(-6), pid(26309), tid(26342). | - / w3:same |  |
| fd-immich | yes (sigabrt) | **same**  | signal: DFX_SignalHandler :: signo(6), si_code(-6), pid(27586), tid(27613). | - / w4:same |  |
| fd-kitchenowl | yes (sigabrt) | **same**  | signal: DFX_SignalHandler :: signo(6), si_code(-6), pid(27065), tid(27089). | - / w4:same |  |
| fd-libre | yes (sigabrt) | **same**  | signal: DFX_SignalHandler :: signo(6), si_code(-6), pid(28881), tid(28904). | - / w4:same |  |
| fd-saber | yes (sigabrt) | **same**  | signal: DFX_SignalHandler :: signo(6), si_code(-6), pid(20351), tid(20374). | w3:same screen as U10.1T8; w3:same (dead) / w3:same |  |
| firefox | yes (disappeared) | **same**  | process-disappeared: process disappeared without cause | - / w4:same |  |
| localsend | yes (sigabrt) | **same**  | signal: DFX_SignalHandler :: signo(6), si_code(-6), pid(5521), tid(5548). | - / w4:same |  |
| ppsspp | yes (disappeared) | **same**  | process-disappeared: process disappeared without cause | - / w4:same |  |
| subwaysurfers | yes (mediandk;sigabrt) | **same**  | signal: DFX_SignalHandler :: signo(6), si_code(-6), pid(3245), tid(3271). | - / w4:same |  |
| vlc | yes (disappeared) | **same**  | process-disappeared: process disappeared without cause | - / w4:same |  |
| fd-im-vector-app | no (java_fix) | **moved** terminal+wall | java-cause: java.lang.UnsatisfiedLinkError: F02-A12-UNCLASSIFIED: dlopen_ns failed for /data/app/el2/100/base/im.vector.ap → java-cause: java.lang.UnsatisfiedLinkError: F02-A12-UNSUPPORTED-SYMBOL: dlopen_ns failed for /data/app/el2/100/base/im.vec (wall: Caused by: java.lang.UnsatisfiedLinkError: F02-A12-UNSUPPORTED-SYMBOL: dlopen_ns failed for /data/app/el2/100/) | - / w4:same | unpredicted, U12-attributable: U12 private libz alias fixed "libz.so not found" for librealm-jni; next wall UNSUPPORTED-SYMBOL in the same dlopen (same mechanism as mcdonalds) |
| mcdonalds | no (java_fix) | **moved** +wall | java-cause: java.lang.NullPointerException: Attempt to invoke interface method 'com.mcdonalds.mcdcoreapp.helper.interfaces → java-cause: java.lang.NullPointerException: Attempt to invoke interface method 'com.mcdonalds.mcdcoreapp.helper.interfaces (wall: Caused by: java.lang.RuntimeException: Unable to get provider androidx.startup.InitializationProvider: android) | - / w4:same | unpredicted, U12-attributable: terminal unchanged (DI NPE = consequence); the wall under it moved libz -> _ctype_ UNSUPPORTED-SYMBOL (outer: libz->_ctype_) |
| toutiao | no (-) | **moved** terminal+wall | no-observed-termination:  → process-disappeared: process disappeared without cause (wall: [B8-UEH] background thread 'CronetInit' uncaught, thread ended (process kept alive): java.lang.NoSuchMethodErr) | - / w3:different / desktop (process gone); U10.1T8 reference: white | NOT attributable to U12: new wall NoSuchMethodError NetworkInfo.getSubtype in CronetInit; NetworkInfo is identical in stubs 2f365a75 and 615b8bbe (no getSubtype in either) and no U12 change touches it; the U10.1T8 reference run is from the toutiao-gain shard -> run variance |
| cv2-ca-vaults-randomlydie | no (n11h_family) | **same**  | no-observed-termination:  | - / w4:same |  |
| cv2-com-bytehamster-flowitgame | no (n11h_family) | **same**  | no-observed-termination:  | - / w4:same |  |
| cv2-com-chessclock-android | no (java_fix;mediandk) | **same**  | java-cause: java.lang.UnsatisfiedLinkError: system library is absent from the adapter manifest | - / w4:same |  |
| cv2-com-degeder-yam | no (n11h_family) | **same**  | no-observed-termination:  | - / w4:same |  |
| cv2-com-emmanuelmess-itsdicey | no (-) | **same**  | no-observed-termination:  | - / w4:same |  |
| cv2-com-frequent-habits | no (-) | **same**  | no-observed-termination:  | - / w4:no-window |  |
| cv2-com-paultirk-yatoo | no (n11h_family) | **same**  | no-observed-termination:  | - / w4:same |  |
| cv2-com-stoutner-privacybrowser-standard | no (java_fix) | **same**  | java-cause: java.lang.UnsupportedOperationException: This method is not supported by the current version of the framework  | - / w4:same |  |
| cv2-dev-obfusk-jiten-webview | no (n11h_family) | **same**  | no-observed-termination:  | - / w4:same |  |
| cv2-org-andresoviedo-dddmodel2 | no (n11h_family) | **same**  | no-observed-termination:  | - / w4:same |  |
| cv2-org-secuso-privacyfriendlyyahtzeedicer | no (-) | **same**  | no-observed-termination:  | w3:same screen as U10.1T8 / w3:same |  |
| cv2-timur-webrtc-check | no (-) | **same**  | no-observed-termination:  | - / w4:same |  |
| fd-AppManager | no (n11h_family) | **same**  | no-observed-termination:  | w3:same screen as U10.1T8; w3:same (white) / w3:same |  |
| fd-api | no (java_fix) | **same**  | java-cause: java.lang.IllegalStateException: You need to use a Theme.AppCompat theme (or descendant) with this activity. | - / w3:same |  |
| fd-app | no (n11h_family) | **same**  | no-observed-termination:  | w3:no t20 (phase blocked) -> unknown (unlit in U10.1T8); w3:no t20 / w3:same |  |
| fd-meet | no (-) | **same**  | java-cause: [CHILD_CK] J_invokeStaticMain_main_threw: com.facebook.soloader.B: java.lang.UnsatisfiedLinkError: F02-A12-UNS | - / w4:same |  |
| fd-mobile | no (-) | **same**  | no-observed-termination:  | w3:no t20 (phase blocked) -> unknown (unlit in U10.1T8); w3:no t20 / w3:same |  |
| fd-musicplayer | no (-) | **same**  | java-cause: java.lang.IllegalArgumentException: can't create bitmap without a color space | - / w4:same |  |
| fd-noice | no (n11h_family) | **same**  | no-observed-termination:  | - / w3:no-window |  |
| fd-plus | no (java_fix) | **same**  | java-cause: java.lang.IllegalStateException: Surface was not locked | - / w4:same |  |
| fd-shatteredpixeldungeon | no (n11h_family) | **same**  | no-observed-termination:  | - / w4:same |  |
| fd-tutanota | no (-) | **same**  | no-observed-termination:  | w3:same screen as U10.1T8; w3:same (dead) / w3:same |  |
| fd-uhabits | no (n11h_family) | **same**  | no-observed-termination:  | - / w4:different / own UI (Loop welcome page) -- lottery key, not a U12 move |  |
| mindustry | no (java_fix) | **same**  | java-cause: java.lang.UnsatisfiedLinkError: F02-A12-UNSUPPORTED-SYMBOL: dlopen_ns failed for /data/app/el1/bundle/public/i | - / w4:same |  |
| noice | no (n11h_family) | **same**  | no-observed-termination:  | - / w4:same |  |
| termux | no (n11h_family) | **same**  | no-observed-termination:  | w3:same screen as U10.1T8; w3:same (white) / w3:same |  |

## Rules this round sets

- **Score both signatures.** A first-fatal comparison scores the terminal **and** the earliest wall under it. A terminal
  that is a consequence (DI NPE, bare SIGABRT, "process disappeared") can stay identical while its cause moves
  (mcdonalds).
- **Check where a move landed.** When a predicted move lands inside our own fix (moodcairns → `GcmDefaultNonce$Spi`),
  the fix is defective, not done. Host tests of JCE wrappers must run against Android's `javax.crypto.Cipher`
  semantics. Android does not `engineInit` an explicitly constructed `Cipher(spi, …)`.
- **Attribute every unpredicted move to a change before counting it.** toutiao's new NetworkInfo wall touches nothing
  U12 changed (stubs `NetworkInfo` identical in 2f365a75 and 615b8bbe), so it is variance, not a U12 effect.

## Files

- `compare.py` → `per-key.json`, `score.json`, `u12-first-fatal.json`, `u12-clusters.json`.
- `table.py` → `table.md`, `table.csv`.
- Pair sheets: `pair-w3/`, `pair-w4/` (`pair-sheet.json` + suspect sheet).
- `results.json`.
