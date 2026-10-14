# T7d stub-jar additions — spec for oc-t4/cc-t3 to build the T7d adapter-mainline-stubs.jar

Scan of the U5 three-board hilog corpus (330 hilog files, ~1.77 GB, boards 5ea/5cd/61b, 2026-09-30..10-01)
plus 740 non-hilog evidence files (0 extra members). Base = `feat/bms-walls` `44ab7862e` (T7c stubs: tagsoup
Parser + NetworkRequest.getNetworkSpecifier / NetworkInfo.getState / NetworkCapabilities.getLink*BandwidthKbps
/ MediaStore.*.EXTERNAL_CONTENT_URI). T7d adds the members below. Every method-level miss's log says
*"declaration … appears in …/adapter-mainline-stubs.jar"* → the class is already in the jar; add the member.

## Priority — FATAL misses fixable in adapter-mainline-stubs (add these)

| target app | class#member | signature | stub body | sev |
|---|---|---|---|---|
| **fd-gallery** | `android.provider.MediaStore#canManageMedia` | `(Landroid/content/Context;)Z` static | `return false;` (app takes the non-privileged path) | FATAL (main threw) |
| **fd-gallery** | `android.provider.MediaStore$Files#getContentUri` | `(Ljava/lang/String;)Landroid/net/Uri;` static | `return android.net.Uri.parse("content://media/" + volumeName + "/file");` | FATAL (worker) |
| **fd-plus** | `android.graphics.ColorMatrix#setSaturation` | `(F)V` virtual | prefer the real AOSP saturation math (pure, no platform dep) if the stub holds the 4x5 array; else `{ /* no-op: clears resolution */ }` | FATAL |
| **x** | `android.net.NetworkCapabilities#getSignalStrength` | `()I` virtual | `return Integer.MIN_VALUE;` // SIGNAL_STRENGTH_UNSPECIFIED | FATAL |
| **wikipedia** | `android.net.ssl.SSLSockets` (NEW class) | 2 static methods | see below | FATAL (kills OkHttp Dispatcher → no network) |

### New class `android/net/ssl/SSLSockets.java`
```java
// [T7d 2026-10-01] wikipedia/noice/fd-noice: NoClassDefFoundError android.net.ssl.SSLSockets in OkHttp
// AndroidPlatform. isSupportedSocket=false makes OkHttp fall back to the standard SSLSocket path (no
// Android-specific TLS extensions) instead of crashing the Dispatcher thread. setUseSessionTickets is a
// no-op (session tickets are an optimization, not required for TLS to work).
package android.net.ssl;
public final class SSLSockets {
    private SSLSockets() {}
    public static boolean isSupportedSocket(javax.net.ssl.SSLSocket socket) { return false; }
    public static void setUseSessionTickets(javax.net.ssl.SSLSocket socket, boolean useSessionTickets) {}
}
```

## Bonus — FATAL misses from other corpus apps (fold in if in scope)

