# U7 5ea preliminary scoring

Not the full 66-key result. Analyst image review is not outer signoff.

Frozen CSV: `fa92c5b964fed2976ba66d82fb703672241435a294c8d9286a7c9192ebab9007`.

| Axis | Scores |
|---|---|
| first_wall | hit=18, unknown=4 |
| checkpoints | not-applicable=21, unknown=1 |
| t20 | unknown=22 |

Analyst-only t20 preview: {'hit': 21, 'unknown': 1}. Not an accepted t20 score.

| Key | First wall | Checkpoint | t20 | Visual draft | Terminal/root hilog lines |
|---|---|---|---|---|---|
| aegis | hit (none) | not-applicable | unknown | own-ui | - / - |
| anki | hit (none) | not-applicable | unknown | own-ui | - / - |
| antennapod | unknown (unknown) | not-applicable | unknown | own-ui | - / - |
| burgerking | hit (realm-libz) | unknown | unknown | desktop | 45572 / 45398 |
| fd-AppManager | unknown (unknown) | not-applicable | unknown | white | - / - |
| fd-android | hit (none) | not-applicable | unknown | own-ui | - / - |
| fd-api | hit (appcompat-theme) | not-applicable | unknown | desktop | 37113 / 37171 |
| fd-app | unknown (unknown) | not-applicable | unknown | white | - / - |
| fd-auxio | hit (none) | not-applicable | unknown | own-ui | - / - |
| fd-binaryeye | hit (none) | not-applicable | unknown | own-ui | - / - |
| fd-breezyweather | hit (startup-getclass-null) | not-applicable | unknown | desktop | 73120 / 73135 |
| fd-calendar | hit (none) | not-applicable | unknown | own-ui | - / - |
| fd-catima | hit (none) | not-applicable | unknown | own-ui | - / - |
| fd-client | hit (accountmanager-null) | not-applicable | unknown | desktop | 55892 / 55907 |
| fd-com-amaze-filemanager | hit (none) | not-applicable | unknown | own-ui | - / - |
| fd-com-kunzisoft-keepass-libre | hit (none) | not-applicable | unknown | own-ui | - / - |
| fd-droidify | hit (none) | not-applicable | unknown | own-ui | - / - |
| fd-etar | hit (none) | not-applicable | unknown | own-ui | - / - |
| fd-feeder | hit (none) | not-applicable | unknown | own-ui | - / - |
| fd-fennec_fdroid | unknown (unknown) | not-applicable | unknown | desktop | - / - |
| fd-filemanager | hit (none) | not-applicable | unknown | own-ui | - / - |
| fd-fitness | hit (none) | not-applicable | unknown | own-ui | - / - |

Missing/unselected keys (not scored): fd-fluffychat, fd-gallery, fd-im-vector-app, fd-immich, fd-k9, fd-kitchenowl, fd-libre, fd-libretube, fd-meet, fd-minetest, fd-mobile, fd-mpv, fd-musicplayer, fd-netguard, fd-noice, fd-notes, fd-organicmaps, fd-plus, fd-reader, fd-saber, fd-seal, fd-shatteredpixeldungeon, fd-stk, fd-tasks, fd-tusky, fd-tutanota, fd-uhabits, fd-wifianalyzer, firefox, localsend, markor, mcdonalds, mindustry, newpipe, noice, ooniprobe, opencamera, ppsspp, subwaysurfers, termux, toutiao, vlc, wikipedia, x

Burger King INPUT-merged checkpoint stays unknown: zero external sidecars skips installed APK readback in the retained runner. Native libz failure does not establish that input checkpoint either way.
Fennec has process-disappearance evidence without a recovered fatal root. White AppManager/app rows remain unknown first wall; no SceneBoard/root-cause inference is made.
Antennapod is visibly lit in this attempt but its frozen flaky flag keeps t20 unknown.
