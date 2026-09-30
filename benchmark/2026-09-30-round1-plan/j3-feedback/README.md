# J3 offline refresh and J4/N3 priorities

The old U2 list treated fd-noice as unlit and had no NewPipe platform-signature cause. J3 retains **24/24 U2 lights and adds fd-noice: 25 lit / 41 unlit out of 66**. These are the outer review's screenshot conclusions; this report does not re-sign images. The J3 source README's claim that fd-api passed AppCompat is contradicted by its own log: only the alias theme ID changed. No board access or historical prediction edits occurred.

Two runs, 5ea and 61b, have identical **119-file fingerprints**, U2 + J3 `75c2068c`. [run-audit.json](run-audit.json) preserves their complete hashes and facts. [record-facts.json](record-facts.json) recounts `record.json` captured flags and app process tables: **126 captures; t5 alive 32 / dead 31 / unknown 3; t20 alive 31 / dead 32 / unknown 3**. Input failures account for the three missing observations. Alive is not lit.

[unlock-priority.csv](unlock-priority.csv) and [next-clusters.json](next-clusters.json) contain **22 clusters**, explicit lane and expected app sets. [J4.json](J4.json) / [N3.json](N3.json) are the lane handoffs. There are **19 unlit apps with named API checkpoint repair targets** (J4 5, N3 14), **5 conditional boot repairs**, **14 investigation candidates**, and **3 host-input repairs**. These are conditional repair yields, not a prediction that all proposed code fixes will work or that 19 new apps will light. All new first-screen outcomes remain unknown.

| Cluster | Owner | Expected checkpoint unlock | Conditional / already lit |
|---|---|---|---|
| N3-namespace | cx-t0 | burgerking, fd-fluffychat, fd-kitchenowl, fd-organicmaps, localsend, mcdonalds, ppsspp | — |
| J4-boot-api | oc-t4 (#91/T7), cc-t3 API consumers | — | fd-feeder, fd-gallery, fd-plus, wikipedia, x |
| N3-no-fatal-observation | cx-t0 | — | fd-AppManager, fd-mobile, fd-uhabits, termux |
| INPUT-assembly | cx-bms | fd-seal, subwaysurfers, toutiao | — |
| J4-null-producer | cc-t3 | — | fd-breezyweather, fd-catima, fd-wifianalyzer |
| N3-eglimpl | cx-t0 | fd-app, fd-shatteredpixeldungeon | — |
| N3-jna-symbol | cx-t0 | fd-fennec_fdroid, firefox | — |
| N3-property | cx-t0 | fd-libre, fd-saber | — |
| J4-haptics | cc-t3 | fd-reader | — |
| J4-media-session | cc-t3 | fd-musicplayer | — |
| J4-mediarouter | cc-t3 | noice | — |
| J4-sentry | cc-t3 | fd-im-vector-app | — |
| J4-tls-java | cc-t3 | fd-client | fd-noice |
| N3-opensles | cx-t0 | mindustry | — |
| J4-alias-theme | cc-t3 | — | fd-api |
| J4-cache-input | cc-t3 | — | fd-libretube |
| J4-intent-contract | cc-t3 | — | opencamera |
| J4-restrictions | cc-t3 | — | fd-meet |
| J4-verifier-interface | cc-t3 | — | fd-immich |
| N3-theme-projection | cx-t0 | — | vlc |
| N3-webview | cx-t0 | — | fd-tutanota |
| J4-platform-signature | cc-t3 | — | newpipe |

Priority interpretation: N3 namespace visibility affects seven current first-wall apps, plus secondary evidence in VLC/SPD/Element; those extra keys are not added to the primary count. JNA `__sF`, EGLImpl and property APIs each affect two direct apps. J4's five boot API cases require oc-t4's #91/T7 boot-classpath artifacts; an ordinary adapter JAR alone predicts zero passage there. The eight other uncertain J4 and six uncertain N3 cases retain explicit observation boundaries. A matching NPE shape is not proof that one patch repairs all apps.

Three important corrections, with PID-attributed excerpts in [target-evidence.json](target-evidence.json) and full paths/hashes in [evidence.json](evidence.json):

- **fd-api**, J3 5ea `fd-api/hilog.txt:13812`: alias ID `0x1030237 → 0x7f120252`; line **18447** still throws `You need to use a Theme.AppCompat theme`. Alias-only work predicts no further unlock. Resource/context investigation belongs to cc-t3; a parser defect is not established.
- **NewPipe**, J3 61b `newpipe/hilog.txt:55590`: synthesized Android package; line **55592** exposes `Platform signature not found` during PlayerService bind. Already lit. A coherent package-signing metadata fix predicts passing this functional checkpoint, **zero new lights counted**; playback remains unverified.
- **fd-noice**, J3 5ea `fd-noice/hilog.txt:37704`: background `SSLSockets` failure, process kept alive. Outer signed its welcome UI lit. Keep it as a J4 TLS functional beneficiary, not an unlit first-screen blocker.

PPSSPP's J3 log catches `libGLESv2` loading failure and subsequently calls `System.exit(-1)`; this report does not carry forward U2's SIGSEGV description. Four FDSAN debug reports remain evidence to inspect, not automatic first-fatal diagnoses. Every tracked row records current PID-attributed first blocker/terminal, source SHA, and any archived faultlog; old scoring fields live under `historical_U2_assessment`.

`evidence.json` covers all 66 apps. `per-key.json` refreshes the **42 formerly unlit** rows (including now-lit fd-noice); it is not an all-66 result table. Input repairs are detailed in [the separate receipt](../../2026-09-30-input-recovery/README.md); Subway's revised identity does not change its historical J3 failure.

Reproduce from repository root (master's archived J3 and U2 runs must be readable):

```sh
python3 benchmark/2026-09-30-round1-plan/j3-feedback/extract.py
python3 benchmark/2026-09-30-round1-plan/j3-feedback/build.py
python3 benchmark/2026-09-30-input-recovery/test_receipt.py -v
```

Two receipt tests verify 66 keys, the 25-light set size, identical fingerprints, all process/capture recounts, 41-key unlit coverage, exact target-log excerpts/PIDs, source hashes, and conditional/functional boundaries. R2: archived observations verified; future repair yield and additional lighting unverified. SHA256SUMS freezes this handoff independently of previous predictions.
