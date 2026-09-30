# N9 first-frame investigation targets

Exploratory scores failed lit negative controls; this is a target shortlist, not a detector or deploy manifest.

Seven keys; repeated fd-noice attempts remain separate. Zero score does not rule out the symptom.

| cohort / attempt | key | PID(s) | score | VSync request / callback | present / finishDrawing |
|---|---|---|---:|---:|---|
| t7d / t6 | wikipedia | 2105 | 40 | 582 / 582 | unknown / unknown |
| t7d / t6 | fd-noice | 5079 | 20 | 104 / 104 | unknown / unknown |
| u6 / 5cd | fd-AppManager | 12597 | 0 | 4 / 4 | unknown / unknown |
| u6 / 5cd | fd-app | 21665 | 0 | 5 / 5 | unknown / unknown |
| t7d / t6-extra-1 | fd-noice | 13870 | 0 | 95 / 95 | unknown / unknown |
| t7d / t6-extra-2 | fd-noice | 14835 | 0 | 98 / 98 | unknown / unknown |
| u6 / 5ea-resume | fd-shatteredpixeldungeon | 9509 | 0 | 5 / 5 | unknown / unknown |
| u6 / 61b | noice | 6057 | 0 | 49 / 49 | unknown / unknown |
| u6 / 61b | termux | 11010 | 0 | 0 / 0 | unknown / unknown |

## Lit negative controls

| cohort | key | score | VSync request / callback | result at score >= 20 |
|---|---|---:|---:|---|
| u6 | aegis | 0 | 11 / 11 | low |
| u6 | anki | 0 | 28 / 28 | low |
| u6 | antennapod | 40 | 1347 / 1346 | false alarm |
| u6 | fd-android | 0 | 5 / 5 | low |
| u6 | fd-auxio | 40 | 1328 / 1327 | false alarm |
| u6 | fd-binaryeye | 0 | 12 / 12 | low |
| u6 | fd-calendar | 0 | 11 / 11 | low |
| u6 | fd-catima | 0 | 11 / 11 | low |
| u6 | fd-com-amaze-filemanager | 0 | 30 / 30 | low |
| u6 | fd-com-kunzisoft-keepass-libre | 40 | 1355 / 1354 | false alarm |
| u6 | fd-droidify | 0 | 12 / 12 | low |
| u6 | fd-etar | 0 | 12 / 12 | low |
| u6 | fd-feeder | 0 | 25 / 25 | low |
| u6 | fd-filemanager | 40 | 1275 / 1274 | false alarm |
| u6 | fd-fitness | 0 | 7 / 7 | low |
| u6 | fd-k9 | 0 | 5 / 5 | low |
| u6 | fd-minetest | 0 | 3 / 3 | low |
| u6 | fd-mpv | 0 | 11 / 11 | low |
| u6 | fd-netguard | 0 | 46 / 46 | low |
| u6 | fd-noice | 0 | 26 / 26 | low |
| u6 | fd-notes | 0 | 73 / 73 | low |
| u6 | fd-stk | 0 | 22 / 22 | low |
| u6 | fd-tasks | 0 | 27 / 27 | low |
| u6 | fd-tusky | 0 | 27 / 27 | low |
| u6 | fd-uhabits | 0 | 28 / 28 | low |
| u6 | markor | 0 | 14 / 14 | low |
| u6 | newpipe | 0 | 81 / 81 | low |
| u6 | ooniprobe | 0 | 11 / 11 | low |
| u6 | opencamera | 40 | 723 / 722 | false alarm |
| t7d | aegis | 0 | 12 / 12 | low |
| t7d | fd-gallery | 0 | 12 / 12 | low |
| t7d | fd-libretube | 0 | 11 / 11 | low |
| t7d | noice | 0 | 23 / 23 | low |
| t7d | ooniprobe | 0 | 10 / 10 | low |

## Excluded reviewed-white attempts

| cohort | key | exclusion |
|---|---|---|
| u6 | fd-organicmaps | process-disappearance-cause-unknown |
| t7d | x | process-disappearance-cause-unknown |

Raw evidence, all 78 rows, capture hashes, per-PID counts and retained retries: results.json and evidence/observations.json.
