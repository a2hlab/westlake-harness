# r17t (ec583a26): AudioProductStrategy stub + two boot-routed walls (2026-09-30)

**One line:** r17t (on r17s `3b523289`) adds one clean runtime-JAR fix — Noice's audio-JNI `System.exit(1)`
— by pre-seeding `AudioProductStrategy.sAudioProductStrategies` empty so the native list call is never made.
The two extra walls the outer loop routed here (**gallery `EXTERNAL_CONTENT_URI`**, **vlc ConstraintLayout
inflate**) are **not runtime-JAR-fixable** and are recorded for the oc-t4 boot/resource line.

## The fix in r17t (JAR — clean)

`AudioProductStrategy.getAudioProductStrategies()` (`:77`) caches its result in the private static
`sAudioProductStrategies` and only enters its lazy branch (`initializeAudioProductStrategies :189 →
native_list_audio_product_strategies :199`, unexported on route-A → `System.exit(1)`) when that field is
null. `B7BindFixes.stubAudioProductStrategies()` reflectively pre-seeds the field with
`Collections.emptyList()` at bind, so the getter never touches native. No ArtMethod patch (that SIGSEGVs on
this generation's ART, per cc-wiki). Log: `[B8-AUDIO] AudioProductStrategy.sAudioProductStrategies
pre-seeded empty`.

Death-point evidence (Noice, `com.github.ashutoshgngwr.noice`, cc-wiki 09:06):
`AudioProductStrategy.native_list_audio_product_strategies(Native) ← initializeAudioProductStrategies(:189)
← getAudioProductStrategies(:77) → System.exit(1)`.

### Same-family coverage (r17p-61b-sweep hilog)
- **opencamera** — same death point (`getAudioProductStrategies → initializeAudioProductStrategies →
  native`). **The stub should cover it.**
- **vlc** — hits `getAudioProductStrategies` **and** additionally `AudioSystem.native_get…` (a *different*
  native, `android.media.AudioSystem`). The stub covers only the AudioProductStrategy half; vlc may still
  die on the AudioSystem native — a separate `AudioSystem` stub would be needed if so.

## Two walls the outer loop routed to r17t — judged NOT JAR-fixable

Evidence: cc-wiki's 5ea `second-activity-32df-r17s` run.

### gallery (`org.fossify.gallery`) — boot stub missing field → oc-t4
```
NoSuchFieldError: No static field EXTERNAL_CONTENT_URI of type Landroid/net/Uri; in class
Landroid/provider/MediaStore$Images$Media; ... (declaration ... in /system/android/framework/adapter-mainline-stubs.jar)
```
`MediaStore$Images$Media` lives in the **boot** `adapter-mainline-stubs.jar` and its stub **omits the
`EXTERNAL_CONTENT_URI` static field**. The runtime JAR cannot add a field to an already-defined boot class,
and a `sget-object` field access has no interception point (unlike a method). **Not JAR-fixable → oc-t4 boot
image** (add the MediaStore URIs to the stub, same rebuild as tagsoup).

### vlc (`org.videolan.vlc`) OnboardingActivity — theme-attr native resolution → oc-t4/resource
```
InflateException: ...activity_onboarding line #9: Error inflating class androidx.constraintlayout.widget.ConstraintLayout
Caused by: java.lang.UnsupportedOperationException: Failed to resolve attribute at index 13:
  TypedValue{t=0x2/d=0x7f040072 a=-1}, theme={... Theme.VLC.Transparent, forced, Theme.AppCompat.Empty, forced, ...}
  at android.content.res.TypedArray.getDrawableForDensity(:1007) at ConstraintLayout.<init>(:587)
```
ConstraintLayout's constructor reads a styled attribute (index 13) whose value is an **unresolved theme-attr
reference** (`t=0x2` TYPE_ATTRIBUTE, `d=0x7f040072`, `a=-1` = not resolved) — the forced theme overlay
(`Theme.AppCompat.Empty, forced`) doesn't resolve the vlc custom attr `0x7f040072`, so the **native**
`TypedArray.getDrawableForDensity` throws. This is the same family as fd-api's `Theme.AppCompat` ISE
(theme/resource projection). Fixing it needs **aapt2 resource/theme injection** or a **boot-level TypedArray
/ theme-application change**; the only JAR route (patching the boot `TypedArray` method) requires an
ArtMethod patch, which SIGSEGVs on this generation. **Not cleanly JAR-fixable → oc-t4 boot/resource line.**
(vlc: `alive t5=yes t20=no` — its main screen shows, OnboardingActivity is the wall.)

## Verdict
- **r17t** = r17s `3b523289` + the AudioProductStrategy stub only. SHA `ec583a26`. Queued 3rd on 61b (after
  oc-t4, cx-t0); regression set + fd-noice/noice/opencamera/vlc to be verified when the board frees.
- **gallery `EXTERNAL_CONTENT_URI`** and **vlc ConstraintLayout theme-attr** → **oc-t4 boot/resource line**
  (same rebuild as tagsoup); not carried into r17t.
