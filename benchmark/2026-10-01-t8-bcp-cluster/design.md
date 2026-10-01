# T8 — BCP / boot-image cluster design (#90)

Four walls whose fix is a **boot-classpath class** (can't be shadowed by `oh-adapter-runtime.jar`, which is
PathClassLoader / non-BCP): once a class lives in the BCP it can only be changed by rebuilding the boot image. T7d
(mine, DIGEST §389) already drove this path — `adapter-mainline-stubs.jar` stubs + full-AOSP tagsoup → re-bake → board.
T8 collects the next four and reuses that pipeline.

## Shared re-bake pipeline (FZ-005 dex2oat; reproducible, proven T6c/T7d)
All BCP items below go through the **same** steps (DIGEST §386–389):
1. **Edit the BCP source**: `framework/mainline-stubs/java/…` (items ①③a) or the `adapter-runtime-bcp.jar` adapter
   source (item ②). When the build tree `/home/dspfac/bridge-build` is unreachable, use the **CLAMP48 surgical path**:
   `baksmali → smali additive patch → smali 2.5.2 -a 29 → dex 039`, as done for WindowSessionAdapter (DIGEST §12/§164).
2. **Build the jar** (d8 / dex).
3. **Re-bake the boot image** with the self-built **RB-OFF host dex2oat** (oat247, `ART_USE_READ_BARRIER=false`,
   `concurrent-copying=false`; oc-t4 T3b host + T5c recipe, boot.oat `0e7dc0e4`/boot.art `6e909d6c`). **Do NOT swap
   libart** — overlay only the 27 boot-image files (board R155 libart `8c2796fc` accepts them, T6c PASS).
4. **Offline gates before board** (all mine, `knowledge/toolchains/art-r155/` + `image_predeploy_gate.py`):
   rb-gate (`concurrent-copying=false`), t4b-gate (libart↔oat RB consistent), **G1** (image↔BCP dex-checksum per
   `boot-<jar>.vdex` kChecksumSection — the changed jar MUST be in `swap_jars`), **G2** (oatdump compiled-code
   suspend-check shape = explicit `pTestSuspend`, not the implicit fault-handler form that crashes on R155). G2 is
   mandatory on any jar/image swap; `SKIPPED≠PASS`.
5. **Deploy**: overlay the 27 files, appspawn-x socket fix (`0:6005`/`0660`/`appspawn_socket`) after start stabilises,
   verify RUNTIME fingerprint unchanged (image-only, libart untouched) + boot_id.
6. **Bundle ①②③a into ONE re-bake** (they all change BCP jars; one image covers all). ③b is routed to native (see below).

## Item ① — `com.android.org.conscrypt.SSLParametersImpl` presence stub (toutiao OkHttp)
| field | value |
|---|---|
| **Wall** | toutiao OkHttp `NullPointerException("No platform found on Android")` — both `Android10Platform`/`AndroidPlatform.buildIfSupported` `findClass("com.android.org.conscrypt.SSLParametersImpl")`; route-A has no conscrypt apex (okhttp-platform.md, master `f57867194`). |
| **Source origin** | **Already written** — `framework/mainline-stubs/java/com/android/org/conscrypt/SSLParametersImpl.java` is a presence-only stub (private throwing ctor; comment §676/§441: okhttp only resolves the type + probes a field, so class *presence* suffices; TLS goes through JSSE/`android.net.ssl.SSLSockets`, FZ-008, already present). **It is in the current mainline-stubs source but NOT in the deployed j10g boot image** (cc-t3 dexdump of the deployed payload = 0 conscrypt hits). |
| **Re-bake?** | **YES** — `com.android.org.conscrypt.*` is BCP; the stub must be in `adapter-mainline-stubs.jar` in the baked image. No new code needed beyond re-baking with current mainline-stubs (confirm the stub is in the jar that goes into `swap_jars`). |
| **Regression** | `fd-droidify`, `newpipe` (stock okhttp 4.x, 0 refs to SSLParametersImpl, use SSLSockets) must stay **lit** — unaffected by adding the class. `fd-tusky` (older `AndroidPlatform`, reflects `OptionalMethod` setUseSessionTickets/setHostname/ALPN on it) — the presence-only stub has none of those; OkHttp `OptionalMethod` tolerates absent methods (no-op), so tusky should build its platform; its network path should recover or at least not regress. Watch tusky as a *secondary* (its "lit" is UI-before-network, not a clean okhttp control). |
| **Evidence app** | toutiao (Android10Platform path). Secondary: fd-tusky (AndroidPlatform path). |

