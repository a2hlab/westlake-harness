# Demo t3 mechanical tier tally

## Evidence first

Pinned outer signoff: **128/128 canonical packages**; **0 pending**. This is not stability, reboot or interaction acceptance.

Historical content tier: **87/94 signed lit/lit_splash**. Empty-state and error-screen tiers are kept separate even when signed lit.

- manifest: `$WORKSPACES/westlake-harness-bms/benchmark/2026-10-09-demo-baseline/demo-manifest.json`, SHA256 `7a2627326cb536bc8b0ee35587827999f448f827a91e22bdc663809767d82933`.
- outer_signoff: `$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-baseline/t3-outer-signoff.json`, SHA256 `0e9b825a0ccbfcbe6af0bc1ccd7f93d55d323e1869b8ecdc957a7591048aa387`.

## Tier totals

| Manifest tier | Total | Signed lit/lit_splash | Verdict counts |
|---|---:|---:|---|
| shown | 94 | 87 | half_empty=3, lit=86, lit_splash=1, not_lit=4 |
| minimal | 32 | 26 | half_empty=2, half_loading=3, lit=26, not_lit=1 |
| errors | 2 | 1 | lit_splash=1, not_lit=1 |

## Content-tier signed-lit keys

- `aegis`
- `anki`
- `cv2-anupam-acrylic`
- `cv2-biz-binarysolutions-vatcalculator`
- `cv2-com-aptasystems-dicewarepasswordgenerator`
- `cv2-com-asdoi-timetable`
- `cv2-com-ath0-rpn`
- `cv2-com-atr-hiit`
- `cv2-com-benny-pxerstudio`
- `cv2-com-better-alarm`
- `cv2-com-caniwebview-android`
- `cv2-com-chancehorizon-just24hoursplus`
- `cv2-com-chess-clock`
- `cv2-com-codedead-advancedpassgen`
- `cv2-com-codedead-deadhash`
- `cv2-com-darkempire78-opencalculator`
- `cv2-com-edward-studytracker`
- `cv2-com-ei-bmicalc`
- `cv2-com-example-dozencalc`
- `cv2-com-example-ttime`
- `cv2-com-github-dfa-diaspora-android`
- `cv2-com-goofwear-file85toolkit`
- `cv2-com-groce-app`
- `cv2-com-harr1424-listmaker`
- `cv2-com-kaajjo-libresudoku`
- `cv2-com-knirirr-beecount`
- `cv2-com-lcdcode-moodcairns`
- `cv2-com-lolo-io-onelist`
- `cv2-com-maltaisn-notes-sync`
- `cv2-com-mzhang-cleantimer`
- `cv2-com-nicue-onetwo`
- `cv2-com-paperknifeplus-app`
- `cv2-com-pocket-plan-j7-003`
- `cv2-com-pvcodes-debtcalc`
- `cv2-com-rootminusone8004-bazarnote`
- `cv2-com-ruesga-android-wallpapers-photophase`
- `cv2-com-simonimal-minimalcurconv`
- `cv2-com-sunilpaulmathew-snotz`
- `cv2-com-tomatodev-timerdroid`
- `cv2-com-trianguloy-clipboardeditor`
- `cv2-com-vonglasow-michael-voltagedrop`
- `cv2-com-wattwurm-toodoo`
- `cv2-com-zola-bmi`
- `cv2-de-koelle-christian-trickytripper`
- `cv2-de-markusfisch-android-shadereditor`
- `cv2-io-github-jdanders-dropcount`
- `cv2-org-secuso-privacyfriendly2048`
- `cv2-org-secuso-privacyfriendlybattleship`
- `cv2-org-secuso-privacyfriendlycircuittraining`
- `cv2-org-secuso-privacyfriendlydame`
- `cv2-org-secuso-privacyfriendlydicer`
- `cv2-org-secuso-privacyfriendlyintervaltimer`
- `cv2-org-secuso-privacyfriendlyludo`
- `cv2-org-secuso-privacyfriendlymemory`
- `cv2-org-secuso-privacyfriendlyminesweeper`
- `cv2-org-secuso-privacyfriendlynotes`
- `cv2-org-secuso-privacyfriendlypaindiary`
- `cv2-org-secuso-privacyfriendlypasswordgenerator`
- `cv2-org-secuso-privacyfriendlypausinghealthily`
- `cv2-org-secuso-privacyfriendlypin`
- `cv2-org-secuso-privacyfriendlyrecknoningskills`
- `cv2-org-secuso-privacyfriendlyruler`
- `cv2-org-secuso-privacyfriendlysudoku`
- `cv2-org-secuso-privacyfriendlytapemeasure`
- `cv2-org-secuso-privacyfriendlytodolist`
- `cv2-org-secuso-privacyfriendlyyahtzeedicer`
- `fd-calendar`
- `fd-catima`
- `fd-client`
- `fd-com-amaze-filemanager`
- `fd-com-kunzisoft-keepass-libre`
- `fd-etar`
- `fd-feeder`
- `fd-filemanager`
- `fd-fitness`
- `fd-mpv`
- `fd-netguard`
- `fd-noice`
- `fd-organicmaps`
- `fd-reader`
- `fd-seal`
- `fd-tasks`
- `fd-tusky`
- `fd-uhabits`
- `markor`
- `ooniprobe`
- `wikipedia`

