# U5 vs frozen J6/N4 predictions

Previously, disappearance of an error was liable to be called a pass. This score requires the exact frozen positive witness; runtime progress and insufficient instrumentation are reported separately.

Frozen CSV SHA256: `bae8fd74ffdcba3aa5ea05688fcc0c516169f0b0cfcc29d46249c7352fc6a26d` (unchanged).
U5 evidence commit: `d1f27274920ceea074f362082b82911e7f4561e4` in `westlake-harness-bms-deploy`.

The 135-file Git-byte audit is `j6n4-scoring/source-verification.json`; only the results summary uses acceptance annotation commit `7031131ccbfecb105d1aa9fe1b2c151b5a534b8d`. No later repeat records are imported.

## Results

**66 keys: 38 hit / 2 false_positive / 26 unknown.**
Evaluable: **40**, hit rate **95.0%**; unknowns are excluded, not successes.
Primary repair checkpoints (18, because Element has two): `{'unknown': 17, 'false_positive': 1}`.
Preservation controls: **23/24 hit**, AntennaPod first t20 is desktop (already flaky; not a deterministic regression claim).
Unchanged-wall predictions: **15 hit / 1 unknown** (Jitsi now stops at native android_set_abort_message, so no proven crossing of its old iterator wall).
Repair forecasts: **0 fully witnessed hits / 1 false_positive / 16 unknown keys**. Mindustry still fails slCreateEngine relocation.
Unknown forecasts: **9 retained**, including all three host-input failures.
Auxiliary alarm rechecks: **2/2 hit** (fd-android, fd-k9); not additional lights.
Outer first-t20 UI: **24/66 keys** (5cd 12 + 5ea 5 + 61b 7), including restored fd-uhabits; no single-fix causal attribution.

## Why progress is not automatically a frozen hit

- **N4-owner, 11 unknown:** all publish the resident runtime, but no target PID logs the required `[N2-OWNER] ABI global ready`. Post-publication consumer failures are positive partial progress, not the full frozen conjunction. This does not negate the outer operational report of owner progress; it does refuse to change the scoring criterion after the run.
- **N4-egl, 2 unknown:** fd-app and SPD fail in `SystemVibratorManager.getVibratorIds`; neither has an executed EGL initialization witness. OH_RegHook lists are registration, not execution. The outer shorthand “fd-app crossed EGL” is not independently supported by this first U5 attempt under the frozen rule.
- **N4-megazord, 2 unknown:** both browsers fail `libmozglue.so: __gnu_strerror_r`; that is not evidence of libmegazord resolving `__get_h_errno`.
- **J6-metadata, unknown:** Element has metadata count 6 and a later Realm/libz wall, but no self-query value `io.sentry.auto-init=false` as frozen.
- **J6-service-query, unknown:** MusicPlayer logs `MediaLibraryService -> 1` and an actual PlaybackService bind attempt; the forecast required `MediaSessionService` plus successful SessionToken resolution. Preserve this useful partial evidence, not a post-hoc criterion rewrite. The bitmap wall was already known in U4.
- **N4-opensles, false_positive:** Mindustry/libarc still says `slCreateEngine: symbol not found` (34309).

## Missing-signature feedback

7 families / 14 keys, separate from key verdicts and not an exhaustive recall score:

| Signature | Keys | Raw hilog lines |
|---|---|---|
| FlutterJNI.nativeRunBundleAndSnapshotFromLibrary GetLongField with null field ID, not EGLImpl.eglInitialize. | fd-fluffychat, fd-immich, fd-libre, fd-saber | fd-fluffychat:28453,28455; fd-immich:32880,32882; fd-libre:41197,41199; fd-saber:38961,38963 |
| Private libandroid dependency attempts runtime loading; Xpm mmap errno 22 then load failure/FDSAN. Not proof that the library is absent or that musl never searches inherit. | fd-kitchenowl, localsend | fd-kitchenowl:30190,30318; localsend:25830,26180 |
| Realm consumer DT_NEEDED libz.so fails after resident publication; McDonald's also has Xpm/FDSAN. | fd-im-vector-app, mcdonalds | fd-im-vector-app:40538; mcdonalds:37692 |
| SystemVibratorManager synchronization lock null during Activity start; prevents inferring an EGL pass. | fd-app, fd-shatteredpixeldungeon | fd-app:39093,39077; fd-shatteredpixeldungeon:23050,23034 |
| libmozglue.so requires __gnu_strerror_r; different consumer from frozen libmegazord checkpoint. | firefox, fd-fennec_fdroid | fd-fennec_fdroid:45884; firefox:59412 |
| PPSSPP JNI consumer relocation requires android_dlopen_ext. | ppsspp | ppsspp:33885 |
| Jitsi libc++_shared relocation requires android_set_abort_message; masks the predicted restrictions/null-producer wall. | fd-meet | fd-meet:36246 |

