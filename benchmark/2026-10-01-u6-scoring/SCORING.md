# U6 frozen three-axis scoring

## Evidence and the rule corrected

A warning signature is not the first fatal wall. U6 is scored from the target-PID **termination and its causal chain**, not the earliest provider/SSL exception. A repaired-input observation is not comparable to a frozen input. The outer reviewer explicitly confirmed **strict frozen scoring; list observations separately** on 2026-10-01 at 04:43:51.

- Reference: `../2026-10-01-u6-prospective/PREDICTIONS.csv`, SHA256 **b9a414ed0b70134e2b9dbd54be91dd843e130c5d3020acf905577e17ef419746**. All 25 freeze pins remain unchanged.
- Sources: `WORKSPACES/westlake-harness-bms-deploy/benchmark/2026-10-01-u6-sweep/{5cd,61b,5ea,5ea-resume}`, **22+22+16+6=66** unique records. Retained source paths and SHA256 pins are in `evidence/u6-index.json` and each key excerpt.
- All 66 candidate inventories match **119 runtime + 36 boot files**. All APK hashes match. **Six sidecar inventories differ**; they are non-comparable on **all three axes**, not only the input checkpoint.
- There are **65 timed launches/t20 captures**; Seal was rejected before launch. First attempts are selected without retries. Raw logs are cut off at the bound t20 capture and filtered by target PID; compositor output cannot establish app behavior.
- Screenshots are labeled from **outer ACK(95) 2026-10-01T04:36:43+0800**, not process survival. This report does not claim a new independent visual review.
- `first_fatal.py` determines termination before noise subtraction. The 18-entry noise registry only trims context. Signals 42/35/4, caught coroutine probes and earlier warnings cannot erase or replace the selected causal chain.

## Three independent scores

| Axis | Hit | False positive | Unknown | Not applicable | Judgable hit rate |
|---|---:|---:|---:|---:|---:|
| First wall | 39 | 5 | 22 | 0 | 39/44 = 88.64% |
| Named repair checkpoints | 5 | 0 | 14 | 47 | Not an all-66 accuracy rate |
| t20 own UI | 46 | 1 | 19 | 0 | 46/47 = 97.87% |

The frozen helper calls any confirmed different first wall `false_positive`; this report preserves that vocabulary rather than inventing a new false-negative scoring rule. An actual unpredicted blocker is described below. Unknowns are excluded from judgable denominators, **not turned into hits**.

Outer lighting remains **24 preserved + 3 newly lit = 27**, plus **2 additional flaky-lit** keys (Antennapod, fd-noice), hence 29 observed own-UI captures. New stable lights are **fd-catima, opencamera, fd-feeder**; no outer-observed U5 UI regression. The freeze marks **four** keys flaky (also fd-notes and fd-uhabits), so all four t20 scores remain unknown even though the outer total includes the latter two preserved apps. The two totals answer different questions.

## Incorrect first-wall predictions

| Key | Frozen ordering | Termination-linked observation | Consequence |
|---|---|---|---|
| fd-client | SSLEngine unsupported first; accountManager null later | main_threw L50580 → accountManager null L50595 | First-wall false positive under literal first-causal ordering |
| fd-feeder | CoroutineStart class wall; unlit t20 | Outer-reviewed own UI, no pre-t20 terminal | First-wall and t20 false positives |
| fd-immich | provider verifier first | JNI fatal fid==null L33571 → terminal L33578 | Earlier provider text is not the terminal cause |
| fd-plus | ColorMatrix saturation first | main_threw L75115 → MapInfoLayer null L75130 | Do not relabel an earlier signature as the causal wall |
| wikipedia | SSLSockets class first | tagsoup/XMLReader ICCE L78299 → System.exit L78340 | SSLSockets warning is not this exit's cause |

