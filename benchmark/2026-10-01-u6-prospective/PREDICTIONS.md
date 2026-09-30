# U6-T7c/J7b v1 frozen first-wall forecast

Component tests are prior evidence, not a completed combined U6 run. T7d/N5 are not interchangeable with this version.

| key | prediction | first wall / expected crossing | repairs | t20 forecast |
|---|---|---|---|---|
| aegis | retain-ui | No first-page blocking wall expected | none | own-ui |
| anki | retain-ui | No first-page blocking wall expected | none | own-ui |
| antennapod | uncertain | Flaky first-frame result; no deterministic first-wall prediction | none | unknown |
| burgerking | advance | Unknown after complete-input install; React Native/class-loading startup remains a risk | INPUT-merged | unknown |
| fd-AppManager | uncertain | Unresolved white/no-content first frame | none | unknown |
| fd-android | retain-ui | No first-page blocking wall expected | none | own-ui |
| fd-api | retain-wall | Activity requires Theme.AppCompat | none | unlit |
| fd-app | advance | Expected past VibratorManager lock; next EGL/GL wall unknown | J7-vibrator | unknown |
| fd-auxio | retain-ui | No first-page blocking wall expected | none | own-ui |
| fd-binaryeye | retain-ui | No first-page blocking wall expected | none | own-ui |
| fd-breezyweather | retain-wall | Activity startup Object.getClass null producer | none | unlit |
| fd-calendar | retain-ui | No first-page blocking wall expected | none | own-ui |
| fd-catima | advance | Expected past AppWidget and SearchManager; no known first-page blocker | J7-appwidget, J7-search | own-ui |
| fd-client | retain-wall | WestlakeSSLContext SSLEngine unsupported; accountManager null later | none | unlit |
| fd-com-amaze-filemanager | retain-ui | No first-page blocking wall expected | none | own-ui |
| fd-com-kunzisoft-keepass-libre | retain-ui | No first-page blocking wall expected | none | own-ui |
| fd-droidify | retain-ui | No first-page blocking wall expected | none | own-ui |
| fd-etar | retain-ui | No first-page blocking wall expected | none | own-ui |
| fd-feeder | advance | CoroutineStart class-loading path remains after NetworkSpecifier | T7-networkrequest | unlit |
| fd-fennec_fdroid | retain-wall | libmozglue.so strong __gnu_strerror_r relocation | none | unlit |
| fd-filemanager | retain-ui | No first-page blocking wall expected | none | own-ui |
| fd-fitness | retain-ui | No first-page blocking wall expected | none | own-ui |
| fd-fluffychat | retain-wall | FlutterJNI bundle startup GetLongField fid-null | none | unlit |
| fd-gallery | advance | MediaStore.canManageMedia / MediaStore$Files.getContentUri missing | T7-mediastore | unlit |
| fd-im-vector-app | retain-wall | Realm JNI libz.so dependency cannot resolve in its load scope | none | unlit |
| fd-immich | retain-wall | Provider A2.b VerifyError is earliest blocking candidate; FlutterJNI fid-null also remains | none | unlit |
| fd-k9 | retain-ui | No first-page blocking wall expected | none | own-ui |
| fd-kitchenowl | retain-wall | Private Flutter libandroid -> runtime reload/XPM load failure | none | unlit |
| fd-libre | retain-wall | FlutterJNI bundle startup GetLongField fid-null | none | unlit |
| fd-libretube | advance | Expected past Parser.setProperty; next fatal unknown (provider size>0 error remains a candidate) | T7-tagsoup | unknown |
| fd-meet | retain-wall | Native loader chain: libhermes __register_atfork then libc++ android_set_abort_message | none | unlit |
| fd-minetest | retain-ui | No first-page blocking wall expected | none | own-ui |
| fd-mobile | uncertain | Unresolved black/no-content first frame | none | unknown |
| fd-mpv | retain-ui | No first-page blocking wall expected | none | own-ui |
| fd-musicplayer | retain-wall | Cannot create bitmap without a color space | none | unlit |
| fd-netguard | retain-ui | No first-page blocking wall expected | none | own-ui |
| fd-noice | uncertain | Flaky first-frame result; no deterministic first-wall prediction | none | unknown |
| fd-notes | uncertain | Flaky first-frame result; no deterministic first-wall prediction | none | unknown |
| fd-organicmaps | uncertain | Unresolved white/no-content after native owner publication | none | unknown |
| fd-plus | advance | ColorMatrix.setSaturation missing; OsmandMap null may follow | T7-networkinfo | unlit |
| fd-reader | advance | Expected past Vibrator, Wallpaper and Parser.setProperty; next wall unknown | J7-vibrator, J7-wallpaper, T7-tagsoup | unknown |
| fd-saber | retain-wall | FlutterJNI bundle startup GetLongField fid-null | none | unlit |
| fd-seal | input-blocked | Host sidecar inventory/ELF validation still rejects; repair not physically complete | INPUT-sidecar-clean | unknown |
| fd-shatteredpixeldungeon | advance | Expected past VibratorManager lock; next EGL/GL wall unknown | J7-vibrator | unknown |
| fd-stk | retain-ui | No first-page blocking wall expected | none | own-ui |
| fd-tasks | retain-ui | No first-page blocking wall expected | none | own-ui |
| fd-tusky | retain-ui | No first-page blocking wall expected | none | own-ui |
| fd-tutanota | retain-wall | WebView provider UnsupportedOperationException | none | unlit |
| fd-uhabits | uncertain | Flaky first-frame result; no deterministic first-wall prediction | J7-appwidget | unknown |
| fd-wifianalyzer | advance | CountryPreference constructor wb0.H Object.getClass null | J7-wifi | unlit |
| firefox | advance | libmozglue.so __gnu_strerror_r still unresolved after merged-input install | INPUT-merged | unlit |
| localsend | retain-wall | Private Flutter libandroid -> runtime reload/XPM load failure | none | unlit |
| markor | retain-ui | No first-page blocking wall expected | none | own-ui |
| mcdonalds | advance | librealmc/librealm-jni libz dependency remains after merged-input install | INPUT-merged | unlit |
| mindustry | retain-wall | libarc.so slCreateEngine remains unresolved | none | unlit |
| newpipe | retain-ui | No first-page blocking wall expected | none | own-ui |
| noice | uncertain | White/no-content first frame unresolved; SSLSockets background failure remains | none | unknown |
| ooniprobe | retain-ui | No first-page blocking wall expected | none | own-ui |
| opencamera | advance | Expected past battery Intent null; no known first-page blocker | J7-battery | own-ui |
| ppsspp | retain-wall | libppsspp_jni.so android_dlopen_ext relocation | none | unlit |
| subwaysurfers | advance | Expected past pin/split input rejection; Unity/native first wall unknown | INPUT-merged, INPUT-pin | unknown |
| termux | uncertain | Unresolved white/no-content first frame | none | unknown |
| toutiao | input-blocked | Host sidecar inventory/ELF validation still rejects; repair not physically complete | INPUT-sidecar-clean | unknown |
| vlc | retain-wall | Onboarding layout/theme/context inflation failure | none | unlit |
| wikipedia | advance | android.net.ssl.SSLSockets class gap after TagSoup property crossing | T7-tagsoup | unlit |
| x | advance | NetworkCapabilities.getSignalStrength missing after bandwidth crossing | INPUT-merged, T7-bandwidth | unlit |
