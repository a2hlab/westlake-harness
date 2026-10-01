# u10 vs u9 first-wall diff (OBSERVATION)

**u10 is UNSIGNED — failed-candidate observation.** verdict = process survival at t20 (alive/dead), NOT lit/white (screenshots are ground truth, read by the outer ring).

classes: unchanged | moved (U9 wall -> new U10 wall) | cleared? (U9 wall not hit; confirm lit) | not_run (not reached this window) | regression? (ok U9 -> fatal U10) | ran-ok? (ran, no fatal)

counts: {'ran-ok?': 33, 'moved': 9, 'not_run': 28, 'cleared?': 7, 'unchanged': 7, 'regression?': 2}

## Focus keys

| Key | Class | U10 verdict | Detail |
|---|---|---|---|
| toutiao | cleared? | alive@t20 | u9=java:NullPointerException -> u10 no-fatal alive@t20 (U9 wall not hit; confirm lit by screenshot) |
| fd-meet | unchanged | dead@t20 | java:UnsatisfiedLinkError |
| fd-fennec_fdroid | unchanged | dead@t20 | native:signal |
| fd-tutanota | cleared? | alive@t20 | u9=java:NullPointerException -> u10 no-fatal alive@t20 (U9 wall not hit; confirm lit by screenshot) |
| cv2-com-nbossard-packlist | not_run | not_run | u9=java:ClassNotFoundException; not run in u10 window |
| opencamera | regression? | dead@t20 | ok in u9 -> u10 java:UnsatisfiedLinkError: [CHILD_CK] J_invokeStaticMain_main_threw: java.lang.UnsatisfiedLinkErr |
| fd-organicmaps | regression? | dead@t20 | ok in u9 -> u10 java:NullPointerException: Caused by: java.lang.NullPointerException: Attempt to invoke virtual m |
| fd-app | moved | dead@t20 | no-fatal () -> java:UnsatisfiedLinkError ([CHILD_CK] J_invokeStaticMain_main_threw: jav) |
| fd-plus | moved | dead@t20 | java:IllegalStateException ([CHILD_CK] J_invokeStaticMain_main_threw: jav) -> java:NullPointerException (Caused by: java.lang.NullPointerException: At) |
| firefox | not_run | not_run | u9=native:signal; not run in u10 window |
| wikipedia | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |

## All keys