**fd-client naming caveat:** the frozen ID is compound `sslengine-accountmanager` and its prose mentions both failures. Its explicit *first* prediction puts SSLEngine before accountManager. We use actual ID `accountmanager-null`, do not credit the later-listed fallback as a correct first wall, and disclose this conservative mapping. No frozen text, ID or scoring helper was changed. These observations do **not** prove that the earlier SSL/provider/ColorMatrix problems have been fixed.

## Checkpoint evidence and limits

Positive named-repair witnesses are retained in `REVIEW.json` and the per-key excerpts:

| Key | Named repair | Positive execution evidence |
|---|---|---|
| fd-catima | J7-appwidget, J7-search | L34483 manager allocated; L21385 search installed and queryLocalInterface OK |
| fd-uhabits | J7-appwidget | L24793 manager allocated |
| fd-wifianalyzer | J7-wifi | L38230 WifiManager allocated non-null |
| opencamera | J7-battery | L32178 synthetic ACTION_BATTERY_CHANGED sticky Intent |
| firefox | INPUT-merged | Exact pinned APK, all 18 sidecars verified installed, and target launch binding |

These are initialization/return-path checkpoints, **not full service functionality**. OpenCamera own UI does not demonstrate a working camera. A next wall, absent old error, or own UI alone is never credited as crossing every required repair.

Remaining required-checkpoint rows stay unknown when actual execution of every named operation is not positively witnessed. For example reader reaching tagsoup does not prove every frozen ImageDecoder/TagSoup/Vibrator checkpoint; the allocation message advertising getVibratorIds returning int[0] is not by itself a witnessed invocation of every repaired API.

## Six non-comparable observations (not scored)

| Key | Frozen → actual external sidecars | Retained observation only |
|---|---:|---|
| burgerking | 34 → 0 | Installed/ran; System.exit L46101 linked to libz.so chain L46002; t20 not own UI |
| mcdonalds | 10 → 0 | main_threw L58669 → SplashActivity/DataSourceModuleProvider null L58684; t20 not own UI |
| subwaysurfers | 20 → 0 | SIGABRT L58962 and bound cppcrash abort frames; JNI diagnostic mentions libmediandk; t20 not own UI |
| x | 33 → 0 | main_threw L44937 → application object graph L44952; t20 not own UI |
| fd-seal | 9 → 6 | Host input rejection; no timed launch or t20 |
| toutiao | 138 → 137 | main_threw L70561 → MainActivity Boolean null L70598; outer t20 desktop |

The first four moved external libraries inside merged APKs. Equal APK bytes do not establish equal declared native input inventories. Seal/Toutiao declarations also changed. **No internal/external equivalence waiver is applied.** A future prediction may freeze the new inputs; this score cannot be rewritten retroactively.

## Unresolved causes and nonfatal stalls

- Firefox and Fennec have launch-PID bindings but are absent from the bound t20 process snapshot. This is **process disappearance, cause unknown**. A mozglue error is an observation, not a proven terminal chain. Firefox's independent input checkpoint still passes.
- PPSSPP exits at L35869; the dlopen diagnostic at L34007 is about three seconds earlier, outside the same-TID contiguous two-second cause window. Root stays unknown rather than guessing the first error.
- OrganicMaps has disappeared processes alongside surviving ones and an outer-reviewed white image. This does not prove an app-wide crash cause.
- White: fd-app, fd-AppManager, noice, termux, fd-shatteredpixeldungeon, fd-organicmaps. Black: fd-mobile. These nonfatal visual stalls are not automatically assigned a fatal wall.
- fd-reader and fd-libretube have confirmed tagsoup terminal causes, but frozen first-wall predictions were unknown; those scores remain unknown.
- Non-own images without an outer-specified finer label use `not-own-ui`, not an invented desktop/crash classification.

## Every frozen key

Observed walls and images below remain observations even where strict identity makes the score unknown. Each key links to record/log/image hashes, original source path, PID/TID line witnesses and causal-chain excerpts.

