# Boat v2 r3: rejected geometry, restored baseline

The six-pin candidate omitted the historical geometry repair at `libandroid.so`. Pinning and mapping runtime947 did not prove that the relevant app calls used its repaired definitions. The actual t30 screen still showed stretched controls, so no touch acceptance or 128-app run was claimed.

The child-root hashes are runtime947 and libandroid9cc; maps contain two mappings of each. The actual relocation owner remains unobserved. The attempted hilog capture returned CODE-31 (incompatible flags), not an empty app log. See `owner-readonly/results.json` and the independent static actual-owner report.

All candidate files/binds were rolled back, all 319 baseline identities matched, and a new cold boot reached READY56/Permissive. The original activation smoke passed. The outer reviewer personally inspected HelloWorld and Zigzag t20 screenshots. Raw facts: `TOTAL keys=2 screenshots_captured=4/4 alive_t5=2 alive_t20=2`.

This window exceeded its 30-minute limit: 10:34:13 to 11:39:30 CST, including an execution gap around 10:37–11:27. This is a scheduling failure, not a compliant experiment. 61b was unchanged. The full raw evidence is durably archived with a verified remote SHA in `../window2-persistence/persistence.json`; these summary files were added after that archive.
