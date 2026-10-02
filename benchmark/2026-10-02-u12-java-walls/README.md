# U12 r2: the candidate base's Java-layer first fatals, and the fixes merged into the round's one JAR version

#90, offline, no board. The candidate base is U10.1+T8+U11i, unified since 2026-10-02 17:52. Its window-5
first-fatal clusters are `2026-10-02-candidate-first-fatal-clusters`. This round covers the Java-layer groups:
NPE 4, ISE 3, ULE 3, CNFE 1, UnsupportedOperation 1, AEADBadTag 1.

Per key (`predictions.csv`, line numbers in `evidence/key-lines.txt`): the window-5 first-fatal line, then what
returned null or is missing, then whether upstream has a same-wall fix, then the fix layer.

**Predicted first-fatal moves: 6 of 13**: notepad, fd-client, clipboardeditor, x, packlist, moodcairns.

All six fixes are JAR-layer and are merged into U12 as **U12 r2**:
- runtime `0482c9b1…`, replacing r1's `3bca82c5`;
- stubs `00b30467…`, replacing r1's `3a12918a`.

Neither r1 jar was deployed. The framework jar is unchanged.

## What was wrong first

- **"NPE on a Cursor" read as an app bug was not one.** notepad and Nextcloud query their *own* providers. Our
  bind list publishes those providers under the raw resource id of their `android:authorities="@string/…"`:
  `[B8-PROV-INSTALL] @2131755008 already instantiated` (notepad).
  - The real authority (`…MyContentAuthority`, `org.nextcloud`) then misses and reaches the OH DataShare bridge,
    `query: not connected`, and the query returns null.
  - The bind list comes from the native manifest JSON (`AppSchedulerBridge.buildProvidersFromManifest`), which
    keeps references unresolved.
  - The PackageManager projection (`ManifestComponentProjection`, `Resources.obtainAttributes`) resolves them
    correctly.
  - 8 of the 166 keys declare such authorities.
- **x's "object graph not defined" and clipboardeditor's null TelephonyManager have one cause.**
  `adapter-mainline-stubs` defines its own `android.telephony.TelephonyFrameworkInitializer`, with only
  `registerServiceWrappers` and a no-op `setTelephonyServiceManager`. On the boot class path it shadows
  framework.jar's complete class. Two consequences:
  - `TelephonyManager.getSubscriptionService()` throws `NoSuchMethodError getTelephonyServiceManager`. In x, datadog's
    `getPhoneType()` inside a ContentProvider's `onCreate` fails the whole bind; StartActivity then finds no DI
    graph.
  - Nothing fills `SystemServiceRegistry.SYSTEM_SERVICE_NAMES` for telephony. TelephonyFetcher replaces the
    `phone` fetcher (prev=null) but no class→name entry exists, so `getSystemService(TelephonyManager.class)` is
    null. Linkify uses exactly that (clipboardeditor).
- **moodcairns' AEADBadTag is our cipher default, not a corrupted key.** Without Conscrypt, AES/GCM resolves to
  Bouncy Castle. Its parameterless encrypt generates a 16-byte IV, while Tink writes `iv||ct` and decrypts with 12
  bytes. The board's `[WL-KS-PROBE]` self-test reproduces it: "ivLen=16 (Tink reads 12) … REPRODUCES the on-board
  root".
- **U11i's `com.android.internal.util.Predicate` is in the wrong jar.** It sits in `oh-adapter-runtime.jar`, loaded
  by the runtime PathClassLoader, and app class loaders never see it; packlist still dies with
  ClassNotFoundException. It belongs on the boot class path.
- **The other 7 are not Java-layer walls.** mcdonalds' NPE is the consequence of an earlier `librealmc.so` dlopen
  failure during bind.

## Per key

