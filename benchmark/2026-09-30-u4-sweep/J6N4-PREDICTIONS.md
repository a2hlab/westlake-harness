# Frozen J6 + N4 predictions (66 keys)

The earlier mistake was equating shipped symbols or missing error text with a passed wall, and a passed wall with a new light. This prospective sheet freezes checkpoint predictions and separate t20 expectations **before the combined batch**, not after reading its outcomes.

## Scope and forecast

Outer ACK(90) 2026-09-30 23:36:46 + 23:49:19 + 23:55:12: J5b base + alarm split + metadata + service-query; N4 owner/EGL/megazord/OpenSLES; Noice gate unresolved

U4 first sweep stays 22 UI; AntennaPod/Notes repeat recovery is a separately attributed control fact. Unified state remains U3; this is not a U3-to-U4 rescore.

- Predictions: {"不变": 40, "过墙": 17, "unknown": 9}.
- Primary checkpoint instances: {"N4-owner": 11, "N4-egl": 2, "N4-megazord": 2, "J6-metadata": 1, "J6-service-query": 1, "N4-opensles": 1}. Metadata overlaps one owner key; do not add checkpoint counts as distinct apps or lights.
- Alarm split rechecks: fd-k9 and fd-android. These remain UI preservation controls.
- No unconditional new-light forecasts. `过墙` is the stated operational checkpoint, `不变` is exact-wall persistence or reviewed UI preservation, `unknown` is explicitly unforecastable. `点亮` is reserved for a genuine own-UI forecast; none is justified here.
- fd-noice is an unresolved mandatory restoration gate, not an invented N4 fix; noice is another APK of the same package. Unknown prediction does not waive the restoration release gate.
- Bitmap, boot APIs/TagSoup, theme/resource and real WebView-provider work are NOT included. Musicplayer query can improve while bitmap still fails.

## Freeze and pre-run binding

CSV, this Markdown, criteria.json and predict.py are SHA-frozen in `scoring-inputs/J6N4-predictions-reference.json`; `J6N4-PREDICTIONS.sha256` is the portable check list. The board ACK repeats the CSV SHA and actual freeze time. Historical SCORING files are untouched.

Final J6/N4 artifacts are not yet bound by this forecast. Before the first combined-batch run, cx-t0/outer must add a separate dated receipt binding this reference/CSV SHA to final JAR SHA, native generation manifest SHA, exact changed-unit/patch coverage, APK+sidecar cohort manifest, both RUNTIME/BOOTIMAGE fingerprint files and the frozen-gate receipt. Missing approved fixes or changed input identities are a different candidate, not a free prediction edit. Do not overwrite this frozen reference to fill in artifact hashes. A revised prediction requires a new named version, separate SHA and pre-run ACK. No retrospective revision is prospective.

## Log checkpoints

All witnesses must belong to the APK/package-bound target PID and relevant execution episode. Reject OH_RegHook registration text as a call-level witness, unrelated processes, truncated logs and absent-only success. These are criteria, not claims that every requested trace already exists; absent required instrumentation means unknown, not success.

### N4-owner

- Positive: Same target PID: [N3-OWNER] resident runtime published + [N2-OWNER] ABI global ready, then configuration returned 0 or an actual app dlopen attempt after configuration; no duplicate runtime construction
- Failure: Flutter default-owner namespace configuration failed: [nonzero] OR [N3-OWNER] resident runtime unavailable
- Limit: Publication alone is not completion proof; a later consumer relocation can fail after this configuration checkpoint passed

### N4-egl

- Positive: Executed eglInitialize on a real EGLDisplayImpl: non-null field access completed and real EGL initialization reached (EGL_TRUE or a recorded EGL error), or actual later eglChooseConfig/context execution; not OH_RegHook registration
- Failure: JNI fid == null with GetLongField and EGLImpl.eglInitialize in the same PID/TID abort context
- Limit: EGL_FALSE after verified field access is a field-contract hit plus a separate later EGL wall, not a light; missing execution evidence stays unknown

### N4-megazord

- Positive: Actual libmegazord load/relocation or a specific later relocation/init error in that same consumer after resolving __get_h_errno@LIBC
- Failure: libmegazord.so: __get_h_errno: symbol not found
- Limit: __sF/JNA registration success and absence of the old string alone do not prove this checkpoint

