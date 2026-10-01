# Corpus-v2 APK scan v1: U7 baseline

The index-only selection did not prove DEX language/UI frameworks, launch manifests, JNI consumers or native dependencies. This version scans all actual APK bytes and records conditional first-wall candidates; it does not convert references into observed crashes or screenshots.

## Evidence and identities

- Cohort: 100 exact packages and APK SHA/size identities, 100 independent apksigner checks against the indexed signer fingerprints, and 100 LAUNCHER manifests. The original selection files and old apps.json remain unchanged.
- Input manifest: the corrected oc-t4 100-key cv2 manifest, separately pinned in FREEZE.json; compact copy in input-manifest.json.gz.b64. Private APK paths are represented as $WORKSPACES.
- Runtime: U7 T7d + J7b, native N4-order; no N10/J8 overlays. J7b 381110a675fb and T7d stubs d8b2406eb89d. Canonical sigchain/threadguard use route bytes 6d5d5538ff45 / 674d3ef3b9b0, not the different android/lib64 copies in the same native package.
- 100 actual runtime SO/JAR inputs are SHA-bound. JNI declarations: {"exported": 210, "missing": 5, "registered": 2151, "unknown": 3050}. Class-attributed compiled tables establish coverage, not successful RegisterNatives or classloader/namespace resolution. No historical approved JNI exceptions are promoted into this profile.
- Deployment-domain correction: 14 package-only input paths are excluded and JNI attribution rebuilt against deployed hashes. Package inventory alone does not establish active U7 bytes; bind_runtime.py records the exclusion list and expected-run SHA.
- APK facts: {"app_native_candidates": 222, "dex": 136, "jni_calls": 73404, "libraries": 73, "services": 5767}. Full reproducible facts and runtime attribution evidence are compressed text in facts.json.gz.b64 and runtime-profile.json.gz.b64; binary inputs stay outside this repository.

## Rules and prediction limits

- B10 primitives are reused directly: scan_apps.method_scan (service constants/JNI calls), rules85.inspect_method and elf_info, rules_u5_feedback.dex_family, scan_jni compiled ownership, and the existing trampoline manifest/DEX parser. Exact dependency/tool hashes are pinned.
- scan_risks_v3.inspect_method additionally examines bounded startup invokes for WorkManager/Koin/native-loader/context contracts. This projection has no preceding constant/branch instructions and does not claim the full-APK guard-string or argument-propagation coverage of that scanner.
- Manifest classification retains launch aliases, activity counts, Application and provider classes. Application name comes from the XML tree, not dump badging; the latter omits that class and would undercount early startup roots.
- All DEX instructions are examined. Startup roots include launcher/Application/provider lifecycle methods and in-APK superclass methods, with three exact-target call edges. Virtual dispatch, reflection, native entry and later event callbacks remain unknown; no claim of complete reachability is made.
- compact.py counts the complete scan before retaining up to three original coordinates per family/API and startup membership. Full raw scan byte/SHA identity is recorded; counts are not inferred from the retained example count. Native export projection retains every symbol resolving another packaged-library import.
- Native scan retains every packaged ABI member and all AArch64 ELF imports/exports/DT_NEEDED. An import outside the union is a candidate, not a proved relocation failure: OH system providers and private namespaces remain unverified. App JNI export matches do not prove invocation; dynamically registered declarations remain unknown.
- Compose/WebView/GL classifications record definitions and actual invoke instructions separately, including bounded startup invokes. R8-obfuscated/dynamically loaded frameworks can evade these names.
- First-wall and checkpoint are unknown for all 100. Candidate families are ranked by bounded-startup occurrences, not asserted chronological fatal order. t20 hypotheses: {"own-ui": 73, "unknown": 27}. Native/special-rendering or compiled missing/stub startup binding yields unknown; light native-free UI gets a low-confidence static transfer hypothesis. No app is declared actually lit.
- first_fatal.py must score target-PID termination and causal root; checkpoint needs positive execution; t20 requires the first scheduled identity-bound screenshot and outer visual signoff. Do not deduct benign context from actual terminal events.

