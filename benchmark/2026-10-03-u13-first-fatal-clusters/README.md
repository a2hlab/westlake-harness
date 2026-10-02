# U13 first-fatal clusters + U14 coverage: 43 non-lit keys in 18 clusters; 21 keys still unowned; U15 = bionic LIBC export per domain (3), Bitmap null ColorSpace (2), NDK symbol in private domains (2)

#90, offline. Nothing was deployed to a board.

## What the data is (and what was wrong with the ask)

**The ask** was U13 window 1 (5ea/5cd) plus the latest U12 record for 61b. **The data is narrower than that.**
- U13 window 1 is stage A: the 122 lit-protection keys plus the movers. Of the 44 keys that are non-lit in the U13
  reference (`2026-10-03-u13-reference`, 55/55/56 = 166), it ran only **10** (9 + fd-fitness).
- So the population is built per key:
  - **Population (43).** The 44 non-lit reference keys, minus fd-noice and fd-uhabits (window 1: lit 6/6), plus
    fd-fitness (lit reference, dead 0/1 in window 1).
  - **Source.** The key's U13 window-1 run when it exists (**10 keys**, runtime jar bbc3f530). Otherwise its latest U12
    stage-A run (**33 keys**, jar 0482c9b1), on its own board; 61b has no U13 run.
- Every row carries `generation` (u13 / u12). U12 rows say nothing about what U13 changed for them; the U13-owned
  predictions below (C3, C9, C10, noice) are still unmeasured.

**Method** (`collect.py` → `per-run.json`). Same signatures as `2026-10-03-u12-predicted-vs-actual/compare.py`,
imported, not copied:
- **terminal:** `first_fatal.py` + `cluster_first_cause.cluster_key`.
- **wall:** the earliest WALL line of the target pids before the terminal. For `bind_failed` runs it is the innermost
  `Caused by:` under `ensureBindApplication FAILED`.
- **bind:** `bind_status` semantics per run (bound / bind_failed / fatal_before_bind / unbound_at_capture).
- **near-fatal libraries:** `dlopen_failures.scan --near-fatal 3`.
- **Clustering** (`clusters.py` → `clusters.json`, `per-key.csv`):
  - by terminal when the terminal is the fault itself;
  - by wall when the terminal is a consequence (process disappeared, bind_failed, DI NPE, JniAbort SIGABRT, a
    J_invokeStaticMain wrapper).
- Each assignment rests on a verbatim hilog line in `evidence/walls.txt`. Each provider claim rests on
  `evidence/provider-exports.txt` (llvm-nm of the U14 / U13 artifacts, and deployed loader eebd62f2 strings).

## The table (sorted by keys blocked)

