Stage A window 4: safe finish after a runner layout bug
======================================================

The rc=1 continuation fix used the wrong real directory layout. shard_all_wrapped(sout, keys) searches */*/record.json, but sout is runner/<shard> and actual records live at timestamp/serial/key/record.json. The exact function from master 0f83d75444 returns False on all three completed first shards. runner-layout-proof.json records the source SHA, matching counts and finished/cleanup flags. No tool or package was changed during the window.

The candidate is the same armed bundle 190afedd. All three activation smokes passed. The runner measured first shards with 2/2/1 completed app attempts, then incorrectly stopped remaining shards and ran unconditional U9 finish. Exact facts and t20 screenshots are included per board; these are not lighting verdicts. The 57 remaining attempts are unknown, including authorized tail retests and Toutiao. This was not the 35-minute cutoff and does not demonstrate a native regression.

Every board restored signed U9 before its 45-minute deadline: 318 assertions have empty diff/absent, recovery HW/ZZ smoke PASS, final RUNTIME 565fc6fdc116 on 5ea/5cd and a2919b793eb6 on 61b, BOOT 4db882a81732 everywhere. Locks are empty. results.json binds the final receipts, run paths and SHA-inventoried raw archive in westlake-inputs. JSON copies normalize home/workspace paths and bind originals; no raw data was removed.

Coverage caveat: fd-binaryeye has a completed window2 record but was absent from outer window2 signoff. Record-based continuation excluded it; the existing t20 evidence was posted for outer supplemental review, rather than claimed signed. Seven lottery keys follow the outer 0/3 rule, including TrickyTripper. No new outside-plan test or automatic promotion occurred.

Stage B remains a disabled draft at ../stageB-draft/. It requires complete Stage A signoff and separate approval, fresh controls and Toutiao screenshots, 318/dual fingerprint identity, and otherwise finishes U9. Its known installation-chain and ZigZag retry constraints are explicit. The runner directory-depth fix remains with the outer-assigned tool owner; this delivery contains diagnosis and execution evidence only.
