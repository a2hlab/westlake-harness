# Open-gap leaderboard — 100 apps (static)

Stacks: android-jvm 68, native-engine 8, flutter 8, react-native 7, libgdx/arc 3, unity-il2cpp 2, gecko 2, webview-hybrid 2

| # apps | gap | verdicts | class | effort | OH touchpoint | shim |
|---:|---|---|---|---|---|---|
| 100 | **java:App framework** | hollow-candidate×41, missing×59 | C9 | verify | ability_runtime | check each hollow body against AOSP |
| 100 | **java:Java library** | hollow-candidate×49, missing×51 | C9 | verify | none (library code inside Westlake) | check each hollow body against AOSP |
| 100 | **load:runtime-silent-success** | unresolved×100 | C3 | verify | Runtime.nativeLoad in the runtime's own OpenJDK stub | compare the staged library's methods against the tables the runtime's  |
| 99 | **java:Other** | probe-only×55, missing×41, hollow-candidate×3 | C8 | verify | unmapped | confirm the probed class should (not) exist on this platform |
| 99 | **java:Views & windows** | hollow-candidate×27, missing×72 | C9 | verify | window_manager / render_service | check each hollow body against AOSP |
| 97 | **java:Content & intents** | hollow-candidate×96, missing×1 | C9 | verify | ability_runtime | check each hollow body against AOSP |
| 97 | **java:Graphics** | hollow-candidate×80, missing×17 | C9 | verify | render_service / graphic_2d | check each hollow body against AOSP |
| 97 | **java:Other Android** | hollow-candidate×45, missing×52 | C9 | verify | unmapped | check each hollow body against AOSP |
| 97 | **pm:call:resolveContentProvider** | stub×97 | C9 | M | none | resolve against the APK's intent filters |
| 97 | pm:providers | unverified×97 | CU | verify | none | install every main-process provider in initOrder before Application.on |
| 97 | svc:accessibility | inert×97 | C5 | none | unmapped | none: the manager is written to run without its service |
| 96 | **svc:notification** | hollow×96 | C9 | S | notification (ANS) | replace the hollow binder with an implementation over notification (AN |
| 96 | java:Widgets | hollow-candidate×96 | C9 | verify | none (library code inside Westlake) | check each hollow body against AOSP |
| 93 | **svc:audio** | hollow×93 | C9 | S | audio_framework | replace the hollow binder with an implementation over audio_framework |
| 92 | **pm:call:getPackagesForUid** | stub×92 | C9 | S | bundle_framework (for other packages) | answer from the APK/package state |
| 92 | **pm:call:queryIntentActivityOptions** | stub×92 | C9 | M | none | resolve against the APK's intent filters |
| 91 | **pm:call:setComponentEnabledSetting** | stub×91 | C9 | S | none | answer from the APK/package state |
| 89 | **pm:call:getComponentEnabledSetting** | stub×89 | C9 | S | none | answer from the APK/package state |
| 88 | **pm:call:queryIntentContentProviders** | stub×88 | C9 | M | none | resolve against the APK's intent filters |
| 86 | **svc:textclassification** | unresolved×86 | CU | verify | unmapped | trace the helper's binder; then treat as null, inert or supplied |
| 81 | **java:OS services** | hollow-candidate×40, missing×40, probe-only×1 | C9 | verify | various system abilities | check each hollow body against AOSP |
| 81 | **pm:call:queryIntentServices** | stub×81 | C9 | M | none | resolve against the APK's intent filters |
| 80 | **svc:jobscheduler** | hollow×80 | C9 | M | resourceschedule/work_scheduler | replace the hollow binder with an implementation over resourceschedule |
| 79 | **svc:user** | strict×79 | C9 | S | account/os_account | answer the methods callers use with Android's value for this device; a |
| 78 | svc:vibrator | inert×78 | C4 | S | sensors/miscdevice | Android Vibrator facade over sensors/miscdevice |
| 71 | **pm:call:queryBroadcastReceivers** | stub×71 | C9 | M | none | resolve against the APK's intent filters |
| 68 | **svc:keyguard** | null×68 | C4 | S | theme/screenlock | Android KeyguardManager facade over theme/screenlock |
| 68 | **wv:renderer-process** | missing×68 | C4 | L | process spawn (appspawn): an isolated Android service process with its own sandbox | host the renderer: spawn an isolated child and bind Chromium's Sandbox |
| 68 | svc:phone | inert×68 | C4 | M | telephony/core_service | Android TelephonyManager facade over telephony/core_service |
| 67 | svc:autofill | inert×67 | C5 | none | unmapped | none: the manager is written to run without its service |
| 67 | svc:sensor | inert×67 | C4 | M | sensors | Android SensorManager facade over sensors |
| 63 | **svc:wifi** | null×63 | C4 | S | communication/wifi | Android WifiManager facade over communication/wifi |
| 60 | **java:Networking** | hollow-candidate×53, missing×7 | C9 | verify | netmanager | check each hollow body against AOSP |
| 60 | **pm:call:resolveService** | stub×60 | C9 | M | none | resolve against the APK's intent filters |
| 59 | java:WebView | hollow-candidate×59 | C9 | verify | web (ArkWeb) or bundled Chromium | check each hollow body against AOSP |
| 58 | **policy:lnk_file** | denied×58 | C5 | M | SELinux u:r:normal_hap:s0 → u:object_r:appdat:s0 | neverallow'd for hap_domain on app data; needs a libc-level emulation  |
| 56 | **java:Java extensions** | missing×48, hollow-candidate×6, probe-only×2 | C1/C5 | S | none (library code inside Westlake) | port from AOSP, or confirm the caller tolerates absence |
| 56 | **java:Media store** | missing×15, hollow-candidate×41 | C4 | S | multimedia/media_library | implement the members over multimedia/media_library |
| 54 | **pm:call:getInstallerPackageName** | stub×54 | C9 | S | bundle_framework (for other packages) | answer from the APK/package state |
| 51 | **sym:bionic-private (not in the NDK)** | missing×51 | C1/C2 | S | OH musl / system libraries | bionic-ABI shim: forward or translate to musl |
| 49 | svc:camera | inert×49 | C4 | M | multimedia/camera_framework | Android CameraManager facade over multimedia/camera_framework |
| 48 | **svc:captioning** | unresolved×48 | CU | verify | unmapped | trace the helper's binder; then treat as null, inert or supplied |
| 46 | **svc:media_metrics** | null×46 | C5 | S | unmapped | truthful local manager (feature absent) |
| 45 | **java:Media** | missing×13, hollow-candidate×32 | C4 | S | multimedia | implement the members over multimedia |
| 45 | **pm:call:getInstallSourceInfo** | stub×45 | C9 | S | none | answer from the APK/package state |
| 45 | svc:download | inert×45 | C4 | S | miscservices/download_server | Android DownloadManager facade over miscservices/download_server |
| 43 | **pm:call:getNameForUid** | stub×43 | C9 | S | none | answer from the APK/package state |
| 42 | **dep:google-play-services** | absent×42 | C5 | M | none: no Google services on OH | decide per feature: truthful 'unavailable' result, or an OH-backed rep |
| 42 | **pm:multiprocess** | missing×42 | C4 | L | appspawn (second process) | spawn and route secondary Android processes |
| 41 | **svc:biometric** | null×41 | C5 | S | unmapped | truthful local manager (feature absent) |
| 40 | java:Camera | hollow-candidate×40 | C9 | verify | multimedia/camera_framework | check each hollow body against AOSP |
| 39 | **svc:fingerprint** | null×39 | C5 | S | unmapped | truthful local manager (feature absent) |
| 38 | dep:firebase-component-discovery:ComponentDiscoveryService | partial×38 | C5 | verify | none: no Google services on OH | component discovery is local (see pm:component-metadata); GMS-backed c |
| 34 | **svc:bluetooth** | unresolved×34 | CU | verify | communication/bluetooth | trace the helper's binder; then treat as null, inert or supplied |
| 33 | **pm:call:getSystemAvailableFeatures** | stub×33 | C9 | S | none | answer from the APK/package state |
| 32 | **pm:call:getReceiverInfo** | stub×32 | C9 | S | none | answer from the APK/package state |
| 31 | **load:shadowed-by-board** | missing×31 | C3 | XS | OH dynamic linker search order: /system/lib64/libc++_shared.so comes before the app's library directory | load these 20 libraries in the isolated Android namespace so DT_NEEDED |
| 31 | svc:credential | inert×31 | C5 | none | unmapped | none: the manager is written to run without its service |
| 30 | **svc:vibrator_manager** | unresolved×30 | CU | verify | unmapped | trace the helper's binder; then treat as null, inert or supplied |
| 29 | **svc:print** | unresolved×29 | CU | verify | print_service | trace the helper's binder; then treat as null, inert or supplied |

## Ignored maps outside corpus

`fd-k9`

Bold: at least one app has a hard verdict (missing, null, strict, denied, stub, hollow, unresolved).

## Most widely referenced absent Java members

| # apps | member |
|---:|---|