| Key | Class | U10 verdict | Detail |
|---|---|---|---|
| aegis | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| anki | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| antennapod | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| burgerking | moved | dead@t20 | no-fatal () -> java:UnsatisfiedLinkError (10-01 23:35:21.051 15054 15078 W C00f00/SoLoa) |
| cv2-ca-vaults-randomlydie | not_run | not_run | u9=no-fatal; not run in u10 window |
| cv2-com-bytehamster-flowitgame | not_run | not_run | u9=no-fatal; not run in u10 window |
| cv2-com-chessclock-android | not_run | not_run | u9=java:UnsatisfiedLinkError; not run in u10 window |
| cv2-com-degeder-yam | not_run | not_run | u9=no-fatal; not run in u10 window |
| cv2-com-emmanuelmess-itsdicey | not_run | not_run | u9=no-fatal; not run in u10 window |
| cv2-com-frequent-habits | not_run | not_run | u9=no-fatal; not run in u10 window |
| cv2-com-kaajjo-libresudoku | not_run | not_run | u9=no-fatal; not run in u10 window |
| cv2-com-lcdcode-moodcairns | not_run | not_run | u9=java:AEADBadTagException; not run in u10 window |
| cv2-com-nbossard-packlist | not_run | not_run | u9=java:ClassNotFoundException; not run in u10 window |
| cv2-com-nononsenseapps-notepad | not_run | not_run | u9=java:NullPointerException; not run in u10 window |
| cv2-com-paultirk-yatoo | not_run | not_run | u9=no-fatal; not run in u10 window |
| cv2-com-stoutner-privacybrowser-standard | not_run | not_run | u9=java:NullPointerException; not run in u10 window |
| cv2-com-trianguloy-clipboardeditor | not_run | not_run | u9=java:NoSuchMethodError; not run in u10 window |
| cv2-dev-obfusk-jiten-webview | not_run | not_run | u9=no-fatal; not run in u10 window |
| cv2-org-andresoviedo-dddmodel2 | not_run | not_run | u9=no-fatal; not run in u10 window |
| cv2-org-linaro-glmark2 | not_run | not_run | u9=native:signal; not run in u10 window |
| cv2-org-secuso-privacyfriendlyyahtzeedicer | not_run | not_run | u9=java:PackageManager$NameNotFoundException; not run in u10 window |
| cv2-timur-webrtc-check | not_run | not_run | u9=no-fatal; not run in u10 window |
| fd-AppManager | cleared? | alive@t20 | u9=no-fatal -> u10 no-fatal alive@t20 (U9 wall not hit; confirm lit by screenshot) |
| fd-android | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-api | unchanged | dead@t20 | java:IllegalStateException |
| fd-app | moved | dead@t20 | no-fatal () -> java:UnsatisfiedLinkError ([CHILD_CK] J_invokeStaticMain_main_threw: jav) |
| fd-auxio | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-binaryeye | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-breezyweather | unchanged | dead@t20 | java:NullPointerException |
| fd-calendar | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-catima | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-client | not_run | not_run | u9=java:NullPointerException; not run in u10 window |
| fd-com-amaze-filemanager | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-com-kunzisoft-keepass-libre | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-droidify | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-etar | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-feeder | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-fennec_fdroid | unchanged | dead@t20 | native:signal |
| fd-filemanager | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-fitness | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-fluffychat | moved | dead@t20 | native:signal () -> java:UnsatisfiedLinkError (Caused by: java.lang.UnsatisfiedLinkError: Fl) |
| fd-gallery | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-im-vector-app | unchanged | dead@t20 | java:UnsatisfiedLinkError |
| fd-immich | moved | dead@t20 | native:signal () -> java:UnsatisfiedLinkError (Caused by: java.lang.UnsatisfiedLinkError: Fl) |
| fd-k9 | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-kitchenowl | moved | dead@t20 | native:signal () -> java:UnsatisfiedLinkError (Caused by: java.lang.UnsatisfiedLinkError: Fl) |
| fd-libre | moved | dead@t20 | native:signal () -> java:UnsatisfiedLinkError (Caused by: java.lang.UnsatisfiedLinkError: Fl) |
| fd-libretube | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-meet | unchanged | dead@t20 | java:UnsatisfiedLinkError |
| fd-minetest | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-mobile | cleared? | alive@t20 | u9=no-fatal -> u10 no-fatal alive@t20 (U9 wall not hit; confirm lit by screenshot) |
| fd-mpv | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-musicplayer | unchanged | dead@t20 | java:IllegalArgumentException |
| fd-netguard | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-noice | cleared? | alive@t20 | u9=no-fatal -> u10 no-fatal alive@t20 (U9 wall not hit; confirm lit by screenshot) |
| fd-notes | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-organicmaps | regression? | dead@t20 | ok in u9 -> u10 java:NullPointerException: Caused by: java.lang.NullPointerException: Attempt to invoke virtual m |
| fd-plus | moved | dead@t20 | java:IllegalStateException ([CHILD_CK] J_invokeStaticMain_main_threw: jav) -> java:NullPointerException (Caused by: java.lang.NullPointerException: At) |
| fd-reader | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-saber | moved | dead@t20 | native:signal () -> java:UnsatisfiedLinkError (Caused by: java.lang.UnsatisfiedLinkError: Fl) |
| fd-seal | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-shatteredpixeldungeon | moved | dead@t20 | no-fatal () -> java:UnsatisfiedLinkError ([CHILD_CK] J_invokeStaticMain_main_threw: jav) |
| fd-stk | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-tasks | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-tusky | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| fd-tutanota | cleared? | alive@t20 | u9=java:NullPointerException -> u10 no-fatal alive@t20 (U9 wall not hit; confirm lit by screenshot) |
| fd-uhabits | cleared? | alive@t20 | u9=no-fatal -> u10 no-fatal alive@t20 (U9 wall not hit; confirm lit by screenshot) |
| fd-wifianalyzer | not_run | not_run | u9=java:NullPointerException; not run in u10 window |
| firefox | not_run | not_run | u9=native:signal; not run in u10 window |
| helloworld | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| localsend | not_run | not_run | u9=native:signal; not run in u10 window |
| markor | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| mcdonalds | not_run | not_run | u9=java:NullPointerException; not run in u10 window |
| mindustry | not_run | not_run | u9=java:ExceptionInInitializerError; not run in u10 window |
| newpipe | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| noice | not_run | not_run | u9=no-fatal; not run in u10 window |
| ooniprobe | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| opencamera | regression? | dead@t20 | ok in u9 -> u10 java:UnsatisfiedLinkError: [CHILD_CK] J_invokeStaticMain_main_threw: java.lang.UnsatisfiedLinkErr |
| ppsspp | not_run | not_run | u9=no-fatal; not run in u10 window |
| subwaysurfers | unchanged | dead@t20 | native:signal |
| termux | cleared? | alive@t20 | u9=no-fatal -> u10 no-fatal alive@t20 (U9 wall not hit; confirm lit by screenshot) |
| toutiao | cleared? | alive@t20 | u9=java:NullPointerException -> u10 no-fatal alive@t20 (U9 wall not hit; confirm lit by screenshot) |
| vlc | not_run | not_run | u9=no-fatal; not run in u10 window |
| wikipedia | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
| x | not_run | not_run | u9=java:NullPointerException; not run in u10 window |
| zigzag | ran-ok? | alive@t20 | ran u10 alive@t20, no fatal (lit U9 -> likely still ok; confirm screenshot) |
