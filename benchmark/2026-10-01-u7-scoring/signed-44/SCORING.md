# U7 signed 44-key partial score

Frozen fa92c5b9 unchanged. Original 5ea preliminary and signed-44 snapshots remain intact.

5ea t20 authority: outer ACK(95) **06:33:44**, not the nonexistent 06:0x reference. 5cd: **06:25:18**.

| Shard | First wall | Checkpoints | t20 |
|---|---|---|---|
| 5ea | {'hit': 18, 'unknown': 4} | {'not-applicable': 21, 'unknown': 1} | {'hit': 21, 'unknown': 1} |
| 5cd | {'hit': 15, 'unknown': 7} | {'not-applicable': 16, 'unknown': 6} | {'hit': 17, 'unknown': 4, 'false_positive': 1} |

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

Unknown is not a hit or a miss. Seal never installed/launched and has no screenshot: all three runtime axes unknown. Frozen flaky keys remain unknown t20 despite signed light.
Applicable checkpoint rows remain unknown: exact positive operation receipts are absent; UI/absence-of-error/class linkage cannot replace frozen criteria.
fd-plus has an earlier ColorMatrix.set warning at L50986, but its terminal root is the later MapInfoLayer null (L60342 -> L60357). Do not substitute an earlier caught exception for first_fatal.
fd-organicmaps is the only scored t20 false-positive (predicted unlit, signed own splash). fd-reader's unknown forecast stays unknown, not a retrospectively claimed hit. See GAINS.md for separate causal analysis.