### N4-opensles

- Positive: Actual libarc relocation completed with slCreateEngine bound to real platform OpenSLES, or specific later libarc relocation; retain provider path/SHA/namespace witness
- Failure: libarc.so: slCreateEngine: symbol not found
- Limit: A provider-handle dlsym alone is insufficient; engine/PCM behavior and IID identity are separate later checks

### J6-metadata

- Positive: [B8-PM] projected getApplicationInfo metaData=... for im.vector.app plus self GET_META_DATA showing io.sentry.auto-init=false and execution beyond the formerly failing initialization
- Failure: DSN is required. Use empty string or set enabled to false in SentryOptions to disable SDK.
- Limit: A metadata count alone does not prove the false value; score independently of N4-owner

### J6-service-query

- Positive: [B8-PM] projected queryIntentServices androidx.media3.session.MediaSessionService -> positive self service count, correct PlaybackService in the returned slice, and successful SessionToken resolution
- Failure: Failed to resolve SessionToken for ComponentInfo{org.fossify.musicplayer/org.fossify.musicplayer.playback.PlaybackService}
- Limit: The bitmap color-space fatal already followed the old query error in U4; seeing bitmap again alone is NOT query-pass proof

### J6-alarm-recheck

- Positive: [B8-FETCH] alarm fetcher replaced in the target process (outer-requested split recheck)
- Failure: AlarmFetcher split absent or alarm behavior regresses; missing marker with incomplete logs remains unknown
- Limit: Revalidates frozen alarm behavior for fd-k9/fd-android; no new-light or vibrator-manager repair claim

## Per-key frozen table

`L` is the original U4 hilog line, not a proposed future line number. The CSV and criteria.json carry full paths, SHA, original text, separate first-fatal witnesses and each row's log/t20 rules. First wall means the first supported causal/precursor wall among archived signatures, not a claim to have discovered every earlier warning. Caught precursors and the first fatal must not be conflated.