| key | window-5 first fatal (line) | cause | upstream same wall | layer | U12 r2 fix | moves? |
|---|---|---|---|---|---|---|
| notepad | :37403 NPE `Cursor.moveToFirst()` | own provider published as `@2131755008` | not in upstream corpus | JAR runtime | R1 `ProviderAuthorityRefs` | **yes** (high) |
| fd-client | :19427 NPE `Cursor.moveToFirst()` (MainApp, during bind) | `FileContentProvider` `@0x7f1300a7` (5/7 providers) | nextcloud blocked upstream, cause not identified | JAR runtime | R1 (+ U11j for the lookup made before install) | **yes** (medium-high) |
| clipboardeditor | :31090 NPE `TelephonyManager.getSimCountryIso()` on null | no class→name for TelephonyManager; then `getTelephonyServiceManager` missing | none | JAR runtime + stubs | R2 `TelephonyServiceNames` + S1 | **yes** (medium) |
| x | :31375 ISE object graph | bind failed: `NoSuchMethodError getTelephonyServiceManager` | x blocked upstream, no row | JAR stubs | S1 | **yes** (high; next wall unknown) |
| packlist | :31088 CNFE `com.android.internal.util.Predicate` | interface absent from BCP | none | JAR stubs | S2 `Predicate` | **yes** (high) |
| moodcairns | :43005 AEADBadTag → master key unusable | BC 16-byte default GCM nonce | draws upstream, no row | JAR runtime | R3 `GcmDefaultNonce` | **yes** (medium-high) |
| mcdonalds | :31141 NPE DI | bind failed earlier: `librealmc.so` dlopen_ns | none | native | – | no |
| fd-api | :12992 ISE Theme.AppCompat | alias theme re-resolved to `0x7f120252` (`Theme.BaseActivity.DayNight.NoActionBar`) and still rejected; same on U9; J3 passed it on U3 | none | unknown, needs a board probe of the theme at `setContentView` | – | no |
| fd-plus | :30255 ISE Surface was not locked | `nativeLockCanvas` returns 0 (DIGEST 558) | – | native | – | no |
| chessclock | :43043 ULE "system library is absent from the adapter manifest" (`MediaPlayer.<clinit>`, media_jni) | libmedia_jni not in the native policy | none | native/config | – | no |
| fd-im-vector-app | :25664 ULE `librealm-jni` dlopen_ns | native | element draws upstream after EGL14 / AlarmManager (our next walls) | native | – | no |
| mindustry | :19404 ULE UNSUPPORTED-SYMBOL | bionic-only symbol | OpenSL ES 64-bit (0b5c9af), next wall | native | – | no |
| privacybrowser | :39017 UnsupportedOperation (androidx.webkit) | no WebView support-library boundary | none | JAR, large | – | no |

## The fixes (new files only; verified sources copied where they exist)

- **R1 `adapter.activity.ProviderAuthorityRefs`** (runtime). After `B8BindExtras.afterProviders(bindData)`, every
  bind provider whose authority list contains an `@<id>` part takes the authority the PM projection resolves for
  the same class.
  - It uses `SelfComponentFallback.manifestProvider(name, flags)`, the lookup `afterProviders` already uses for
    metaData.
  - Literal authorities are untouched; an unprojected reference is left and logged. Marker: `[B8-PROV-AUTH]`.
- **R2 `adapter.activity.TelephonyServiceNames`** (runtime). Called right after `SystemServiceFetcherStubs.install()`
  (which runs TelephonyFetcher), inside the same try block. It registers `TelephonyManager→phone` and
  `SubscriptionManager→telephony_subscription_service`, only where that fetcher exists and the class has no name.
  - This is the same registration `OnlineConnectivityManager.registerServiceName` / `AppWidgetFetcher` perform.
  - Marker: `[B8-FETCH] phone class->name registered`.
