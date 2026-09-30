# Frozen v4-r2 versus completed r15c

The five-family predecessor covers **3/20 classified fatal candidates**, with **1/20 first-family agreement**, on exact APK identities. These denominators intentionally include families outside the old detector so missing JNI/guest/loader coverage is visible. Inside its original five-family scope the classified fatal cases are three (SharedPreferences, VelocityTracker, bionic imports), all candidate-covered; that narrower 3/3 is not the headline coverage score.

All 66 planned records finished. There are 32 exact predecessor APK matches, 34 outside its scan; among exact matches, 11 observations remain unclassified and one is not proven fatal. Nonfatal warnings and accepted UI are not first-fatal hits. Unknown outcomes remain excluded with reasons in backtest.csv and missed-or-unresolved.csv. Triage's selected exception is not necessarily the first causal startup failure. Static r13 coverage and r15c execution differ; this is family-level feedback, not causal repair verification or false-positive precision.

Reproduce from repository root:

    python3 benchmark/2026-09-29-static-wall-prediction/backtest_batch90.py \
      --predictions benchmark/2026-09-29-static-wall-prediction/v4-r2 \
      --triage /Users/zhaoyue/orca/workspaces/westlake-harness-b4/benchmark/2026-09-29-wikipedia-diff/r15cfull-triage.json \
      --out /tmp/r15c-backtest

For the next completed full run, use task90-feedback-static as --predictions and its new auto_triage JSON as --triage. Multiple shards must appear in one triage JSON; duplicate keys fail. Default expected count is 66 and every record must finish. Partial diagnostics require explicit --allow-partial and stay full_batch_complete=false. Prediction SHA is checked against freeze.json before scoring.

The next-run baseline was frozen after reading r15c; it must not be used to claim prospective success against r15c. Results store each prediction-before-click timing comparison and input record hashes. R16 sanity/control runs do not satisfy the full-batch gate.