| Key | Current first wall / evidence | Fix or recheck | Forecast | Log criterion | t20 expectation |
|---|---|---|---|---|---|
| aegis | No first-page blocking wall in outer-reviewed U4 own UI (reviewed-ui-control) | None for current wall | 不变 | UI-PRESERVE + target bind/log capture | Own UI preserved |
| anki | No first-page blocking wall in outer-reviewed U4 own UI (reviewed-ui-control) | None for current wall | 不变 | UI-PRESERVE + target bind/log capture | Own UI preserved |
| antennapod | U4 first-run RenderThread SIGSEGV; outer 23:01 reports 3/3 zero-variable UI recovery (L43248) | None for current wall | 不变 | UI-PRESERVE + target bind/log capture | Own UI preserved |
| burgerking | Running a recovery step for libreactnative.so due to com.facebook.soloader.C: java.lang.UnsatisfiedLinkError: Flutter default-owner namespace configuration failed: 2 (L31749) | N4-owner | 过墙 | N4-owner | Own UI unknown; checkpoint advance is not a lighting promise |
| fd-AppManager | No explicit causal fatal; observation-only unlit outcome (no-confirmed-causal-wall) | None for current wall | unknown | OBSERVE-ONLY / no automatic hit | Own UI unknown; checkpoint advance is not a lighting promise |
| fd-android | No first-page blocking wall in outer-reviewed U4 own UI (reviewed-ui-control) | J6-alarm-recheck | 不变 | J6-alarm-recheck | Own UI preserved |
| fd-api | AppCompat theme requirement (L18786) | None for current wall | 不变 | EXACT-OLD-WALL | Unlit likely: unchanged known wall; still review actual frame |
| fd-app | [java_vm_ext.cc:591] JNI DETECTED ERROR IN APPLICATION: fid == null (L32846) | N4-egl | 过墙 | N4-egl | Own UI unknown; checkpoint advance is not a lighting promise |
| fd-auxio | No first-page blocking wall in outer-reviewed U4 own UI (reviewed-ui-control) | None for current wall | 不变 | UI-PRESERVE + target bind/log capture | Own UI preserved |
| fd-binaryeye | No first-page blocking wall in outer-reviewed U4 own UI (reviewed-ui-control) | None for current wall | 不变 | UI-PRESERVE + target bind/log capture | Own UI preserved |
| fd-breezyweather | Object.getClass null producer (L56121) | None for current wall | 不变 | EXACT-OLD-WALL | Unlit likely: unchanged known wall; still review actual frame |
| fd-calendar | No first-page blocking wall in outer-reviewed U4 own UI (reviewed-ui-control) | None for current wall | 不变 | UI-PRESERVE + target bind/log capture | Own UI preserved |
| fd-catima | Object.getClass null producer on resume (L40507) | None for current wall | 不变 | EXACT-OLD-WALL | Unlit likely: unchanged known wall; still review actual frame |
| fd-client | WestlakeSSLContext has no SSLEngine; later accountManager null (L59293) | None for current wall | 不变 | EXACT-OLD-WALL | Unlit likely: unchanged known wall; still review actual frame |
| fd-com-amaze-filemanager | No first-page blocking wall in outer-reviewed U4 own UI (reviewed-ui-control) | None for current wall | 不变 | UI-PRESERVE + target bind/log capture | Own UI preserved |
| fd-com-kunzisoft-keepass-libre | No first-page blocking wall in outer-reviewed U4 own UI (reviewed-ui-control) | None for current wall | 不变 | UI-PRESERVE + target bind/log capture | Own UI preserved |
| fd-droidify | No first-page blocking wall in outer-reviewed U4 own UI (reviewed-ui-control) | None for current wall | 不变 | UI-PRESERVE + target bind/log capture | Own UI preserved |
| fd-etar | No first-page blocking wall in outer-reviewed U4 own UI (reviewed-ui-control) | None for current wall | 不变 | UI-PRESERVE + target bind/log capture | Own UI preserved |
| fd-feeder | NetworkRequest.getNetworkSpecifier missing (T7 held) (L43532) | None for current wall | 不变 | EXACT-OLD-WALL | Unlit likely: unchanged known wall; still review actual frame |
| fd-fennec_fdroid | Error relocating /data/app/el1/bundle/public/org.mozilla.fennec_fdroid/android/lib/arm64-v8a/libmegazord.so: __get_h_errno: symbol not found (L31712) | N4-megazord | 过墙 | N4-megazord | Own UI unknown; checkpoint advance is not a lighting promise |
| fd-filemanager | No first-page blocking wall in outer-reviewed U4 own UI (reviewed-ui-control) | None for current wall | 不变 | UI-PRESERVE + target bind/log capture | Own UI preserved |
| fd-fitness | No first-page blocking wall in outer-reviewed U4 own UI (reviewed-ui-control) | None for current wall | 不变 | UI-PRESERVE + target bind/log capture | Own UI preserved |
| fd-fluffychat | java.util.concurrent.ExecutionException: java.lang.UnsatisfiedLinkError: Flutter default-owner namespace configuration failed: 2 (L32433) | N4-owner | 过墙 | N4-owner | Own UI unknown; checkpoint advance is not a lighting promise |
| fd-gallery | MediaStore.Images.Media.EXTERNAL_CONTENT_URI missing (T7 held) (L56125) | None for current wall | 不变 | EXACT-OLD-WALL | Unlit likely: unchanged known wall; still review actual frame |
| fd-im-vector-app | Sentry DSN precursor at40970; owner configuration fatal at55229 (L40970) | N4-owner, J6-metadata | 过墙 | N4-owner+J6-metadata | Own UI unknown; checkpoint advance is not a lighting promise |
| fd-immich | Caused by: java.lang.VerifyError: Verifier rejected class A2.b: void A2.b.onMethodCall(q7.m, q7.o) failed to verify: void A2.b.onMethodCall(q7.m, q7.o): [0xA6] cannot access instance field boolean b7.a.D from object of type Unresolved Reference: d7.c (declaration of 'A2.b' appears in /data/app/el1/bundle/public/app.alextran.immich/android/base.apk) (L39602) | N4-owner | 过墙 | N4-owner | Own UI unknown; checkpoint advance is not a lighting promise |
| fd-k9 | No first-page blocking wall in outer-reviewed U4 own UI (reviewed-ui-control) | J6-alarm-recheck | 不变 | J6-alarm-recheck | Own UI preserved |
| fd-kitchenowl | java.util.concurrent.ExecutionException: java.lang.UnsatisfiedLinkError: Flutter default-owner namespace configuration failed: 2 (L31408) | N4-owner | 过墙 | N4-owner | Own UI unknown; checkpoint advance is not a lighting promise |
| fd-libre | java.util.concurrent.ExecutionException: java.lang.UnsatisfiedLinkError: Flutter default-owner namespace configuration failed: 2 (L38214) | N4-owner | 过墙 | N4-owner | Own UI unknown; checkpoint advance is not a lighting promise |
| fd-libretube | TagSoup Parser.setProperty missing (T7 held) (L37133) | None for current wall | 不变 | EXACT-OLD-WALL | Unlit likely: unchanged known wall; still review actual frame |
| fd-meet | Collection.iterator null producer / restrictions investigation (L37123) | None for current wall | 不变 | EXACT-OLD-WALL | Unlit likely: unchanged known wall; still review actual frame |
| fd-minetest | No first-page blocking wall in outer-reviewed U4 own UI (reviewed-ui-control) | None for current wall | 不变 | UI-PRESERVE + target bind/log capture | Own UI preserved |
| fd-mobile | No explicit causal fatal; observation-only unlit outcome (no-confirmed-causal-wall) | None for current wall | unknown | OBSERVE-ONLY / no automatic hit | Own UI unknown; checkpoint advance is not a lighting promise |
| fd-mpv | No first-page blocking wall in outer-reviewed U4 own UI (reviewed-ui-control) | None for current wall | 不变 | UI-PRESERVE + target bind/log capture | Own UI preserved |
| fd-musicplayer | SessionToken self-service query at34313; bitmap color-space fatal at52303 (L34313) | J6-service-query | 过墙 | J6-service-query | Unlit likely while bitmap wall remains; successful query alone is not a light |
| fd-netguard | No first-page blocking wall in outer-reviewed U4 own UI (reviewed-ui-control) | None for current wall | 不变 | UI-PRESERVE + target bind/log capture | Own UI preserved |
| fd-noice | Repeatable U4 white UI without causal fatal; ANL interaction experiment unresolved at forecast cutoff (no-confirmed-causal-wall) | None for current wall | unknown | OBSERVE-ONLY / no automatic hit | Unknown forecast; outer must require welcome UI restored before promotion |
| fd-notes | U4 first-run RenderThread SIGSEGV; outer 23:01 reports 3/3 zero-variable UI recovery (L45332) | None for current wall | 不变 | UI-PRESERVE + target bind/log capture | Own UI preserved |
| fd-organicmaps | Caused by: java.lang.UnsatisfiedLinkError: Flutter default-owner namespace configuration failed: 2 (L33430) | N4-owner | 过墙 | N4-owner | Own UI unknown; checkpoint advance is not a lighting promise |
| fd-plus | NetworkInfo.getState missing; later OsmandMap null (T7 held) (L43973) | None for current wall | 不变 | EXACT-OLD-WALL | Unlit likely: unchanged known wall; still review actual frame |
| fd-reader | Null reference used for synchronization / haptics producer (L57040) | None for current wall | 不变 | EXACT-OLD-WALL | Unlit likely: unchanged known wall; still review actual frame |
| fd-saber | java.util.concurrent.ExecutionException: java.lang.UnsatisfiedLinkError: Flutter default-owner namespace configuration failed: 2 (L29747) | N4-owner | 过墙 | N4-owner | Own UI unknown; checkpoint advance is not a lighting promise |
| fd-seal | HOST INPUT: native sidecar is not an AArch64 shared ELF: libaria2c.zip.so (host-input-not-run) | None for current wall | unknown | OBSERVE-ONLY / no automatic hit | No t20 expected without separately approved input recovery; do not count capture absence as runtime failure |
| fd-shatteredpixeldungeon | [java_vm_ext.cc:591] JNI DETECTED ERROR IN APPLICATION: fid == null (L29158) | N4-egl | 过墙 | N4-egl | Own UI unknown; checkpoint advance is not a lighting promise |
| fd-stk | No first-page blocking wall in outer-reviewed U4 own UI (reviewed-ui-control) | None for current wall | 不变 | UI-PRESERVE + target bind/log capture | Own UI preserved |
| fd-tasks | No first-page blocking wall in outer-reviewed U4 own UI (reviewed-ui-control) | None for current wall | 不变 | UI-PRESERVE + target bind/log capture | Own UI preserved |
| fd-tusky | No first-page blocking wall in outer-reviewed U4 own UI (reviewed-ui-control) | None for current wall | 不变 | UI-PRESERVE + target bind/log capture | Own UI preserved |
| fd-tutanota | WebView provider path UnsupportedOperationException; real provider still held (L38564) | None for current wall | 不变 | EXACT-OLD-WALL | Unlit likely: unchanged known wall; still review actual frame |
| fd-uhabits | No explicit causal fatal; observation-only unlit outcome (no-confirmed-causal-wall) | None for current wall | unknown | OBSERVE-ONLY / no automatic hit | Own UI unknown; checkpoint advance is not a lighting promise |
| fd-wifianalyzer | Object.getClass null producer (L38099) | None for current wall | 不变 | EXACT-OLD-WALL | Unlit likely: unchanged known wall; still review actual frame |
| firefox | Error relocating /data/app/el1/bundle/public/org.mozilla.firefox/android/lib/arm64-v8a/libmegazord.so: __get_h_errno: symbol not found (L39364) | N4-megazord | 过墙 | N4-megazord | Own UI unknown; checkpoint advance is not a lighting promise |
| localsend | java.util.concurrent.ExecutionException: java.lang.UnsatisfiedLinkError: Flutter default-owner namespace configuration failed: 2 (L35868) | N4-owner | 过墙 | N4-owner | Own UI unknown; checkpoint advance is not a lighting promise |
| markor | No first-page blocking wall in outer-reviewed U4 own UI (reviewed-ui-control) | None for current wall | 不变 | UI-PRESERVE + target bind/log capture | Own UI preserved |
| mcdonalds | Caused by: java.lang.RuntimeException: Unable to get provider androidx.startup.InitializationProvider: androidx.startup.StartupException: java.lang.UnsatisfiedLinkError: Flutter default-owner namespace configuration failed: 2 (L35811) | N4-owner | 过墙 | N4-owner | Own UI unknown; checkpoint advance is not a lighting promise |
| mindustry | Caused by: java.lang.UnsatisfiedLinkError: F02-A12-UNSUPPORTED-SYMBOL: dlopen_ns failed for /data/app/el1/bundle/public/io.anuke.mindustry/android/lib/arm64-v8a/libarc.so: Error relocating /data/app/el1/bundle/public/io.anuke.mindustry/android/lib/arm64-v8a/libarc.so: slCreateEngine: symbol not found (L22459) | N4-opensles | 过墙 | N4-opensles | Own UI unknown; checkpoint advance is not a lighting promise |
| newpipe | No first-page blocking wall in outer-reviewed U4 own UI (reviewed-ui-control) | None for current wall | 不变 | UI-PRESERVE + target bind/log capture | Own UI preserved |
| noice | Other Noice APK: no causal fatal, white/no-content despite media_router installation (no-confirmed-causal-wall) | None for current wall | unknown | OBSERVE-ONLY / no automatic hit | Own UI unknown; checkpoint advance is not a lighting promise |
| ooniprobe | No first-page blocking wall in outer-reviewed U4 own UI (reviewed-ui-control) | None for current wall | 不变 | UI-PRESERVE + target bind/log capture | Own UI preserved |
| opencamera | Intent.getIntExtra on null Intent (L32047) | None for current wall | 不变 | EXACT-OLD-WALL | Unlit likely: unchanged known wall; still review actual frame |
| ppsspp | LoadLibrary failed, UnsatifiedLinkError: java.lang.UnsatisfiedLinkError: Flutter default-owner namespace configuration failed: 2 (L41039) | N4-owner | 过墙 | N4-owner | Own UI unknown; checkpoint advance is not a lighting promise |
| subwaysurfers | HOST INPUT: pinned identity changed: apk_sha256 (host-input-not-run) | None for current wall | unknown | OBSERVE-ONLY / no automatic hit | No t20 expected without separately approved input recovery; do not count capture absence as runtime failure |
| termux | No explicit causal fatal; observation-only unlit outcome (no-confirmed-causal-wall) | None for current wall | unknown | OBSERVE-ONLY / no automatic hit | Own UI unknown; checkpoint advance is not a lighting promise |
| toutiao | HOST INPUT: native sidecar is not an AArch64 shared ELF: libcvt.so (host-input-not-run) | None for current wall | unknown | OBSERVE-ONLY / no automatic hit | No t20 expected without separately approved input recovery; do not count capture absence as runtime failure |
| vlc | Onboarding inflater/theme/context failure; resource fix held (L34576) | None for current wall | 不变 | EXACT-OLD-WALL | Unlit likely: unchanged known wall; still review actual frame |
| wikipedia | TagSoup Parser.setProperty missing (T7 held) (L77741) | None for current wall | 不变 | EXACT-OLD-WALL | Unlit likely: unchanged known wall; still review actual frame |
| x | NetworkCapabilities bandwidth method missing; later app graph undefined (T7 held) (L40601) | None for current wall | 不变 | EXACT-OLD-WALL | Unlit likely: unchanged known wall; still review actual frame |

