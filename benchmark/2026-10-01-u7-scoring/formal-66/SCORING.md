# U7 signed 66-key formal score

Frozen fa92c5b9 unchanged. Original 5ea preliminary and signed-44 snapshots remain intact.

5ea t20 authority: outer ACK(95) **06:33:44**, not the nonexistent 06:0x reference. 5cd: **06:25:18**.

| Shard | First wall | Checkpoints | t20 |
|---|---|---|---|
| 5ea | {'hit': 18, 'unknown': 4} | {'not-applicable': 21, 'unknown': 1} | {'hit': 21, 'unknown': 1} |
| 5cd | {'hit': 15, 'unknown': 7} | {'not-applicable': 16, 'unknown': 6} | {'hit': 17, 'unknown': 4, 'false_positive': 1} |
| 61b | {'hit': 15, 'unknown': 7} | {'not-applicable': 14, 'unknown': 8} | {'hit': 21, 'unknown': 1} |

61b authority: outer ACK(95) **06:39:59**.

All axes: {'first_wall': {'hit': 48, 'unknown': 18}, 'checkpoints': {'not-applicable': 51, 'unknown': 15}, 't20': {'hit': 59, 'unknown': 6, 'false_positive': 1}}

Frozen t20 predictions: 28 own UI / 32 unlit / 6 unknown. Signed screenshots: {'own-ui': 34, 'desktop': 24, 'white': 6, 'black': 1, 'no-capture': 1}
Rates (unknown/NA excluded from scored denominator, also show all 66): {'first_wall': {'hits': 48, 'scored': 48, 'hit_fraction_on_scored': 1.0, 'hit_fraction_all_keys': 0.7272727272727273}, 'checkpoints': {'hits': 0, 'scored': 0, 'hit_fraction_on_scored': None, 'hit_fraction_all_keys': 0.0}, 't20': {'hits': 59, 'scored': 60, 'hit_fraction_on_scored': 0.9833333333333333, 'hit_fraction_all_keys': 0.8939393939393939}}

Confirmed unpredicted fatal walls: 0. Unknown first-wall keys are coverage gaps, not a zero-miss claim over all apps.

