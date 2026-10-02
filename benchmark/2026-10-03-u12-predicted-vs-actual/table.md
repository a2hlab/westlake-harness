| key | predicted (by) | actual | U10.1T8 first fatal → U12 first fatal | screen: outer / pair-auto / cc-t3 read (unsigned) | notes |
|---|---|---|---|---|---|
| burgerking | yes (disappeared) | **moved** terminal+wall | process-disappeared: process disappeared without cause → signal: DFX_SignalHandler :: signo(11), si_code(1), pid(6791), tid(6988). | - / w4:same | moved: libNitroMmkv dlopen (libz) gone; now SIGSEGV in librsa_bridge (Go cgo x_cgo_sigaction) on pool-4-thread-1 |
| cv2-com-kaajjo-libresudoku | yes (disappeared) | **moved** terminal | process-disappeared: process disappeared without cause → no-observed-termination:  | - / w4:different / own UI (LibreSudoku start screen: board + 开始 + settings) | moved: no termination, alive at t20 |
| cv2-com-lcdcode-moodcairns | yes (java_fix) | **moved** terminal | java-cause: javax.crypto.AEADBadTagException: mac check in GCM failed → java-cause: java.lang.IllegalStateException: GCM cipher needs to be initialised | - / w4:same | moved INTO OUR FIX: IllegalStateException "GCM cipher needs to be initialised" at adapter.core.GcmDefaultNonce$Spi.engineDoFinal -- see README (GcmDefaultNonce defect) |
| cv2-com-nbossard-packlist | yes (java_fix) | **moved** terminal+wall | java-cause: java.lang.ClassNotFoundException: com.android.internal.util.Predicate → no-observed-termination:  | - / w4:different / own UI (empty trip list, title = class name: labelRes wall) |  |
| cv2-com-nononsenseapps-notepad | yes (java_fix) | **moved** terminal | java-cause: java.lang.NullPointerException: Attempt to invoke interface method 'boolean android.database.Cursor.moveToFirs → no-observed-termination:  | - / w4:different / own UI (task list "欢迎! 打开这个即可开始") |  |
| cv2-com-trianguloy-clipboardeditor | yes (java_fix) | **moved** terminal | java-cause: java.lang.NullPointerException: Attempt to invoke virtual method 'java.lang.String android.telephony.Telephony → no-observed-termination:  | - / w4:different / own UI (clipboard editor panel, top-left, on white) |  |
| fd-breezyweather | yes (icu) | **moved** terminal | java-cause: java.lang.NullPointerException: Attempt to invoke virtual method 'java.lang.Class java.lang.Object.getClass()' → unknown:  | - / w3:same | moved to next wall: lateinit property weatherView has not been initialized (app-level, after the ICU fix) |
| fd-client | yes (java_fix) | **moved** terminal | java-cause: java.lang.NullPointerException: Attempt to invoke interface method 'boolean android.database.Cursor.moveToFirs → no-observed-termination:  | w4:lit (new): own onboarding page; ACK 2026-10-03T00:58:37 (U10.1T8: dead) / w4:different |  |
| fd-wifianalyzer | yes (icu) | **moved** terminal+wall | java-cause: java.lang.NullPointerException: Attempt to invoke virtual method 'java.lang.Class java.lang.Object.getClass()' → java-cause: java.lang.NoSuchMethodError: No virtual method isScanThrottleEnabled()Z in class Landroid/net/wifi/WifiManager (wall: [CHILD_CK] J_invokeStaticMain_main_threw: java.lang.NoSuchMethodError: No virtual method isScanThrottleEnabled) | - / w4:same | moved to next wall: NoSuchMethodError WifiManager.isScanThrottleEnabled() |
| x | yes (java_fix;n11h_family) | **moved** terminal+wall | java-cause: java.lang.IllegalStateException: The application object graph is not defined. Is your Application class callin → java-cause: java.lang.NullPointerException: Attempt to invoke interface method 'void com.android.internal.telephony.ITelep (wall: F02-A12-UNSUPPORTED-SYMBOL: dlopen_ns failed for /data/app/el1/bundle/public/com.twitter.android/android/lib/a) | - / w4:no-window / white (no window) | moved to next wall: NPE ITelephonyRegistry.listenWithEventList (fixed in U13 JAR v2 506abe23) |
| cv2-org-linaro-glmark2 | yes (sigabrt) | **same**  | signal: DFX_SignalHandler :: signo(6), si_code(-6), pid(3139), tid(3163). | - / w4:same |  |
| fd-fennec_fdroid | yes (disappeared) | **same**  | process-disappeared: process disappeared without cause | - / w3:same |  |
| fd-fluffychat | yes (sigabrt) | **same**  | signal: DFX_SignalHandler :: signo(6), si_code(-6), pid(26309), tid(26342). | - / w3:same |  |
| fd-immich | yes (sigabrt) | **same**  | signal: DFX_SignalHandler :: signo(6), si_code(-6), pid(27586), tid(27613). | - / w4:same |  |
| fd-kitchenowl | yes (sigabrt) | **same**  | signal: DFX_SignalHandler :: signo(6), si_code(-6), pid(27065), tid(27089). | - / w4:same |  |
| fd-libre | yes (sigabrt) | **same**  | signal: DFX_SignalHandler :: signo(6), si_code(-6), pid(28881), tid(28904). | - / w4:same |  |
| fd-saber | yes (sigabrt) | **same**  | signal: DFX_SignalHandler :: signo(6), si_code(-6), pid(20351), tid(20374). | w3:same screen as U10.1T8; w3:same (dead) / w3:same |  |
| firefox | yes (disappeared) | **same**  | process-disappeared: process disappeared without cause | - / w4:same |  |
| localsend | yes (sigabrt) | **same**  | signal: DFX_SignalHandler :: signo(6), si_code(-6), pid(5521), tid(5548). | - / w4:same |  |
| ppsspp | yes (disappeared) | **same**  | process-disappeared: process disappeared without cause | - / w4:same |  |
| subwaysurfers | yes (mediandk;sigabrt) | **same**  | signal: DFX_SignalHandler :: signo(6), si_code(-6), pid(3245), tid(3271). | - / w4:same |  |
| vlc | yes (disappeared) | **same**  | process-disappeared: process disappeared without cause | - / w4:same |  |
| fd-im-vector-app | no (java_fix) | **moved** terminal+wall | java-cause: java.lang.UnsatisfiedLinkError: F02-A12-UNCLASSIFIED: dlopen_ns failed for /data/app/el2/100/base/im.vector.ap → java-cause: java.lang.UnsatisfiedLinkError: F02-A12-UNSUPPORTED-SYMBOL: dlopen_ns failed for /data/app/el2/100/base/im.vec (wall: Caused by: java.lang.UnsatisfiedLinkError: F02-A12-UNSUPPORTED-SYMBOL: dlopen_ns failed for /data/app/el2/100/) | - / w4:same | unpredicted, U12-attributable: U12 private libz alias fixed "libz.so not found" for librealm-jni; next wall UNSUPPORTED-SYMBOL in the same dlopen (same mechanism as mcdonalds) |
| mcdonalds | no (java_fix) | **moved** +wall | java-cause: java.lang.NullPointerException: Attempt to invoke interface method 'com.mcdonalds.mcdcoreapp.helper.interfaces → java-cause: java.lang.NullPointerException: Attempt to invoke interface method 'com.mcdonalds.mcdcoreapp.helper.interfaces (wall: Caused by: java.lang.RuntimeException: Unable to get provider androidx.startup.InitializationProvider: android) | - / w4:same | unpredicted, U12-attributable: terminal unchanged (DI NPE = consequence); the wall under it moved libz -> _ctype_ UNSUPPORTED-SYMBOL (outer: libz->_ctype_) |
| toutiao | no (-) | **moved** terminal+wall | no-observed-termination:  → process-disappeared: process disappeared without cause (wall: [B8-UEH] background thread 'CronetInit' uncaught, thread ended (process kept alive): java.lang.NoSuchMethodErr) | - / w3:different / desktop (process gone); U10.1T8 reference: white | NOT attributable to U12: new wall NoSuchMethodError NetworkInfo.getSubtype in CronetInit; NetworkInfo is identical in stubs 2f365a75 and 615b8bbe (no getSubtype in either) and no U12 change touches it; the U10.1T8 reference run is from the toutiao-gain shard -> run variance |
| cv2-ca-vaults-randomlydie | no (n11h_family) | **same**  | no-observed-termination:  | - / w4:same |  |
| cv2-com-bytehamster-flowitgame | no (n11h_family) | **same**  | no-observed-termination:  | - / w4:same |  |
| cv2-com-chessclock-android | no (java_fix;mediandk) | **same**  | java-cause: java.lang.UnsatisfiedLinkError: system library is absent from the adapter manifest | - / w4:same |  |
| cv2-com-degeder-yam | no (n11h_family) | **same**  | no-observed-termination:  | - / w4:same |  |
| cv2-com-emmanuelmess-itsdicey | no (-) | **same**  | no-observed-termination:  | - / w4:same |  |
| cv2-com-frequent-habits | no (-) | **same**  | no-observed-termination:  | - / w4:no-window |  |
| cv2-com-paultirk-yatoo | no (n11h_family) | **same**  | no-observed-termination:  | - / w4:same |  |
| cv2-com-stoutner-privacybrowser-standard | no (java_fix) | **same**  | java-cause: java.lang.UnsupportedOperationException: This method is not supported by the current version of the framework  | - / w4:same |  |
| cv2-dev-obfusk-jiten-webview | no (n11h_family) | **same**  | no-observed-termination:  | - / w4:same |  |
| cv2-org-andresoviedo-dddmodel2 | no (n11h_family) | **same**  | no-observed-termination:  | - / w4:same |  |
| cv2-org-secuso-privacyfriendlyyahtzeedicer | no (-) | **same**  | no-observed-termination:  | w3:same screen as U10.1T8 / w3:same |  |
| cv2-timur-webrtc-check | no (-) | **same**  | no-observed-termination:  | - / w4:same |  |
| fd-AppManager | no (n11h_family) | **same**  | no-observed-termination:  | w3:same screen as U10.1T8; w3:same (white) / w3:same |  |
| fd-api | no (java_fix) | **same**  | java-cause: java.lang.IllegalStateException: You need to use a Theme.AppCompat theme (or descendant) with this activity. | - / w3:same |  |
| fd-app | no (n11h_family) | **same**  | no-observed-termination:  | w3:no t20 (phase blocked) -> unknown (unlit in U10.1T8); w3:no t20 / w3:same |  |
| fd-meet | no (-) | **same**  | java-cause: [CHILD_CK] J_invokeStaticMain_main_threw: com.facebook.soloader.B: java.lang.UnsatisfiedLinkError: F02-A12-UNS | - / w4:same |  |
| fd-mobile | no (-) | **same**  | no-observed-termination:  | w3:no t20 (phase blocked) -> unknown (unlit in U10.1T8); w3:no t20 / w3:same |  |
| fd-musicplayer | no (-) | **same**  | java-cause: java.lang.IllegalArgumentException: can't create bitmap without a color space | - / w4:same |  |
| fd-noice | no (n11h_family) | **same**  | no-observed-termination:  | - / w3:no-window |  |
| fd-plus | no (java_fix) | **same**  | java-cause: java.lang.IllegalStateException: Surface was not locked | - / w4:same |  |
| fd-shatteredpixeldungeon | no (n11h_family) | **same**  | no-observed-termination:  | - / w4:same |  |
| fd-tutanota | no (-) | **same**  | no-observed-termination:  | w3:same screen as U10.1T8; w3:same (dead) / w3:same |  |
| fd-uhabits | no (n11h_family) | **same**  | no-observed-termination:  | - / w4:different / own UI (Loop welcome page) -- lottery key, not a U12 move |  |
| mindustry | no (java_fix) | **same**  | java-cause: java.lang.UnsatisfiedLinkError: F02-A12-UNSUPPORTED-SYMBOL: dlopen_ns failed for /data/app/el1/bundle/public/i | - / w4:same |  |
| noice | no (n11h_family) | **same**  | no-observed-termination:  | - / w4:same |  |
| termux | no (n11h_family) | **same**  | no-observed-termination:  | w3:same screen as U10.1T8; w3:same (white) / w3:same |  |
