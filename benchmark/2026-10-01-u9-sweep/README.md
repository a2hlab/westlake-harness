# U9 full sweep: outer sign-off and prediction check (2026-10-01)

U9 = U8 + N10b native (child dc73a28d, runtime ac59dec0) + one JAR carrying J10d/e/f/g (238ffc14); the frozen
installer / libbms (FZ-001, 7048c7c5 / 6aadb8b4) unchanged. RUNTIME a8cb9a5a45a6, BOOTIMAGE 4db882a81732. Run by cx-t0
on all three boards (rollout `$WORKSPACES/westlake-harness-u7-executor/benchmark/2026-10-01-u9-native/rollout/approved-j10g/`,
runs listed in `outer-signoff.json`); every shard was read by the outer loop from t20 screenshots and signed on the board.

## Result

| | U8 (signed) | U9 |
|---|---|---|
| lit | 99 | **114** |

Every key U8 lit is lit again in U9 except two, neither a runtime regression: **fd-noice** (known flaky, ~50 %, white this
run) and **fd-seal** (install failure on 5ea/5cd: their libinstalls 2c9a5294 lacks the #79 native-data exception that
61b's 51e1b525 carries; re-run on 61b pending). Newly lit (17): acrylic, rpn (N10b); caniwebview, jslab (J10f);
beecount, trickytripper (J10e); deadhash, knot, advancedpassgen, diaspora, textpad, timerdroid, diceware, photophase,
shoppinglist, memory (J10d); page-bizzle.

## Against the prediction written before any U9 result (predictions-v5.csv)

`predict_vs_actual.py compare`: hit 155, flaky 6, missed-wall 4, regression 1 (fd-seal, above). Missed walls:
fd-kitchenowl and localsend (Flutter; past the N10b libandroid wall, now SIGABRT), vlc (predicted to pass with J10d,
still dies without a logged fatal), jiten-webview (predicted lit?, white window). These four feed the next scan.
