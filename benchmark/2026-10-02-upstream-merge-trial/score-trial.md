# gap-map trial: upstream lifecycle vs our u9-first-wall, and score_first_blockers output

Their `harness.westlake_gap.lifecycle --json` ran on all 51 U9 unlit-key hilogs; compared to our `u9-first-wall` first fatal. Then `scripts/score_first_blockers.py` scored them against the 101 upstream corpus gap maps.

## Per-key: ours (u9-first-wall) vs theirs (lifecycle)

| key | verdict | ours family | theirs category | theirs blocker |
|---|---|---|---|---|
| burgerking | dead | no-fatal | native-loading | path is outside app domain: /system/android/li |
| cv2-ca-vaults-randomlydie | alive-white-window | no-fatal | no-blocker | path is outside app domain: /system/android/li |
| cv2-com-bytehamster-flowitgame | alive-white-window | no-fatal | no-blocker | path is outside app domain: /system/android/li |
| cv2-com-chessclock-android | dead | java:UnsatisfiedLinkError | native-loading | path is outside app domain: /system/android/li |
| cv2-com-degeder-yam | alive-white-window | no-fatal | no-blocker | path is outside app domain: /system/android/li |
| cv2-com-emmanuelmess-itsdicey | alive-black-content | no-fatal | no-blocker | path is outside app domain: /system/android/li |
| cv2-com-frequent-habits | app_failed | no-fatal | None |  |
| cv2-com-kaajjo-libresudoku | dead | no-fatal | no-blocker | path is outside app domain: /system/android/li |
| cv2-com-lcdcode-moodcairns | dead | java:AEADBadTagException | native-loading | path is outside app domain: /system/android/li |
| cv2-com-nbossard-packlist | dead | java:ClassNotFoundException | native-loading | path is outside app domain: /system/android/li |
| cv2-com-nononsenseapps-notepad | dead | java:NullPointerException | native-loading | path is outside app domain: /system/android/li |
| cv2-com-paultirk-yatoo | alive-white-window | no-fatal | no-blocker | path is outside app domain: /system/android/li |
| cv2-com-stoutner-privacybrowser-standard | dead | java:NullPointerException | native-loading | path is outside app domain: /system/android/li |
| cv2-com-trianguloy-clipboardeditor | dead | java:NoSuchMethodError | native-loading | path is outside app domain: /system/android/li |
| cv2-dev-obfusk-jiten-webview | alive-white-window | no-fatal | no-blocker | path is outside app domain: /system/android/li |
| cv2-org-andresoviedo-dddmodel2 | alive-white-window | no-fatal | no-blocker | path is outside app domain: /system/android/li |
| cv2-org-linaro-glmark2 | dead | native:signal | native-loading | path is outside app domain: /system/android/li |
| cv2-org-secuso-privacyfriendlyyahtzeedicer | alive-launcher-foreground | java:PackageManager$NameNotFoundException | native-loading | path is outside app domain: /system/android/li |
| cv2-timur-webrtc-check | alive-black-window | no-fatal | no-blocker | path is outside app domain: /system/android/li |
| fd-AppManager | alive-white-window | no-fatal | no-blocker | path is outside app domain: /system/android/li |
| fd-api | dead | java:IllegalStateException | native-loading | path is outside app domain: /system/android/li |
| fd-app | alive-white-window | no-fatal | no-blocker | path is outside app domain: /system/android/li |
| fd-breezyweather | dead | java:NullPointerException | native-loading | path is outside app domain: /system/android/li |
| fd-client | dead | java:NullPointerException | native-loading | path is outside app domain: /system/android/li |
| fd-fennec_fdroid | dead | native:signal | native-loading | path is outside app domain: /system/android/li |
| fd-fluffychat | dead | native:signal | native-loading | path is outside app domain: /system/android/li |
| fd-im-vector-app | dead | java:UnsatisfiedLinkError | native-loading | path is outside app domain: /system/android/li |
| fd-immich | dead | native:signal | native-loading | path is outside app domain: /system/android/li |
| fd-kitchenowl | dead | native:signal | native-loading | path is outside app domain: /system/android/li |
| fd-libre | dead | native:signal | native-loading | path is outside app domain: /system/android/li |
| fd-meet | dead | java:UnsatisfiedLinkError | native-loading | path is outside app domain: /system/android/li |
| fd-mobile | alive-black-window | no-fatal | no-blocker | path is outside app domain: /system/android/li |
| fd-musicplayer | dead | java:IllegalArgumentException | no-blocker | path is outside app domain: /system/android/li |
| fd-noice | alive-white-window | no-fatal | no-blocker | path is outside app domain: /system/android/li |
| fd-plus | dead | java:IllegalStateException | no-blocker | path is outside app domain: /system/android/li |
| fd-saber | dead | native:signal | native-loading | path is outside app domain: /system/android/li |
| fd-shatteredpixeldungeon | alive-white-window | no-fatal | no-blocker | path is outside app domain: /system/android/li |
| fd-tutanota | dead | java:NullPointerException | native-loading | path is outside app domain: /system/android/li |
| fd-uhabits | alive-white-window | no-fatal | no-blocker | path is outside app domain: /system/android/li |
| fd-wifianalyzer | dead | java:NullPointerException | native-loading | path is outside app domain: /system/android/li |
| firefox | dead | native:signal | native-loading | path is outside app domain: /system/android/li |
| localsend | dead | native:signal | native-loading | path is outside app domain: /system/android/li |
| mcdonalds | dead | java:NullPointerException | native-loading | path is outside app domain: /system/android/li |
| mindustry | dead | java:ExceptionInInitializerError | native-loading | path is outside app domain: /system/android/li |
| noice | alive-white-window | no-fatal | no-blocker | path is outside app domain: /system/android/li |
| ppsspp | dead | no-fatal | no-blocker | path is outside app domain: /system/android/li |
| subwaysurfers | dead | native:signal | native-loading | path is outside app domain: /system/android/li |
| termux | alive-white-window | no-fatal | native-loading | path is outside app domain: /system/android/li |
| toutiao | dead | java:NullPointerException | native-loading | path is outside app domain: /system/android/li |
| vlc | dead | no-fatal | native-loading | path is outside app domain: /system/android/li |
| x | alive-white-window | java:NullPointerException | native-loading | path is outside app domain: /system/android/li |

## Summary
- no-fatal/white keys where theirs agrees (no-blocker = reached drawing): **17**.
- keys with a real fatal in ours where theirs instead reports the route-A `libwestlake_html_compat.so` 'path outside app domain' line: **30 of 30**.
- `score_first_blockers.py` vs the 101 upstream corpus maps: **all 51 = `no-map`** (corpus maps use upstream package names, not our fd-<key>/cv2-<key>; no U9-specific maps exist).

## Adaptations needed to score route-A (none are blockers)
1. route-A profile for `lifecycle`: treat `[CHILD_CK] J_invokeStaticMain_main_threw: <exc>` as the fatal; ignore the ubiquitous `libwestlake_html_compat.so` path-outside-domain load attempt.
2. a U9 runtime index (`westlake-apk-gap snapshot-runtime` over U9 BCP + bridge/runtime ELFs) + scan our 51 APKs -> per-key `gap-map.json`.
3. fd-<key> <-> package-name alignment so lifecycle's app key matches the map dir.