| # | cluster | keys | U13-run | bind | owner | predicted first-fatal move |
|---|---|---|---|---|---|---|
| C15 | no termination, alive at t20, white/black, **unowned residual** | 9: randomlydie, flowitgame, yam, yatoo, jiten-webview, webrtc-check (black), fd-app, shatteredpixeldungeon, fd-tutanota | 0 | bound | – | 0 |
| C14 | no termination, alive at t20, owned | 5: fd-AppManager, fd-mobile, dddmodel2, termux, noice | 0 | bound | bridge 7daa5435 M6 / M5 / M5(+U13 M1); JAR 0349eb83+M6; U13 M1 shim | AppManager white goes (med); mobile own dialog (high); dddmodel2 own dialog (med); termux → launcher (not lit); noice moves (U13, med) |
| C1 | Flutter raster SIGSEGV `ANativeWindow_getFormat+60` | 4: localsend, fd-kitchenowl, fd-fluffychat, fd-libre | 4 | bound | **Flutter libandroid fff9be31** | **4 move (high)** |
| C2a | bionic LIBC symbol out of scope, **covered** (native cluster) | 4: firefox, fd-fennec_fdroid (`__gnu_strerror_r`), vlc (`__pthread_cleanup_push`), ppsspp (`android_dlopen_ext`) | 1 | fatal_before_bind / bound | **native_abi 7605812c** | firefox/fennec move (high, replay 0 missing); vlc (med: other libs not replayed); ppsspp (med: next = extinfo calls get ENOTSUP) |
| C12 | single-key fatal walls, unowned | 4: fd-wifianalyzer (`WifiManager.isScanThrottleEnabled` NSME), chessclock (`InvalidDisplayException` at addView), fd-breezyweather (`lateinit weatherView`), burgerking (SIGSEGV pc 0) | 1 | bound | – | 0 |
| C2b | bionic `_ctype_` (Realm), **native domain, unowned** | 2: mcdonalds (librealmc), fd-im-vector-app (librealm-jni) | 0 | **bind_failed** | – | 0 |
| C3 | GetLongField JniAbort | 2: fd-saber, glmark2 | 0 | bound | U13 runtime 18763dd4 | move (U13, high; the 4 C1 keys moved past exactly this); saber then expected at C1 → fff9be31 |
| C4 | NDK API symbol missing in a private domain, unowned | 2: fd-immich (`ATrace_beginSection`, libcronet; bind also fails on VerifyError A2.b), mindustry (`slCreateEngine`, libarc) | 1 | bind_failed / bound | – | 0 (mindustry: only if 341c1260's inherit reaches the native domain, unverified) |
| C5 | `Bitmap.createScaledBitmap` → "can't create bitmap without a color space", unowned | 2: privacybrowser (U13), fd-musicplayer | 1 | bound | – | 0 |
| C2c | bionic `__register_atfork` (Hermes/RN), **normal domain, unowned** | 1: fd-meet (+ x libcrashlytics, caught) | 0 | bound | – | 0 |
| C6 | `libGLESv3.so` ENOENT in app ns | 1: subwaysurfers | 0 | bound | app-ns public libs 341c1260 | move (owner table) |
| C7 | toutiao ICU (public lib + 74/72) | 1: toutiao | 0 | unbound_at_capture | 341c1260 + ICU 9b36b989/4886bc5c | move (owner: lit shell, feed risk) |
| C8 | `android.bluetooth.le.ScanCallback` at bind | 1: fd-plus | 0 | bind_failed | stubs 87cf65cc | move (high) |
| C9 | ITelephonyRegistry NPE | 1: x | 0 | bound | U13 JAR bbc3f530 | move (U13) |
| C10 | AES/GCM R3 | 1: moodcairns | 0 | bound | U13 JAR bbc3f530 | move (U13) |
| C11 | Theme.AppCompat | 1: fd-api | 1 | bound | theme probe (u13-java-walls-2) | probe |
| C13 | RenderThread SIGSEGV lottery (skia `StrikeCache::generateStrike`) | 1: fd-fitness (lit ref.) | 1 | bound | – | lottery, k/n in window 2 |
| C16 | never launched (desktop tile) | 1: frequent-habits | 0 | – | aa start fallback (cx-t0) | not a runtime wall |

**Totals.**

| | keys |
|---|---|
| U14 parts predict a first-fatal move | **11**: C1 4, C2a 4, C6 1, C7 1, C8 1 |
| U14 bridge/JAR change the t20 picture without a fatal | 4 (C14) |
| U13 changes, not yet measured on their board | 5: C3 2, C9 1, C10 1, noice 1 |
| **Unowned** | **21**: C15 9, C12 4, C2b 2, C4 2, C5 2, C2c 1, C13 1 |

## U14 parts with no cluster in this population

| part | why it predicts 0 moves here |
|---|---|
| ICU 9b36b989+4886bc5c | toutiao only |
| 341c1260 | toutiao, subwaysurfers; fd-stk is lit-reference |

Every other U14 part has at least one cluster above.

## U15 candidates: the three largest unowned fatal clusters

Not candidates, and why:
- **C15** (9 keys) is not one mechanism. It is "alive, no fatal line, wrong picture", and first-fatal clustering
  cannot split it; its scan is window-level (scene stack / last frame / createSession), not this one.
- **C12** is four unrelated single-key walls.

### 1. Bionic LIBC export missing from the domain's provider (C2b + C2c): 3 keys (mcdonalds, fd-im-vector-app, fd-meet)

**Mechanism guess.** Realm (`_ctype_`) and Hermes/React Native (`__register_atfork`, then libc++_shared
`android_set_abort_message`) import bionic-only symbols at version `LIBC` (`use_vna_hash=1 van_hash=50d63`).

The only exporter of `_ctype_` is libbionic_compat b8a87f6f:
- it is unversioned;
- it is out of scope for native_private (the gecko replay reproduces the board's first symbol only without compat).

The U14 GLOBAL native_abi 7605812c has `__register_atfork` and `android_set_abort_message`, but no `_ctype_`. And
org.jitsi.meet is not in the 13-package native cluster (deployed loader eebd62f2), so it gets nothing from native_abi.

The fix shape is two halves, one per domain:
- **native:** `_ctype_` added to native_abi as a new source file. Copy b8a87f6f's verified 257-byte table plus pointer
  object verbatim.
- **normal:** a LIBC provider in scope for `__register_atfork`.

**First static scan.** A `reloc_order.py` musl-order replay of every native library of the three APKs (not only the
reported one), against each domain's provider model:
- native: musl + 7605812c;
- normal: musl + whatever is in scope.

It gives the full gap list, the way the Gecko replay turned 1 symbol into 10. Add one more check: does OH musl accept an
unversioned definition for a `use_vna_hash=1` LIBC import? That decides whether compat could ever serve these.

### 2. Bitmap null ColorSpace (C5): 2 keys (privacybrowser, fd-musicplayer)

**The fault.** Both die at `Bitmap.createScaledBitmap` → `createBitmap(Bitmap.java:979)` → `:1203` "can't create
bitmap without a color space", on a source bitmap the app decoded or created.

**Mechanism guess.** AOSP 14 copies `source.getColorSpace()` into the new bitmap. Ours returns null for that source,
because our Bitmap native `nativeComputeColorSpace` has no ColorSpace for the bitmap's config or for the decoded
bitmap's profile.

**First static scan.** A JNI coverage scan (B10) of `android.graphics.Bitmap` natives:
- which library registers `nativeComputeColorSpace` / `nativeGetColorSpace`;
- what they return per config.

Plus the source of the two apps' bitmaps (dexdump the caller frames: `MainWebViewActivity.u`, `df.j.<init>`). This is a
small JAR-or-hwui fix. privacybrowser's U12 webkit wall moved here in U13, so it is next in line.

### 3. NDK API symbol absent in a private domain (C4): 2 keys (fd-immich, mindustry)

**What fails.**
- immich's libcronet needs `ATrace_beginSection`. The Flutter-private libandroid fff9be31 exports no `ATrace_*`.
- mindustry's libarc needs `slCreateEngine` in the native domain.

**Mechanism guess.** These private domains resolve libarc's / libcronet's NEEDED `libandroid.so` / `libOpenSLES.so` to
files that are not the full NDK libraries, and nothing else in scope defines the symbols.

immich also fails bind earlier, on `VerifyError A2.b` (`Unresolved Reference d7.c`), a missing class in the
verifier's view.

**First static scan.** `open_site_scan.py`-style NEEDED resolution per domain:
- for each NEEDED of libcronet / libarc, which file the Flutter / native domain loads;
- `nm` that file for the imported NDK symbols.

For immich, also run `deployed_class_diff` on `d7.c`'s supertype chain.

## Rules this round sets

- **A stage-A window is not a census of the non-lit keys.** Build the cluster population from the reference set and
  label each row with the generation it was measured on. Window 1 measured 10 of 44.
- **"Exported by a deployed library" is not "covered".** For each relocation wall, also check:
  - the domain: deployed loader package list;
  - the provider in that domain's scope;
  - the symbol version.

  U13 compat-ctype exports `_ctype_`, yet both Realm keys stay unowned.

## Files

- `collect.py` → `per-run.json`.
- `clusters.py` → `clusters.json`, `per-key.csv`.
- `evidence/walls.txt`, `evidence/provider-exports.txt`.
- `results.json`.