## Content-tier exceptions

| Key | Package | Verdict | Batch |
|---|---|---|---|
| `antennapod` | `de.danoeh.antennapod` | not_lit | capture-02-resume |
| `cv2-com-armanmaurya-archiv` | `com.armanmaurya.archiv` | half_empty | capture-02-resume |
| `cv2-org-andresoviedo-dddmodel2` | `org.andresoviedo.dddmodel2` | not_lit | capture-02-resume |
| `fd-auxio` | `org.oxycblt.auxio` | half_empty | capture-02-resume |
| `fd-libretube` | `com.github.libretube` | half_empty | capture-02-resume |
| `opencamera` | `net.sourceforge.opencamera` | not_lit | capture-02-resume |
| `vlc` | `org.videolan.vlc` | not_lit | capture-02-resume |

## All empty-state keys

| Key | Package | Verdict | Batch |
|---|---|---|---|
| `cv2-app-varlorg-unote` | `app.varlorg.unote` | lit | capture-05 |
| `cv2-ca-ramzan-delist` | `ca.ramzan.delist` | lit | capture-05 |
| `cv2-com-alxgnon-postwriter` | `com.alxgnon.postwriter` | lit | capture-05 |
| `cv2-com-angrydoughnuts-android-alarmclock` | `com.angrydoughnuts.android.alarmclock` | lit | capture-04 |
| `cv2-com-cg-lrceditor` | `com.cg.lrceditor` | lit | capture-04 |
| `cv2-com-deva-knot` | `com.deva.knot` | lit | capture-05 |
| `cv2-com-emmanuelmess-itsdicey` | `com.emmanuelmess.itsdicey` | lit | capture-04 |
| `cv2-com-git-itdolan31-crystalpad` | `com.git.itdolan31.crystalpad` | lit | capture-05 |
| `cv2-com-maxistar-textpad` | `com.maxistar.textpad` | lit | capture-05 |
| `cv2-com-nathaniel-motus-umlclasseditor` | `com.nathaniel.motus.umlclasseditor` | lit | capture-04 |
| `cv2-com-nbossard-packlist` | `com.nbossard.packlist` | lit | capture-05 |
| `cv2-com-nima-taskmanager` | `com.nima.taskmanager` | lit | capture-05 |
| `cv2-com-nononsenseapps-notepad` | `com.nononsenseapps.notepad` | lit | capture-05 |
| `cv2-com-notecryptpro` | `com.notecryptpro` | lit | capture-05 |
| `cv2-com-omgodse-notally` | `com.omgodse.notally` | lit | capture-05 |
| `cv2-com-page-bizzle` | `com.page.bizzle` | lit | capture-05 |
| `cv2-com-pep1lo-bakerspercentagecalculator` | `com.pep1lo.bakerspercentagecalculator` | lit | capture-04 |
| `cv2-com-rafapps-simplenotes` | `com.rafapps.simplenotes` | lit | capture-05-icon-retry |
| `cv2-com-wbpxre150-shoppinglist` | `com.wbpxre150.shoppinglist` | lit | capture-05 |
| `cv2-com-willbsp-habits` | `com.willbsp.habits` | lit | capture-04 |
| `cv2-com-woefe-shoppinglist` | `com.woefe.shoppinglist` | lit | capture-05 |
| `cv2-de-markusfisch-android-libra` | `de.markusfisch.android.libra` | lit | capture-04 |
| `cv2-eu-dfdx-jslab` | `eu.dfdx.jslab` | half_empty | capture-04 |
| `cv2-org-quicksc0p3r-simplecounter` | `org.quicksc0p3r.simplecounter` | lit | capture-04 |
| `fd-android` | `net.thunderbird.android` | half_loading | capture-05 |
| `fd-binaryeye` | `de.markusfisch.android.binaryeye` | lit | capture-04 |
| `fd-droidify` | `com.looker.droidify` | half_empty | capture-05 |
| `fd-gallery` | `org.fossify.gallery` | lit | capture-04 |
| `fd-k9` | `com.fsck.k9` | half_loading | capture-05 |
| `fd-minetest` | `net.minetest.minetest` | half_loading | capture-04 |
| `fd-notes` | `org.fossify.notes` | lit | capture-05 |
| `newpipe` | `org.schabi.newpipe` | not_lit | capture-05 |

