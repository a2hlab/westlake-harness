# U9 prediction, written before the sweep (2026-10-01)

**Why.** User rule 2026-10-01: a full sweep is judged against a per-key prediction written before it; after the
sweep `predict_vs_actual.py compare` lists regressions, missed walls (to feed the scanner) and unexpected lights.

**State predicted.** U9 = U8 + N10b native (a118aca0: Typeface VM, NDK AssetManager offsets, Emboss, owner preload)
+ J10b jar (cb392c96: Application before launch + NoTitle, keeps J10 ACTINFO). N11 (bridge/runtime double load) is
**not** in U9.

**Inputs.** Baseline `benchmark/2026-10-01-u8-sweep/outer-signoff.json`; death clusters
`benchmark/2026-10-01-u8-death-clusters/clusters.json` (oc-t4); `--cover getactivityinfo-namenotfound=j10b` (ACTINFO
rides in the J10b jar); observed windows: acrylic and ath0-rpn lit in the N10b r3 window, glmark2 still the same fatal,
page-bizzle lit / clipboardeditor dead in the U8 app_failed rerun; flaky keys from knowledge/gates/flaky-keys.json.

**Prediction (`predictions.csv`, 166 keys).** lit 98, flaky 6
(antennapod, fd-noice, fd-notes, fd-uhabits, noice, wikipedia), **lit? 12** (a wall a U9 fix removes; the next wall is unknown), the rest keep their U8 verdict.

lit? keys: cv2-com-aptasystems-dicewarepasswordgenerator (getactivityinfo-namenotfound), cv2-com-codedead-advancedpassgen (j10b-appcompat-actionbar), cv2-com-codedead-deadhash (j10b-appcompat-actionbar), cv2-com-deva-knot (j10b-appcompat-actionbar), cv2-com-emmanuelmess-itsdicey (j10b-appcompat-actionbar), cv2-com-github-dfa-diaspora-android (j10b-appcompat-actionbar), cv2-com-maxistar-textpad (j10b-appcompat-actionbar), cv2-com-ruesga-android-wallpapers-photophase (getactivityinfo-namenotfound), cv2-com-tomatodev-timerdroid (getactivityinfo-namenotfound), cv2-com-woefe-shoppinglist (getactivityinfo-namenotfound), fd-kitchenowl (n10b-flutter-libandroid), localsend (n10b-flutter-libandroid).

Command: `scripts/lab/predict_vs_actual.py predict ...` (exact arguments in this directory's `command.txt`).
After the U9 sweep: `predict_vs_actual.py compare --predictions predictions.csv --actual <U9 outer-signoff.json>`.