N2 never-inherit is a conservative policy, **not** proof of OH musl semantics. Private-load evidence includes Xpm/FDSAN; do not reduce it to an absent-file diagnosis.

## All 66 first attempts

Line numbers below refer to the full raw `source.log` path in JSON, not excerpt-array positions. `j6n4-scoring/evidence/logs/<key>.json` retains exact PID-scoped lines and SHA; source record/t20 SHA are in each JSON row.

| Key | Frozen | Verdict | t20 | Evidence (raw line numbers) |
|---|---|---|---|---|
| aegis | 不变 | hit | own-ui | outer t20 SHA |
| anki | 不变 | hit | own-ui | outer t20 SHA |
| antennapod | 不变 | false_positive | desktop | outer t20 SHA |
| burgerking | 过墙 | unknown | desktop | 31689 |
| fd-AppManager | unknown | unknown | white | outer t20 SHA |
| fd-android | 不变 | hit | own-ui | outer t20 SHA |
| fd-api | 不变 | hit | desktop | 30908 |
| fd-app | 过墙 | unknown | desktop | 39077, 39093 |
| fd-auxio | 不变 | hit | own-ui | outer t20 SHA |
| fd-binaryeye | 不变 | hit | own-ui | outer t20 SHA |
| fd-breezyweather | 不变 | hit | desktop | 44446 |
| fd-calendar | 不变 | hit | own-ui | outer t20 SHA |
| fd-catima | 不变 | hit | desktop | 34317 |
| fd-client | 不变 | hit | desktop | 47506 |
| fd-com-amaze-filemanager | 不变 | hit | own-ui | outer t20 SHA |
| fd-com-kunzisoft-keepass-libre | 不变 | hit | own-ui | outer t20 SHA |
| fd-droidify | 不变 | hit | own-ui | outer t20 SHA |
| fd-etar | 不变 | hit | own-ui | outer t20 SHA |
| fd-feeder | 不变 | hit | desktop | 55783 |
| fd-fennec_fdroid | 过墙 | unknown | desktop | 45884 |
| fd-filemanager | 不变 | hit | own-ui | outer t20 SHA |
| fd-fitness | 不变 | hit | own-ui | outer t20 SHA |
| fd-fluffychat | 过墙 | unknown | desktop | 26330, 28453, 28455 |
| fd-gallery | 不变 | hit | desktop | 56410 |
| fd-im-vector-app | 过墙 | unknown | desktop | 27854, 40536, 40538 |
| fd-immich | 过墙 | unknown | desktop | 27376, 31829, 32880, 32882 |
| fd-k9 | 不变 | hit | own-ui | outer t20 SHA |
| fd-kitchenowl | 过墙 | unknown | desktop | 30189, 30190, 30318 |
| fd-libre | 过墙 | unknown | desktop | 40744, 41197, 41199 |
| fd-libretube | 不变 | hit | desktop | 50600 |
| fd-meet | 不变 | unknown | desktop | 36246 |
| fd-minetest | 不变 | hit | own-ui | outer t20 SHA |
| fd-mobile | unknown | unknown | black | outer t20 SHA |
| fd-mpv | 不变 | hit | own-ui | outer t20 SHA |
| fd-musicplayer | 过墙 | unknown | desktop | 58001, 61468, 78001 |
| fd-netguard | 不变 | hit | own-ui | outer t20 SHA |
| fd-noice | unknown | unknown | white | outer t20 SHA |
| fd-notes | 不变 | hit | own-ui | outer t20 SHA |
| fd-organicmaps | 过墙 | unknown | white | 12474 |
| fd-plus | 不变 | hit | desktop | 45953 |
| fd-reader | 不变 | hit | desktop | 79606 |
| fd-saber | 过墙 | unknown | desktop | 38722, 38961, 38963 |
| fd-seal | unknown | unknown | no-image | native sidecar is not an AArch64 shared ELF: libaria2c.zip.so |
| fd-shatteredpixeldungeon | 过墙 | unknown | desktop | 23034, 23050 |
| fd-stk | 不变 | hit | own-ui | outer t20 SHA |
| fd-tasks | 不变 | hit | own-ui | outer t20 SHA |
| fd-tusky | 不变 | hit | own-ui | outer t20 SHA |
| fd-tutanota | 不变 | hit | desktop | 38425 |
| fd-uhabits | unknown | unknown | own-ui | outer t20 SHA |
| fd-wifianalyzer | 不变 | hit | desktop | 38196 |
| firefox | 过墙 | unknown | desktop | 59412 |
| localsend | 过墙 | unknown | desktop | 25829, 25830, 26180 |
| markor | 不变 | hit | own-ui | outer t20 SHA |
| mcdonalds | 过墙 | unknown | desktop | 37608, 37692 |
| mindustry | 过墙 | false_positive | desktop | 34309 |
| newpipe | 不变 | hit | own-ui | outer t20 SHA |
| noice | unknown | unknown | white | outer t20 SHA |
| ooniprobe | 不变 | hit | own-ui | outer t20 SHA |
| opencamera | 不变 | hit | desktop | 32314 |
| ppsspp | 过墙 | unknown | desktop | 33882, 33885 |
| subwaysurfers | unknown | unknown | no-image | pinned identity changed: apk_sha256 |
| termux | unknown | unknown | white | outer t20 SHA |
| toutiao | unknown | unknown | no-image | native sidecar is not an AArch64 shared ELF: libcvt.so |
| vlc | 不变 | hit | desktop | 61185 |
| wikipedia | 不变 | hit | desktop | 78166 |
| x | 不变 | hit | desktop | 40625 |