## Required games

These verdicts do not certify gameplay interaction; no interaction evidence was supplied.

| Key | Package | Verdict | Batch |
|---|---|---|---|
| `cv2-com-kaajjo-libresudoku` | `com.kaajjo.libresudoku` | lit | window1 |
| `cv2-io-github-jdanders-dropcount` | `io.github.jdanders.dropcount` | lit | window1 |
| `cv2-org-secuso-privacyfriendly2048` | `org.secuso.privacyfriendly2048` | lit | window1 |
| `cv2-org-secuso-privacyfriendlybattleship` | `org.secuso.privacyfriendlybattleship` | lit | window1 |
| `cv2-org-secuso-privacyfriendlydame` | `org.secuso.privacyfriendlydame` | lit | window1 |
| `cv2-org-secuso-privacyfriendlyludo` | `org.secuso.privacyfriendlyludo` | lit | window1 |
| `cv2-org-secuso-privacyfriendlymemory` | `org.secuso.privacyfriendlymemory` | lit | window1 |
| `cv2-org-secuso-privacyfriendlyminesweeper` | `org.secuso.privacyfriendlyminesweeper` | lit | window1 |
| `cv2-org-secuso-privacyfriendlysudoku` | `org.secuso.privacyfriendlysudoku` | lit | window1 |
| `cv2-org-secuso-privacyfriendlyyahtzeedicer` | `org.secuso.privacyfriendlyyahtzeedicer` | lit | window1 |
| `fd-minetest` | `net.minetest.minetest` | half_loading | capture-04 |
| `fd-stk` | `org.supertuxkart.stk` | lit_splash | capture-04 |

## Error-screen tier (not in 94/32)

| Key | Package | Verdict | Batch |
|---|---|---|---|
| `fd-stk` | `org.supertuxkart.stk` | lit_splash | capture-04 |
| `termux` | `com.termux` | not_lit | capture-04 |

## Unsigned / pending

Missing verdict stays pending even if a capture-05 facts row or screenshot already exists.

| Key | Package | Verdict | Batch |
|---|---|---|---|

## Reproduce

```sh
python3 benchmark/2026-10-09-demo-baseline/t3/build_tally.py
```

The default signoff is read fresh from master. Inputs are pinned and the exact signoff bytes are saved as outer-signoff-input.json. No timestamps are generated; unchanged inputs give identical bytes.

The t4 summarizer's separate t3-tier adapter handles the v1 outer table mechanically; it does not convert legacy lit into own-content or weaken its stricter stability-v2 checks.

## Verification scope

Six t3-tally known answers pass. An optional older stability-suite run has nine preexisting fixture path errors (cycle-1/cycle-1/stable/record.json); the control with only the new tally adapter omitted has the same nine errors. See evidence/stability-control.json. No stability PASS is claimed and those unrelated fixtures are not changed.