| app | class#member | signature | stub body |
|---|---|---|---|
| vlc | `android.net.ConnectivityManager#requestNetwork` | `(Landroid/net/NetworkRequest;Landroid/net/ConnectivityManager$NetworkCallback;)V` virtual | `{}` no-op (no network → callback never fires; app doesn't crash) |
| noice | `android.media.MediaFrameworkPlatformInitializer#getMediaServiceManager` | `()Landroid/media/MediaServiceManager;` static | `return new android.media.MediaServiceManager();` + NEW empty class `android/media/MediaServiceManager.java` (`public final class MediaServiceManager { public MediaServiceManager() {} }`). LOW priority — already CAUGHT (WESTLAKE-469), non-fatal. |

## Do NOT add to adapter-mainline-stubs (flagged)

- `android.hardware.input.InputManagerGlobal#sService` — **29 apps** but the field lives in `framework.jar!classes2.dex`, not this jar, and it is a **CAUGHT** `[AdapterIIM]` reflection probe (info-level, process survives). Fixing it means patching framework.jar / the AdapterIIM shim, not the stub jar. Highest app-count but lowest value; leave it.
- `android.net.IConnectivityManager` — AIDL binder interface (Stub/Proxy/asInterface/txn codes), **not** a simple stub; currently caught by the Westlake local-service shim (`connectivity unavailable`, non-fatal). Leave to the shim.
- Out of scope (not android.*/java.*): `kotlinx.coroutines.CoroutineStart` (caught by [COROUTINE-FIX]), conscrypt/Westlake keystore probes, `org.wikipedia.DefaultIcon` / logback (app/third-party classes).

## Honest coverage note — 2 of the 6 target apps are NOT stub-fixable

- **fd-libretube**: no android.*/java.* member blocker in the T7c run — only the caught `sService` probe. Its
  remaining blocker (if any) is not an API resolution failure — look at conscrypt / native / UI, separately.
- **fd-feeder**: no android.*/java.* member blocker — only caught `sService` + out-of-scope
  `kotlinx.coroutines.CoroutineStart`. Not fixable by T7d stubs.

So T7d (stubs) can plausibly move **4 of the 6** targets past their API wall (wikipedia, fd-gallery, fd-plus,
x) + 2 bonus corpus apps (vlc, noice). fd-libretube/fd-feeder need a different track. Ground truth on board
still decides "lit" (screenshots).

## Build + gate + board (division of labor)

1. **cc-t3/oc-t4**: apply the additions above onto `feat/bms-walls` mainline-stubs, build one
   `adapter-mainline-stubs.jar` (`build_aosp_fw.sh --target=mainline-stubs.jar`, needs the hw248 AOSP mainline
   tree + turbine + d8), then re-gen the 27-file image with `t5_gen_image.sh` (dex2oat64 `ae865ddd`) = T7d
   image + jar.
2. **cc-wiki**: run `image_predeploy_gate.py --swap adapter-mainline-stubs --cand-bcp-dir <T7d bcp>
   --oatdump scripts/lab/oatdump_remote.sh` (G1 image↔BCP + G2 suspend-check); gate-fail ⇒ no board.
3. **cc-wiki**: after G1/G2 pass AND 61b is released (watch the blackboard lock, do NOT grab it), LOCK 61b
   ≤30 min, package-deploy (27 image + T7d jar), run the 4 targets + vlc/noice + HW/ZZ/aegis/ooniprobe
   controls, all `--reinstall`; rollback to U5 (resident byte-identical), UNLOCK.

## Build status (2026-10-01, cc-wiki self-build attempt)

**Done (cc-wiki):**
- Stub edits applied to all 6 members (`t7d-stub-edits.patch`, on `feat/bms-walls` 44ab7862e base): ColorMatrix.setSaturation, MediaStore.canManageMedia, MediaStore$Files.getContentUri (`content://media/<vol>/file`), NetworkCapabilities.getSignalStrength, ConnectivityManager.requestNetwork, + new `android/net/ssl/SSLSockets.java`. 112 source files, uploaded to hw248 `/home/alvin/cc-wiki-t7d/src`.
- **Dropped MediaServiceManager / getMediaServiceManager** (noice bonus): `MediaServiceManager` is defined only in framework.jar, so adding it to the stubs jar would be a NEW shadow — G3 rejects it.
- **G3 built + tested** (`image_predeploy_gate.py --g3-*`): dex class-def map proves all 6 additions are safe — ColorMatrix/MediaStore/MediaStore$Files/NetworkCapabilities/ConnectivityManager are ALREADY in the stubs jar (adding methods, not classes); `SSLSockets` is defined in NO other BCP jar (new, no shadow). On THIS route-A board framework.jar does NOT define ColorMatrix (contrary to stock AOSP) — it is already a stub-jar class, so extending it is safe.

**BLOCKER — jar build needs FWK_TURBINE (framework-minus-apex), not on hw248:**
- The mainline-stub sources reference ~10 `@hide` framework types (`MediaServiceManager`, `StatsServiceManager`, `BluetoothServiceManager`, `NfcServiceManager`, `DeviceConfigServiceManager`, `TelephonyServiceManager`) + framework-internal annotations (`android.annotation.SystemApi/IntDef/RequiresPermission/NonNull/Nullable/CallbackExecutor`, `com.android.internal.annotations.*`). These live only in `framework-minus-apex` (the FWK_TURBINE interface jar), NOT in the SDK `android.jar` (javac against `prebuilts/sdk/current/system/android.jar` fails on all 10 + the annotations).
- FWK_TURBINE is absent from hw248 (`find` = none). The r16 tree `out/` is empty (no prior Soong build), so building it = a cold full-framework Soong build: hours, and hw248 is at **96% disk (44 GB free)** — a framework build risks filling a shared disk. Not run.
- oc-t4's T7c jar came from an environment that already has FWK_TURBINE built. That environment (not hw248) is where the mechanical compile belongs.

**Next (needs a decision):** (a) run the compile in the env that has FWK_TURBINE (oc-t4's), using the uploaded sources / this patch; or (b) point cc-wiki to a prebuilt framework-minus-apex.jar; or (c) authorize a cold `m framework-minus-apex` on hw248 despite the disk risk. Once the T7d jar exists: G3 → t5_gen_image.sh → G1/G2 → board 61b (after it frees).

## BUILD DONE (2026-10-01 03:40, cc-wiki, per ACK(80) 03:23 dockbuild recipe)

The FWK_TURBINE blocker is resolved by BUILD.md's dockbuild recipe (not FWK_TURBINE): the 4 compile-only /
.classes jars (`core-all-compile-only`, `core-libart.classes`, `core-compile-only`, `framework.classes`, in
the a2hlab VM `~/a2hlab/ws/out/`) carry the @hide types + framework-internal annotations that the SDK
android.jar lacks. Built on this Mac via docker image `a2hlab-b5-java:24.04` in oc-t4's reused workspace
`~/a2hlab/ws/t7-stubs-build` (OrbStack-mounted): `javac -classpath <4 jars> @srcs.txt` (rc=0, 191 .class) →
`java -cp r8.jar com.android.tools.r8.D8 --min-api 34 --classpath <4 jars>` (rc=0) → thin-shell jar.

- **T7d jar** `6e2f450e` (192 classes = T7c 191 + SSLSockets); all 6 members verified via dex parse.
- **T7d image** dex2oat64 (T3c `ae865ddd`) → 27 files, boot.oat `9f64d69c`, adapter-mainline-stubs vdex `0x37851856`.
- **Gates: G3 PASS** (2 new classes NetworkInfo$State + SSLSockets, neither in another BCP jar) **· G1 PASS**
  (mainline swapped, 8 segments match v3c) **· G2 PASS** (String#hashCode 36==36 vs v3c, explicit suspend).
- Staged: local `_hw248-t7d/` + hw248 `/home/alvin/cc-wiki-t7d-{out,jars,stubs.jar}`. See `t7d-build-results.json`.
- **Pending board**: 61b package deploy (t6 SWAP_JAR) after U6 full sweep frees it; not rushed.

## T7d REBUILT with full AOSP tagsoup (2026-10-01 04:00, per ACK(80) 03:53)

Replaced the incomplete 2-file tagsoup stub (Parser + HTMLSchema, no `implements XMLReader`) with the FULL
AOSP **android-14.0.0_r1 external/tagsoup** source (15 .java, `src/**/*.java`; byte-identical on hw248
`aosp-14.0.0_r1-art` and a2hlab `android-source/external-tagsoup`, Parser.java sha `aa68cc4d`). The other 6
android stub additions are unchanged. Rationale: the BCP tagsoup shadows the app's bundled tagsoup (AOSP keeps
full tagsoup on the boot classpath), so it must be complete — the stub's missing `implements XMLReader` is
what crashed fd-libretube (IncompatibleClassChangeError). tagsoup is defined in NO other BCP jar (verified),
so the full set is G3-safe.

- Rebuild: same dockbuild (a2hlab-b5-java:24.04, 4 compile-only jars, srcs.txt 112→125). javac rc=0 (205
  .class), D8 rc=0.
- **T7d jar** `d8b2406e` (206 classes = 190 baseline + NetworkInfo$State + SSLSockets + 14 tagsoup);
  Parser now `extends DefaultHandler implements ScanHandler, XMLReader, LexicalHandler` with real
  parse/setContentHandler/setFeature/setProperty/getProperty. classes.dex 299,548 B.
- **T7d image** dex2oat64 (T3c) → 27 files, boot.oat `e1286c71`, adapter-mainline-stubs vdex `0xe5e181e2`.
- **Gates: G3 PASS** (16 new classes incl 14 tagsoup, none in another BCP jar) **· G1 PASS** (mainline
  swapped, 8 segments match v3c) **· G2 PASS** (String#hashCode 36==36 vs v3c).
- Staged: local `_hw248-t7d/` (updated) + hw248 `/home/alvin/cc-wiki-t7d-{out,jars,stubs.jar}`.
- **Board list** now: wikipedia, fd-gallery, fd-plus, x, vlc, noice, fd-noice (3×), **+ fd-libretube**
  (tagsoup-XMLReader fix) + HW/ZZ/aegis/ooniprobe controls. After U6 frees 61b.