- **R3 `adapter.core.GcmDefaultNonce`** (runtime, new code: neither upstream nor local trees have it).
  - A provider inserted first that offers `AES/GCM/NoPadding`, delegating every call to the next provider's
    implementation. It takes the service the way JCE does (full name, then `AES/GCM`, `AES//NoPadding`, `AES`
    with mode/padding set) and wraps it with `Cipher`'s protected constructor, so no explicit-provider lookup is
    involved.
  - Parameterless ENCRYPT/WRAP init gets a 12-byte nonce and a 128-bit tag (Conscrypt's behaviour). Everything
    else passes through.
  - Marker: `[B8-GCM] … installed`.
- **S1 `TelephonyFrameworkInitializer.getTelephonyServiceManager()` + field** (stubs, member-only merge).
  - It lazily creates framework.jar's `TelephonyServiceManager`; its registerers read ServiceManager by name, where
    TelephonyFetcher seeds `phone`/`isub`. That is the state AOSP has after `setTelephonyServiceManager` at boot.
  - The deployed members stay byte-identical; the setter remains the deployed no-op.
- **S2 `com.android.internal.util.Predicate`** (stubs, new class): AOSP ≤ 7.1's interface, the same one U11i ships
  in the wrong jar.

**One version per jar:**
- runtime: U11i `5ae3dd29` + U12 r1 (OwnProviderLocal, WlSettingsProvider, WlSettingsStub) + R1–R3;
- stubs: unified `2f365a75` + the android.net members (c6b1eb3bc0) + S1–S2, merged by that directory's
  `merge_smali.py`.

Both builds are deterministic: baksmali/smali 2.5.2 with jcommander-1.64 and `smali -j 1`, built twice, and the same
SHA from a bare `PATH`. They are persisted at `$WORKSPACES/westlake-inputs/generations/u12r2-v1/` with
`receipt.json`.

## Gates (`gate_u12r2.py` → `gates/gate-u12r2.txt`), against the unified state's jars

| check | result |
|---|---|
| `deployed_class_diff --frozen` runtime vs `5ae3dd29` | rc=0: 0 dropped, 0 reshaped, 10 allowed adds, 0 frozen broken |
| `deployed_class_diff --frozen` stubs vs `2f365a75` | rc=0: 9 allowed new classes (8 android.net + Predicate) |
| runtime members vs `5ae3dd29` | 1452 members, exactly 3 changed: `B7BindFixes.apply` (two needle sites), `AppSpawnXInit.preInitSettingsCache`, `AppSchedulerBridge.ensureBindApplication` |
| stubs members vs `2f365a75` | 1896 deployed members, 0 changed; 140 added (138 android.net + 2) |
| stubs members vs U12 r1 `3a12918a` | 2109 members, 0 changed: the android.net patch is carried unchanged |
| `check_frozen.py` | 0 violations. FZ-004/FZ-006 freeze separate files (JarVerificationProviderFix, VibratorFetcher); B7BindFixes / AppSchedulerBridge are only call sites |
| host JVM (`test_u12r2.py`, 6 tests, JDK ≥ 11) | GCM 12-byte default and Tink-style round trip; telephony class→name rules; authority `@2131755008` → projected, literal kept; getter stable; both jar SHAs |

**Deploying:**
- runtime: single-file replacement.
- stubs: a boot-class-path jar, so FZ-005 image rebake plus T8's four gates (rb / t4b / G1 / G2).

**Regression controls** (`regression-controls.csv`, all lit on U9):
- R1 changes antennapod's and fd-auxio's provider authorities;
- R3 sits under the 10 lit keys that reference `AES/GCM/NoPadding`, including passwordgenerator (Tink) and aegis.

No lit U9 hilog shows the S1/R2/S2 signatures.

## Files

- `predictions.csv`: 13 keys (lines, cause, upstream row, layer, fix, prediction, confidence).
- `regression-controls.csv`, `evidence/key-lines.txt`.
- `src-runtime/` (R1-R3), `compile-only-runtime/` (stand-in for `SelfComponentFallback`, not packed),
  `stubs/donor` (S1, S2), `stubs/compile-only` (`TelephonyServiceManager` stand-in), `stubs/members.tsv`.
- `build_u12r2.py`, `gate_u12r2.py`, `gates/` (gate log, stubs merge report, receipt), `test_u12r2.py`.