## Item ② — `PackageManagerAdapter.getInstallSourceInfo` → non-null all-null `InstallSourceInfo` (yahtzeedicer)
| field | value |
|---|---|
| **Wall** | `cv2-org-secuso-privacyfriendlyyahtzeedicer` — `getInstallSourceInfo(self)` → `PackageManager$NameNotFoundException` (cc-t3 cluster-6; the app reads its own install source on launch and doesn't null-check). |
| **Source origin** | `adapter.packagemanager.PackageManagerAdapter` — add/override `getInstallSourceInfo(String)` to return `new InstallSourceInfo(null, null, null, null)` (no initiating/originating/installing package, no signing info) = "installed by nobody", the truthful route-A answer. `android.content.pm.InstallSourceInfo` is a BCP SDK-34 class in `framework.jar` (present); **confirm its exact ctor arity on the deployed framework.jar** (cx-bms/codex via DEX) before coding — SDK 34 has the 4-arg form, later SDKs add fields. |
| **Re-bake?** | **YES (BCP).** Verified: the **deployed `oh-adapter-runtime.jar` (238ffc14) has 0 `PackageManagerAdapter`** — the adapter is in the BCP jar (`adapter-runtime-bcp.jar`, same jar as WindowSessionAdapter, DIGEST §164/§276), not the runtime jar. So the method change + `InstallSourceInfo` construction must be baked in (CLAMP48-style smali patch to `adapter-runtime-bcp.jar` if the build tree is unreachable, like telephony/CLAMP48). cc-t3's note of **two PackageManagerAdapter instances** (double-load) is a separate issue — hand to cx-bms; the getInstallSourceInfo synthesis stands regardless. |
| **Regression** | yahtzeedicer lit. Apps that query `getInstallSourceInfo` of *other* packages still get all-null (no installer) — ensure no lit app depends on a real installer name (none expected on route-A; the field was absent before). |
| **Evidence app** | yahtzeedicer. |

## Item ③a — `com.android.i18n.phonenumbers.PhoneNumberUtil` real impl (clipboardeditor)
| field | value |
|---|---|
| **Wall** | `cv2-com-trianguloy-clipboardeditor` — `NoSuchMethodError: no static getInstance() … PhoneNumberUtil` (DIGEST §381). |
| **Source origin** | Current `framework/mainline-stubs/java/com/android/i18n/phonenumbers/PhoneNumberUtil.java` is an **18-line empty shell** (empty ctor + 3 empty nested classes, **no `getInstance()`**). Replace with the **real AOSP `external/libphonenumber`** `com.android.i18n.phonenumbers.*` (the i18n-repackaged libphonenumber + its metadata assets) — exactly the pattern T7d used to replace the tagsoup stub with full AOSP r1 tagsoup. |
| **Re-bake?** | **YES** — `com.android.i18n.*` is BCP; the real classes + metadata go into `adapter-mainline-stubs.jar` → re-bake. Larger than a stub (libphonenumber carries metadata resources); confirm the metadata loader path (`PhoneNumberUtil.createInstance` reads `/com/android/i18n/phonenumbers/data/…`) resolves from the baked jar. |
| **Regression** | clipboardeditor lit. Any lit app already using i18n phone formatting unaffected (the shell gave them nothing; real impl only adds capability). Size: libphonenumber adds ~several hundred KB to the BCP — check the image budget / G1 checksum. |
| **Evidence app** | clipboardeditor. |

## Item ③b — `Bitmap` created without a ColorSpace (fd-musicplayer) — **route to NATIVE, not BCP**
| field | value |
|---|---|
| **Wall** | `fd-musicplayer` — `IllegalArgumentException: can't create bitmap without a color space` at `Bitmap.createBitmap(Bitmap.java:1203)` ← `createScaledBitmap(831)` ← `df.j.<init>` ← `TracksFragment` (album-art thumbnail: **decode-then-scale**). |
| **Root (analysis)** | `Bitmap.createScaledBitmap(src,…)` → `createBitmap(src, …)` → the overload throws when `src.getColorSpace()==null`. So the **decoded source bitmap has a null ColorSpace** = our **native image-decode path (BitmapFactory/skia/libjnigraphics) did not attach sRGB** to the decoded bitmap. This is a **native gap, not a BCP `Bitmap.java` bug** — `Bitmap.createBitmap(w,h,config)` already defaults sRGB; the null comes from the decode. |
| **Re-bake?** | **NO (not a BCP fix).** Primary fix is **native**: make the decode attach `ColorSpace.get(SRGB)` (or set the skia colorspace) so decoded bitmaps are non-null — **hand to cx-bms (native cluster)**, not T8. A BCP fallback (defensive null→sRGB default inside `Bitmap.createBitmap`) exists but touches the **hottest BCP class** (every bitmap) → very high regression surface → **discouraged**; only if the native decode can't be fixed. |
| **Regression** | fd-musicplayer; and because Bitmap/decode is ubiquitous, any native decode change must keep all lit image apps (fd-gallery etc.) lit. |
| **Evidence app** | fd-musicplayer. (Confirm on-board whether the null ColorSpace is on the decoded source via a one-line log of `src.getColorSpace()` in the decode path before deciding the exact native site.) |

## Summary / hand-off
| item | class | jar | re-bake | lane | evidence |
|---|---|---|---|---|---|
| ① | `com.android.org.conscrypt.SSLParametersImpl` (presence stub, exists in source) | mainline-stubs (BCP) | **yes** | T8 (this) | toutiao (+tusky) |
| ② | `PackageManagerAdapter.getInstallSourceInfo` → all-null `InstallSourceInfo` | adapter-runtime-bcp.jar (BCP) | **yes** | T8 (this) | yahtzeedicer |
| ③a | `com.android.i18n.phonenumbers.PhoneNumberUtil` (real AOSP libphonenumber) | mainline-stubs (BCP) | **yes** | T8 (this) | clipboardeditor |
| ③b | `Bitmap` null ColorSpace (decode attaches sRGB) | native decode (libjnigraphics/skia) | **no** | **cx-bms native** | fd-musicplayer |

- **①②③a ride ONE boot-image re-bake** (all BCP), through the proven T7d/FZ-005 dex2oat pipeline + the 4 offline gates;
  ① is nearly free (stub already in source). Evidence apps re-run after deploy; regression controls above must stay lit;
  screenshots are ground truth (`alive`≠`lit`).
- **③b is not BCP** — routed to the native lane (decode must attach a ColorSpace); the BCP Bitmap fallback is a
  last resort due to regression surface.
- **Blocking caveat (DIGEST §276)**: baseline jar identity is the real gate — before the surgical patch, confirm each
  class's actual *deployed* stage jar (②'s `PackageManagerAdapter` in `adapter-runtime-bcp.jar`; ①③a's stubs in the
  baked `adapter-mainline-stubs.jar`) via on-board DEX class_defs, and confirm `InstallSourceInfo`'s ctor on the
  deployed `framework.jar`. T8 is design-only; no board touch.

Evidence: okhttp-platform.md (master `f57867194`); mainline-stubs source (SSLParametersImpl, PhoneNumberUtil shell);
deployed `oh-adapter-runtime.jar` 238ffc14 dexdump (0 PackageManagerAdapter → BCP); DIGEST §12/§164/§276 (adapters in
adapter-runtime-bcp.jar BCP), §386–389 (dex2oat RB-off, T6c PASS, image_predeploy_gate, T7d); fd-musicplayer U9 hilog.