## Identity and limitations

- All 66 records match the frozen APK/package/entry/native-sidecar identity; three are declared prelaunch input rejections, not installed successes. 63 have target-PID binding and SHA-verified t20.
- Candidate binding (`inputs.json`, planned 00:46) precedes clicks. Runtime `73ecf422dba2` (119 files), boot `0876029078e2` (36 files), N4-order package `7bc02de7…`, J6 `2488052f…`. No T7c image is included.
- Shard indices select first attempts; Organic Maps retains its original timed interrupted-cleanup trial. The resume contains only remaining keys. Later zero-variable probes are excluded, never cherry-picked.
- “t20” means the scheduled capture, not exactly 20.000 seconds; actual elapsed capture times remain in JSON. Survival/foreground-confirmation flags do not determine UI.
- Unknowns distinguish a missing witness from a failed repair. Strict 0 complete advance hits is **not** a claim that all repairs had no effect. Future forecasts should bind the markers the deployed generation really emits; do not revise this frozen CSV.
- New signatures are feedback only in this task; this report does not claim to have extended a static scanner or deployed fixes.

## Landing dependencies

The baseline master does not yet contain the frozen J6/N4 generator/forecast files. Copy the six existing branch files listed in `j6n4-scoring/landing-dependencies.json` unchanged, then the new scoring artifacts and Rust integration file. Do not replace master lib.rs or recalculate a freeze. The dependency manifest binds the source commit and each SHA.

## Reproduce

```sh
python3 benchmark/2026-09-30-u4-sweep/j6n4-scoring/score.py --verify
python3 benchmark/2026-09-30-u4-sweep/j6n4-scoring/test_scoring.py -v
```

For a fresh full-log collection use `collect.py --source <U5 directory> --out <new directory>`; it rejects changed record/image hashes, non-first selection, and pre-click binding violations. `test_scoring.py` runs offline from vendored evidence. Outer visual sign-off is copied verbatim in `outer-review.json`.