## Timing and freeze

FREEZE.json registers the CSV SHA and actual freeze timestamp. The outer authorized the cv2 run to start before the freeze if scanning was not finished. All three device windows started at 09:24:47 +0800; this version is therefore explicitly late-frozen, not a held-out pre-run forecast. This lane performed no device actions and did not read cv2 hilog/screenshots to derive these predictions. Later scoring must retain that timing qualification.

## Per-key predictions

| Key | Phase | DEX/native | t20 hypothesis | Startup-ranked first-wall candidates |
|---|---|---|---|---|
| cv2-com-page-bizzle | priority | 1/0 | own-ui | sharedpreferences-null |
| cv2-com-trianguloy-clipboardeditor | priority | 1/0 | own-ui | sharedpreferences-null, context-contract, system-service:clipboard, system-service:input_method, system-service:notification |
| cv2-com-chessclock-android | priority | 1/0 | own-ui | sharedpreferences-null, framework-jni:unknown |
| cv2-com-ath0-rpn | priority | 1/0 | own-ui | sharedpreferences-null, context-contract |
| cv2-com-angrydoughnuts-android-alarmclock | priority | 1/0 | own-ui | secondary-activity-window-session, system-service:alarm, system-service:power |
| cv2-app-varlorg-unote | priority | 1/0 | own-ui | sharedpreferences-null, context-contract, framework-jni:unknown, system-service:uimode |
| cv2-anupam-acrylic | priority | 1/0 | own-ui | unknown; no exact-target startup candidate |
| cv2-com-degeder-yam | priority | 1/0 | unknown | context-contract, webview-startup-or-first-frame |
| cv2-com-cg-lrceditor | priority | 1/0 | own-ui | framework-jni:unknown, context-contract, sharedpreferences-null, system-service:layout_inflater, system-service:location |
| cv2-com-zola-bmi | priority | 1/0 | own-ui | framework-jni:unknown |
| cv2-com-notecryptpro | priority | 1/0 | own-ui | framework-jni:unknown, sharedpreferences-null |
| cv2-com-atr-hiit | priority | 1/0 | own-ui | framework-jni:unknown, sharedpreferences-null, system-service:audio |
| cv2-com-mzhang-cleantimer | priority | 1/0 | own-ui | framework-jni:unknown, sharedpreferences-null |
| cv2-com-alxgnon-postwriter | priority | 1/0 | own-ui | sharedpreferences-null, system-service:vibrator |
| cv2-com-willbsp-habits | priority | 1/0 | unknown | framework-jni:unknown, context-contract, system-service:notification |
| cv2-de-koelle-christian-trickytripper | priority | 1/0 | unknown | framework-jni:unknown, sharedpreferences-null, webview-startup-or-first-frame, context-contract |
| cv2-com-woefe-shoppinglist | priority | 1/0 | own-ui | framework-jni:unknown, in-app-bindservice |
| cv2-com-emmanuelmess-itsdicey | priority | 1/0 | own-ui | framework-jni:unknown, context-contract |
| cv2-com-omgodse-notally | priority | 1/0 | own-ui | framework-jni:unknown, context-contract, sharedpreferences-null, system-service:location, system-service:power |
| cv2-com-ei-bmicalc | priority | 1/0 | own-ui | sharedpreferences-null, framework-jni:unknown, context-contract, system-service:layout_inflater |
| cv2-com-pep1lo-bakerspercentagecalculator | priority | 1/0 | own-ui | framework-jni:unknown, context-contract, system-service:location, system-service:power, system-service:uimode |
| cv2-com-vonglasow-michael-voltagedrop | priority | 1/0 | own-ui | unknown; no exact-target startup candidate |
| cv2-ca-ramzan-delist | priority | 2/0 | own-ui | sharedpreferences-null, context-contract |
| cv2-com-tomatodev-timerdroid | priority | 1/0 | own-ui | framework-jni:unknown |
| cv2-com-darkempire78-opencalculator | priority | 1/0 | own-ui | sharedpreferences-null, framework-jni:unknown, context-contract, velocitytracker-jni, secondary-activity-window-session |
| cv2-com-simonimal-minimalcurconv | priority | 1/0 | own-ui | context-contract, sharedpreferences-null, framework-jni:unknown, secondary-activity-window-session |
| cv2-com-rafapps-simplenotes | priority | 1/0 | own-ui | sharedpreferences-null, context-contract, system-service:input_method |
| cv2-com-aptasystems-dicewarepasswordgenerator | priority | 1/0 | own-ui | sharedpreferences-null, framework-jni:unknown |
| cv2-com-nbossard-packlist | priority | 1/0 | own-ui | framework-jni:unknown, context-contract, sharedpreferences-null |
| cv2-com-lolo-io-onelist | priority | 1/0 | unknown | framework-jni:unknown, sharedpreferences-null, context-contract, system-service:location, system-service:power |
| cv2-biz-binarysolutions-vatcalculator | priority | 1/0 | own-ui | context-contract, sharedpreferences-null, system-service:uimode |
| cv2-com-example-dozencalc | priority | 1/0 | own-ui | framework-jni:unknown |
| cv2-com-benny-pxerstudio | priority | 1/0 | own-ui | framework-jni:unknown, context-contract |
| cv2-com-nathaniel-motus-umlclasseditor | priority | 1/0 | own-ui | framework-jni:unknown, sharedpreferences-null |
| cv2-de-markusfisch-android-libra | priority | 1/0 | own-ui | sharedpreferences-null, context-contract, secondary-activity-window-session |
| cv2-com-deva-knot | priority | 1/0 | own-ui | framework-jni:unknown |
| cv2-com-sunilpaulmathew-snotz | priority | 1/0 | own-ui | framework-jni:unknown, context-contract, sharedpreferences-null, secondary-activity-window-session, system-service:fingerprint |
| cv2-com-maxistar-textpad | priority | 1/0 | own-ui | sharedpreferences-null, context-contract, secondary-activity-window-session, system-service:power |
| cv2-org-secuso-privacyfriendlydicer | priority | 1/0 | own-ui | sharedpreferences-null, framework-jni:unknown, context-contract, secondary-activity-window-session |
| cv2-com-example-ttime | priority | 1/0 | own-ui | framework-jni:unknown |
| cv2-com-nononsenseapps-notepad | priority | 2/0 | own-ui | framework-jni:unknown, context-contract, sharedpreferences-null, system-service:notification, system-service:unknown |
| cv2-com-chancehorizon-just24hoursplus | priority | 1/0 | own-ui | sharedpreferences-null, context-contract, secondary-activity-window-session, window-type-flags |
| cv2-com-codedead-advancedpassgen | priority | 1/0 | own-ui | framework-jni:unknown, context-contract, sharedpreferences-null, secondary-activity-window-session, system-service:location |
| cv2-com-bytehamster-flowitgame | priority | 1/0 | unknown | sharedpreferences-null, framework-jni:unknown, context-contract, gl-startup-or-first-frame |
| cv2-com-maltaisn-notes-sync | priority | 1/0 | own-ui | framework-jni:unknown, context-contract, sharedpreferences-null, system-service:unknown, system-service:location |
| cv2-com-chess-clock | priority | 1/0 | own-ui | context-contract, sharedpreferences-null, window-type-flags, system-service:audio, system-service:window |
| cv2-com-pvcodes-debtcalc | priority | 1/0 | own-ui | framework-jni:unknown |
| cv2-com-paultirk-yatoo | priority | 2/0 | own-ui | context-contract |
| cv2-com-codedead-deadhash | priority | 1/0 | own-ui | sharedpreferences-null, context-contract |
| cv2-com-nicue-onetwo | priority | 1/0 | own-ui | framework-jni:unknown, context-contract, sharedpreferences-null, system-service:activity, system-service:location |
| cv2-ca-vaults-randomlydie | priority | 1/0 | own-ui | context-contract |
| cv2-com-nima-taskmanager | priority | 1/0 | unknown | context-contract |
| cv2-com-asdoi-timetable | priority | 2/0 | own-ui | sharedpreferences-null, context-contract, system-service:alarm, system-service:notification, system-service:unknown |
| cv2-com-harr1424-listmaker | priority | 1/0 | own-ui | sharedpreferences-null, context-contract, system-service:layout_inflater |
| cv2-com-wattwurm-toodoo | priority | 1/0 | own-ui | context-contract, framework-jni:unknown |
| cv2-org-secuso-privacyfriendlypin | priority | 1/0 | own-ui | framework-jni:unknown, secondary-activity-window-session |
| cv2-org-secuso-privacyfriendlyyahtzeedicer | priority | 1/0 | own-ui | framework-jni:unknown, context-contract, secondary-activity-window-session |
| cv2-com-wbpxre150-shoppinglist | priority | 1/0 | own-ui | context-contract, framework-jni:unknown, velocitytracker-jni |
| cv2-org-secuso-privacyfriendlysudoku | priority | 2/0 | own-ui | context-contract, framework-jni:unknown, secondary-activity-window-session, system-service:notification |
| cv2-com-groce-app | priority | 2/0 | own-ui | sharedpreferences-null, context-contract, framework-jni:unknown |
| cv2-org-secuso-privacyfriendlybattleship | priority | 1/0 | own-ui | sharedpreferences-null, context-contract, framework-jni:unknown, secondary-activity-window-session |
| cv2-com-rootminusone8004-bazarnote | priority | 2/0 | own-ui | context-contract |
| cv2-com-pocket-plan-j7-003 | priority | 3/0 | own-ui | sharedpreferences-null, context-contract, framework-jni:unknown, system-service:alarm, system-service:input_method |
| cv2-org-secuso-privacyfriendlyminesweeper | priority | 2/0 | own-ui | sharedpreferences-null, context-contract, framework-jni:unknown, secondary-activity-window-session |
| cv2-org-secuso-privacyfriendlyrecknoningskills | priority | 1/0 | own-ui | framework-jni:unknown, secondary-activity-window-session |
| cv2-org-secuso-privacyfriendlyruler | priority | 1/0 | own-ui | context-contract, framework-jni:unknown, secondary-activity-window-session |
| cv2-org-secuso-privacyfriendlydame | priority | 2/0 | own-ui | framework-jni:unknown, secondary-activity-window-session |
| cv2-org-secuso-privacyfriendlypausinghealthily | priority | 3/0 | own-ui | sharedpreferences-null, context-contract, framework-jni:unknown, secondary-activity-window-session, system-service:notification |
| cv2-com-knirirr-beecount | priority | 2/0 | unknown | sharedpreferences-null, webview-startup-or-first-frame, context-contract, framework-jni:unknown |
| cv2-org-secuso-privacyfriendlyludo | priority | 1/0 | own-ui | framework-jni:unknown, secondary-activity-window-session |
| cv2-org-secuso-privacyfriendlyintervaltimer | priority | 3/0 | own-ui | framework-jni:unknown, secondary-activity-window-session |
| cv2-com-better-alarm | priority | 2/0 | own-ui | koin-init-or-use, context-contract, framework-jni:unknown |
| cv2-org-secuso-privacyfriendlypaindiary | priority | 3/0 | own-ui | secondary-activity-window-session |
| cv2-org-secuso-privacyfriendlytapemeasure | priority | 3/0 | own-ui | secondary-activity-window-session |
| cv2-org-secuso-privacyfriendlycircuittraining | priority | 3/0 | own-ui | sharedpreferences-null, context-contract, secondary-activity-window-session, framework-jni:unknown |
| cv2-org-secuso-privacyfriendlypasswordgenerator | priority | 3/0 | own-ui | secondary-activity-window-session |
| cv2-org-secuso-privacyfriendlynotes | priority | 3/0 | own-ui | sharedpreferences-null, context-contract, secondary-activity-window-session |
| cv2-org-secuso-privacyfriendlymemory | priority | 1/0 | own-ui | secondary-activity-window-session |
| cv2-org-secuso-privacyfriendlytodolist | priority | 3/0 | own-ui | sharedpreferences-null, context-contract, workmanager-init-or-use, framework-jni:unknown, secondary-activity-window-session |
| cv2-org-secuso-privacyfriendly2048 | priority | 3/0 | own-ui | sharedpreferences-null, context-contract, secondary-activity-window-session |
| cv2-org-quicksc0p3r-simplecounter | compose | 1/0 | unknown | framework-jni:unknown, context-contract |
| cv2-com-goofwear-file85toolkit | compose | 1/4 | unknown | framework-jni:unknown, context-contract, system-service:location, system-service:power, system-service:uimode |
| cv2-com-git-itdolan31-crystalpad | compose | 1/8 | unknown | framework-jni:unknown, context-contract, secondary-activity-window-session, system-service:unknown |
| cv2-com-kaajjo-libresudoku | compose | 1/8 | unknown | framework-jni:unknown, context-contract, system-service:unknown, system-service:location, system-service:power |
| cv2-io-github-jdanders-dropcount | compose | 2/4 | unknown | context-contract, framework-jni:unknown |
| cv2-com-paperknifeplus-app | compose | 1/0 | unknown | context-contract, framework-jni:unknown |
| cv2-com-frequent-habits | compose | 3/4 | unknown | context-contract |
| cv2-com-edward-studytracker | compose | 2/0 | unknown | context-contract |
| cv2-com-lcdcode-moodcairns | compose | 1/12 | unknown | framework-jni:unknown, context-contract, sharedpreferences-null, system-service:unknown, window-type-flags |
| cv2-com-armanmaurya-archiv | compose | 1/16 | unknown | framework-jni:unknown, context-contract, system-service:location, system-service:power, system-service:uimode |
| cv2-de-markusfisch-android-shadereditor | gl | 1/8 | unknown | sharedpreferences-null, framework-jni:unknown, context-contract, secondary-activity-window-session, system-service:location |
| cv2-com-ruesga-android-wallpapers-photophase | gl | 1/5 | unknown | context-contract, system-service:notification |
| cv2-org-linaro-glmark2 | gl | 1/4 | unknown | native-load, native-load-call |
| cv2-org-andresoviedo-dddmodel2 | gl | 2/0 | unknown | context-contract |
| cv2-timur-webrtc-check | webview | 1/0 | unknown | webview-startup-or-first-frame, framework-jni:unknown, context-contract |
| cv2-dev-obfusk-jiten-webview | webview | 1/0 | unknown | webview-startup-or-first-frame, framework-jni:unknown, sharedpreferences-null |
| cv2-com-github-dfa-diaspora-android | webview | 1/0 | unknown | framework-jni:unknown, context-contract, sharedpreferences-null, webview-startup-or-first-frame, secondary-activity-window-session |
| cv2-eu-dfdx-jslab | webview | 1/0 | unknown | sharedpreferences-null, context-contract, framework-jni:unknown |
| cv2-com-caniwebview-android | webview | 1/0 | unknown | context-contract, framework-jni:unknown |
| cv2-com-stoutner-privacybrowser-standard | webview | 1/0 | unknown | sharedpreferences-null, framework-jni:unknown, context-contract, webview-startup-or-first-frame, system-service:unknown |

## Replay and handoff

`python3 benchmark/2026-10-01-corpus-v2/apk-scan-v1/test_scan.py -v` exercises identity rejection, both apksigner output formats, Application XML roots, JNI uncertainty, incomplete-freeze refusal and exact artifact replay.
`report.py --format csv` replays PREDICTIONS.csv without APKs or network. For a new scan, run scan.py --output <scratch> --jobs 3; never overwrite this freeze. validation.json records the exact scoped master overlay and gate exit codes.
landing-paths.txt lists only this handoff. Shared README/DIGEST additions are exact lines in documentation.json. Input preparation/deployment remains with oc-t4; screenshots remain with the outer.