| Key | First wall | Checkpoint | t20 | Visual | Terminal/root |
|---|---|---|---|---|---|
| aegis | hit (none) | not-applicable | hit | own-ui | - / - |
| anki | hit (none) | not-applicable | hit | own-ui | - / - |
| antennapod | unknown (unknown) | not-applicable | unknown | own-ui | - / - |
| burgerking | hit (realm-libz) | unknown | hit | desktop | 45572 / 45398 |
| fd-AppManager | unknown (unknown) | not-applicable | hit | white | - / - |
| fd-android | hit (none) | not-applicable | hit | own-ui | - / - |
| fd-api | hit (appcompat-theme) | not-applicable | hit | desktop | 37113 / 37171 |
| fd-app | unknown (unknown) | not-applicable | hit | white | - / - |
| fd-auxio | hit (none) | not-applicable | hit | own-ui | - / - |
| fd-binaryeye | hit (none) | not-applicable | hit | own-ui | - / - |
| fd-breezyweather | hit (startup-getclass-null) | not-applicable | hit | desktop | 73120 / 73135 |
| fd-calendar | hit (none) | not-applicable | hit | own-ui | - / - |
| fd-catima | hit (none) | not-applicable | hit | own-ui | - / - |
| fd-client | hit (accountmanager-null) | not-applicable | hit | desktop | 55892 / 55907 |
| fd-com-amaze-filemanager | hit (none) | not-applicable | hit | own-ui | - / - |
| fd-com-kunzisoft-keepass-libre | hit (none) | not-applicable | hit | own-ui | - / - |
| fd-droidify | hit (none) | not-applicable | hit | own-ui | - / - |
| fd-etar | hit (none) | not-applicable | hit | own-ui | - / - |
| fd-feeder | hit (none) | not-applicable | hit | own-ui | - / - |
| fd-fennec_fdroid | unknown (unknown) | not-applicable | hit | desktop | - / - |
| fd-filemanager | hit (none) | not-applicable | hit | own-ui | - / - |
| fd-fitness | hit (none) | not-applicable | hit | own-ui | - / - |
| fd-fluffychat | hit (flutter-field-id) | not-applicable | hit | desktop | 28278 / 28608 |
| fd-gallery | hit (none) | unknown | hit | own-ui | - / - |
| fd-im-vector-app | hit (realm-libz) | not-applicable | hit | desktop | 38036 / 38037 |
| fd-immich | hit (flutter-field-id) | not-applicable | hit | desktop | 39298 / 39747 |
| fd-k9 | hit (none) | not-applicable | hit | own-ui | - / - |
| fd-kitchenowl | hit (private-runtime-reload) | not-applicable | hit | desktop | 17845 / 17875 |
| fd-libre | hit (flutter-field-id) | not-applicable | hit | desktop | 32491 / 32667 |
| fd-libretube | hit (none) | unknown | hit | own-ui | - / - |
| fd-meet | hit (jitsi-native-relocation) | not-applicable | hit | desktop | 24014 / 24014 |
| fd-minetest | hit (none) | not-applicable | hit | own-ui | - / - |
| fd-mobile | unknown (unknown) | not-applicable | hit | black | - / - |
| fd-mpv | hit (none) | not-applicable | hit | own-ui | - / - |
| fd-musicplayer | hit (bitmap-color-space) | not-applicable | hit | desktop | 42413 / 42414 |
| fd-netguard | hit (none) | not-applicable | hit | own-ui | - / - |
| fd-noice | unknown (none) | unknown | unknown | own-ui | - / - |
| fd-notes | unknown (none) | not-applicable | unknown | own-ui | - / - |
| fd-organicmaps | unknown (unknown) | not-applicable | false_positive | own-ui | - / - |
| fd-plus | hit (osmand-map-layer-null) | unknown | hit | desktop | 60342 / 60357 |
| fd-reader | unknown (none) | unknown | unknown | own-ui | - / - |
| fd-saber | hit (flutter-field-id) | not-applicable | hit | desktop | 30159 / 30609 |
| fd-seal | unknown (unknown) | unknown | unknown | no-capture | - / - |
| fd-shatteredpixeldungeon | unknown (unknown) | not-applicable | hit | white | - / - |
| fd-stk | hit (none) | not-applicable | hit | own-ui | - / - |
| fd-tasks | hit (none) | not-applicable | hit | own-ui | - / - |
| fd-tusky | hit (none) | not-applicable | hit | own-ui | - / - |
| fd-tutanota | hit (webview-provider) | not-applicable | hit | desktop | 38500 / 38515 |
| fd-uhabits | unknown (none) | not-applicable | unknown | own-ui | - / - |
| fd-wifianalyzer | hit (country-preference-null) | not-applicable | hit | desktop | 38503 / 38536 |
| firefox | unknown (unknown) | unknown | hit | desktop | - / - |
| localsend | hit (private-runtime-reload) | not-applicable | hit | desktop | 26436 / 26465 |
| markor | hit (none) | not-applicable | hit | own-ui | - / - |
| mcdonalds | hit (splash-datasource-null) | unknown | hit | desktop | 57304 / 57319 |
| mindustry | hit (opensles-create-engine) | not-applicable | hit | desktop | 34118 / 34141 |
| newpipe | hit (none) | not-applicable | hit | own-ui | - / - |
| noice | hit (none) | unknown | hit | own-ui | - / - |
| ooniprobe | hit (none) | not-applicable | hit | own-ui | - / - |
| opencamera | hit (none) | not-applicable | hit | own-ui | - / - |
| ppsspp | unknown (unknown) | not-applicable | hit | desktop | 35504 / - |
| subwaysurfers | hit (unity-mediandk-load) | unknown | hit | desktop | 58054 / 58220 |
| termux | unknown (unknown) | not-applicable | hit | white | - / - |
| toutiao | hit (mainactivity-boolean-null) | unknown | hit | desktop | 69762 / 69792 |
| vlc | unknown (unknown) | unknown | hit | desktop | 44510 / - |
| wikipedia | unknown (unknown) | unknown | hit | white | - / - |
| x | unknown (app-di-null) | unknown | hit | white | 75500 / 75515 |

Unknown is not a hit or a miss. Seal never installed/launched and has no screenshot: all three runtime axes unknown. Frozen flaky keys remain unknown t20 despite signed light.
Applicable checkpoint rows remain unknown: exact positive operation receipts are absent; UI/absence-of-error/class linkage cannot replace frozen criteria.
fd-plus has an earlier ColorMatrix.set warning at L50986, but its terminal root is the later MapInfoLayer null (L60342 -> L60357). Do not substitute an earlier caught exception for first_fatal.
fd-organicmaps is the only scored t20 false-positive (predicted unlit, signed own splash). fd-reader's unknown forecast stays unknown, not a retrospectively claimed hit. See GAINS.md for separate causal analysis.