## Post-run scoring protocol (not yet executed)

1. Verify the frozen SHA list and the separate pre-run candidate binding. Preserve all 66 rows, including the three original host-input failures; replaced APKs/sidecars or mixed generations remain unknown for this cohort.
2. Freeze the selected FIRST scheduled attempt per key before reviewing outcomes; retain record/log/t20 hashes. Interrupted attempts may have explicitly indexed continuations, not cherry-picked better repeats. Scope logs by bindApplication package/PID as SCORING does; retain raw line numbers and normalize only timestamps/addresses as appropriate.
3. Score each named checkpoint independently: actual old error on an exercised path = false_positive for a promised advance; positive execution witness past the checkpoint = hit; earlier masking, missing identity/logs, absence-only evidence = unknown. A later wall can coexist with a hit and is separately a missed-wall/false-negative feedback item. Preserve narrower field-contract/ABI advances separately when the operational checkpoint still fails.
4. Aggregate a multi-checkpoint key (Element) as hit only when ALL primary checks pass; any evidenced failed primary promise makes it false_positive, otherwise unknown. Keep per-wall outcomes so metadata and owner never mask each other. Alarm rechecks are separate auxiliary verdicts, not extra lights or a change to the preservation forecast.
5. For unchanged-wall rows, exact old wall reproduced = hit; positive proof of crossing it = false_positive of the unchanged prediction; absence/unlit alone = unknown. For preservation controls, a complete outer-reviewed first t20 decides hit/false_positive; missing screenshot or review = unknown. `unknown` forecasts stay outside the evaluable prediction denominator even if their actual outcome is recorded.
6. Outer reviews APK-matched t20 content. Record actual UI for every key independently from checkpoint score; classify new light, restored old light or protection by baseline identity, never by process survival. AntennaPod/Notes repeats and the unresolved Noice gate are reported separately from first-attempt counts. Both Noice APKs must never become two restoration credits.
7. Write a NEW scoring report (e.g. J6N4-SCORING.md/json), per-key and per-wall hit/false_positive/unknown, plus newly observed missed signatures. Keep denominator counts explicit; do not reinterpret checkpoint accuracy as lighting accuracy. `score_reviewed` supplies a unit-tested decision function for audited summaries, not an automatic raw-log or screenshot judge.

## Reproduce

```sh
python3 benchmark/2026-09-30-u4-sweep/j6n4-predictions/predict.py --out /tmp/j6n4-predictions-new
python3 benchmark/2026-09-30-u4-sweep/j6n4-predictions/predict.py --verify
python3 benchmark/2026-09-30-u4-sweep/j6n4-predictions/test_predictions.py -v
```

Pinned source commits/paths/SHA are listed in `j6n4-predictions/criteria.json`. No future batch measurements were read; no device commands were executed.