| Key | Frozen first wall | Observed terminal-linked wall | First wall | Checkpoints | t20 prediction / observation | t20 |
|---|---|---|---|---|---|---|
| [aegis](evidence/u6/aegis.json) | none | none; L38440 | hit | not-applicable | own-ui / own-ui | hit |
| [anki](evidence/u6/anki.json) | none | none; L96161 | hit | not-applicable | own-ui / own-ui | hit |
| [antennapod](evidence/u6/antennapod.json) | unknown | none; L48771 | unknown | not-applicable | unknown / own-ui | unknown |
| [burgerking](evidence/u6/burgerking.json) | unknown | realm-libz; L46002,L46101 | unknown | unknown | unknown / not-own-ui | unknown |
| [fd-AppManager](evidence/u6/fd-AppManager.json) | unknown | unknown; no confirmed cause | unknown | not-applicable | unknown / white | unknown |
| [fd-android](evidence/u6/fd-android.json) | none | none; L67131 | hit | not-applicable | own-ui / own-ui | hit |
| [fd-api](evidence/u6/fd-api.json) | appcompat-theme | appcompat-theme; L31103,L31118 | hit | not-applicable | unlit / not-own-ui | hit |
| [fd-app](evidence/u6/fd-app.json) | unknown | unknown; no confirmed cause | unknown | unknown | unknown / white | unknown |
| [fd-auxio](evidence/u6/fd-auxio.json) | none | none; L52760 | hit | not-applicable | own-ui / own-ui | hit |
| [fd-binaryeye](evidence/u6/fd-binaryeye.json) | none | none; L49809 | hit | not-applicable | own-ui / own-ui | hit |
| [fd-breezyweather](evidence/u6/fd-breezyweather.json) | startup-getclass-null | startup-getclass-null; L44625,L44640 | hit | not-applicable | unlit / not-own-ui | hit |
| [fd-calendar](evidence/u6/fd-calendar.json) | none | none; L49140 | hit | not-applicable | own-ui / own-ui | hit |
| [fd-catima](evidence/u6/fd-catima.json) | none | none; L34699 | hit | hit | own-ui / own-ui | hit |
| [fd-client](evidence/u6/fd-client.json) | sslengine-accountmanager | accountmanager-null; L50580,L50595 | false_positive | not-applicable | unlit / not-own-ui | hit |
| [fd-com-amaze-filemanager](evidence/u6/fd-com-amaze-filemanager.json) | none | none; L47988 | hit | not-applicable | own-ui / own-ui | hit |
| [fd-com-kunzisoft-keepass-libre](evidence/u6/fd-com-kunzisoft-keepass-libre.json) | none | none; L31182 | hit | not-applicable | own-ui / own-ui | hit |
| [fd-droidify](evidence/u6/fd-droidify.json) | none | none; L55272 | hit | not-applicable | own-ui / own-ui | hit |
| [fd-etar](evidence/u6/fd-etar.json) | none | none; L34564 | hit | not-applicable | own-ui / own-ui | hit |
| [fd-feeder](evidence/u6/fd-feeder.json) | coroutine-class-loading | none; L57230 | false_positive | unknown | unlit / own-ui | false_positive |
| [fd-fennec_fdroid](evidence/u6/fd-fennec_fdroid.json) | mozglue-strerror | unknown; no confirmed cause | unknown | not-applicable | unlit / not-own-ui | hit |
| [fd-filemanager](evidence/u6/fd-filemanager.json) | none | none; L46209 | hit | not-applicable | own-ui / own-ui | hit |
| [fd-fitness](evidence/u6/fd-fitness.json) | none | none; L59834 | hit | not-applicable | own-ui / own-ui | hit |
| [fd-fluffychat](evidence/u6/fd-fluffychat.json) | flutter-field-id | flutter-field-id; L22684,L22691 | hit | not-applicable | unlit / not-own-ui | hit |
| [fd-gallery](evidence/u6/fd-gallery.json) | mediastore-next-api | mediastore-next-api; L57067,L57068 | hit | unknown | unlit / desktop | hit |
| [fd-im-vector-app](evidence/u6/fd-im-vector-app.json) | realm-libz | realm-libz; L50192,L50193 | hit | not-applicable | unlit / not-own-ui | hit |
| [fd-immich](evidence/u6/fd-immich.json) | immich-verifier | flutter-field-id; L33571,L33578 | false_positive | not-applicable | unlit / not-own-ui | hit |
| [fd-k9](evidence/u6/fd-k9.json) | none | none; L68793 | hit | not-applicable | own-ui / own-ui | hit |
| [fd-kitchenowl](evidence/u6/fd-kitchenowl.json) | private-runtime-reload | private-runtime-reload; L30193,L30223 | hit | not-applicable | unlit / not-own-ui | hit |
| [fd-libre](evidence/u6/fd-libre.json) | flutter-field-id | flutter-field-id; L26706,L26713 | hit | not-applicable | unlit / not-own-ui | hit |
| [fd-libretube](evidence/u6/fd-libretube.json) | unknown | tagsoup-xmlreader; L75297,L75298 | unknown | unknown | unknown / not-own-ui | unknown |
| [fd-meet](evidence/u6/fd-meet.json) | jitsi-native-relocation | jitsi-native-relocation; L36157 | hit | not-applicable | unlit / not-own-ui | hit |
| [fd-minetest](evidence/u6/fd-minetest.json) | none | none; L58661 | hit | not-applicable | own-ui / own-ui | hit |
| [fd-mobile](evidence/u6/fd-mobile.json) | unknown | unknown; no confirmed cause | unknown | not-applicable | unknown / black | unknown |
| [fd-mpv](evidence/u6/fd-mpv.json) | none | none; L32619 | hit | not-applicable | own-ui / own-ui | hit |
| [fd-musicplayer](evidence/u6/fd-musicplayer.json) | bitmap-color-space | bitmap-color-space; L54265,L54266 | hit | not-applicable | unlit / not-own-ui | hit |
| [fd-netguard](evidence/u6/fd-netguard.json) | none | none; L29406 | hit | not-applicable | own-ui / own-ui | hit |
| [fd-noice](evidence/u6/fd-noice.json) | unknown | none; L38679 | unknown | not-applicable | unknown / own-ui | unknown |
| [fd-notes](evidence/u6/fd-notes.json) | unknown | none; L47039 | unknown | not-applicable | unknown / own-ui | unknown |
| [fd-organicmaps](evidence/u6/fd-organicmaps.json) | unknown | unknown; no confirmed cause | unknown | not-applicable | unknown / white | unknown |
| [fd-plus](evidence/u6/fd-plus.json) | colormatrix-saturation | osmand-map-layer-null; L75115,L75130 | false_positive | unknown | unlit / not-own-ui | hit |
| [fd-reader](evidence/u6/fd-reader.json) | unknown | tagsoup-xmlreader; L65239,L65240 | unknown | unknown | unknown / not-own-ui | unknown |
| [fd-saber](evidence/u6/fd-saber.json) | flutter-field-id | flutter-field-id; L38700,L38707 | hit | not-applicable | unlit / not-own-ui | hit |
| [fd-seal](evidence/u6/fd-seal.json) | input-sidecar-rejection | unknown; no confirmed cause | unknown | unknown | unknown / no capture | unknown |
| [fd-shatteredpixeldungeon](evidence/u6/fd-shatteredpixeldungeon.json) | unknown | unknown; no confirmed cause | unknown | unknown | unknown / white | unknown |
| [fd-stk](evidence/u6/fd-stk.json) | none | none; L35397 | hit | not-applicable | own-ui / own-ui | hit |
| [fd-tasks](evidence/u6/fd-tasks.json) | none | none; L56821 | hit | not-applicable | own-ui / own-ui | hit |
| [fd-tusky](evidence/u6/fd-tusky.json) | none | none; L91762 | hit | not-applicable | own-ui / own-ui | hit |
| [fd-tutanota](evidence/u6/fd-tutanota.json) | webview-provider | webview-provider; L38422,L38437 | hit | not-applicable | unlit / not-own-ui | hit |
| [fd-uhabits](evidence/u6/fd-uhabits.json) | unknown | none; L37889 | unknown | hit | unknown / own-ui | unknown |
| [fd-wifianalyzer](evidence/u6/fd-wifianalyzer.json) | country-preference-null | country-preference-null; L38711,L38744 | hit | hit | unlit / not-own-ui | hit |
| [firefox](evidence/u6/firefox.json) | mozglue-strerror | unknown; no confirmed cause | unknown | hit | unlit / not-own-ui | hit |
| [localsend](evidence/u6/localsend.json) | private-runtime-reload | private-runtime-reload; L26566,L26595 | hit | not-applicable | unlit / not-own-ui | hit |
| [markor](evidence/u6/markor.json) | none | none; L40538 | hit | not-applicable | own-ui / own-ui | hit |
| [mcdonalds](evidence/u6/mcdonalds.json) | realm-libz | splash-datasource-null; L58669,L58684 | unknown | unknown | unlit / not-own-ui | unknown |
| [mindustry](evidence/u6/mindustry.json) | opensles-create-engine | opensles-create-engine; L34586,L34609 | hit | not-applicable | unlit / not-own-ui | hit |
| [newpipe](evidence/u6/newpipe.json) | none | none; L58796 | hit | not-applicable | own-ui / own-ui | hit |
| [noice](evidence/u6/noice.json) | unknown | unknown; no confirmed cause | unknown | not-applicable | unknown / white | unknown |
| [ooniprobe](evidence/u6/ooniprobe.json) | none | none; L54918 | hit | not-applicable | own-ui / own-ui | hit |
| [opencamera](evidence/u6/opencamera.json) | none | none; L31749 | hit | hit | own-ui / own-ui | hit |
| [ppsspp](evidence/u6/ppsspp.json) | ppsspp-dlopen-ext | unknown; no confirmed cause | unknown | not-applicable | unlit / not-own-ui | hit |
| [subwaysurfers](evidence/u6/subwaysurfers.json) | unknown | unknown; no confirmed cause | unknown | unknown | unknown / not-own-ui | unknown |
| [termux](evidence/u6/termux.json) | unknown | unknown; no confirmed cause | unknown | not-applicable | unknown / white | unknown |
| [toutiao](evidence/u6/toutiao.json) | input-sidecar-rejection | mainactivity-boolean-null; L70561,L70598 | unknown | unknown | unknown / desktop | unknown |
| [vlc](evidence/u6/vlc.json) | vlc-onboarding-inflate | vlc-onboarding-inflate; L46871,L46945 | hit | not-applicable | unlit / not-own-ui | hit |
| [wikipedia](evidence/u6/wikipedia.json) | ssl-sockets-class | tagsoup-xmlreader; L78299,L78340 | false_positive | unknown | unlit / desktop | hit |
| [x](evidence/u6/x.json) | network-signal-strength | application-object-graph; L44937,L44952 | unknown | unknown | unlit / not-own-ui | unknown |

## Reproduction and delivery

```sh
python3 benchmark/2026-10-01-u6-scoring/measured.py "$U6_ROOT" \
  --review benchmark/2026-10-01-u6-scoring/REVIEW.json > /tmp/u6-rescore.json
python3 benchmark/2026-10-01-u6-scoring/test_measured.py
```

The first command re-reads all raw runs, verifies identities and the prepared-evidence seal, then delegates to the unchanged frozen scoring helper. Its result matches `SCORING.json` excluding the supplemental `outer_lighting` annotation. Offline tests independently replay every compact observation and reject changed hashes/invalid claims. The compact excerpts are not a replacement for full-log causal review.

`SCORING-VALIDATION.json` records current tests, contract scenarios and isolated-master gate exit codes. `results.json` and `validation.json` are explicitly historical **preparation** receipts, not current-source hash attestations. `landing-paths.txt` lists the full delivery and excludes U7 and unrelated lane files. Only the u6-scoring README/DIGEST lines should be extracted from shared files.

