# Authorized host restoration and clock alignment

Both assigned boards rejected the original control probe because the installed demonstration host differed from the signed build. Under blackboard #11, `hdc install -r` restored the host without clearing application data. Both installation commands returned 0. Before/after `bm dump` reported versionName `1.0.0`, versionCode `2`.

| Artifact | SHA-256 |
|---|---|
| Installed host before replacement (both boards) | `df3856387ba6971202b33e4475fde4e0fb1bf7fb33da0f4250429fe6535b014a` |
| Signed input and installed host after replacement (both boards) | `8cfa5bb1eb1a26fa69dbfd5618cecf0aefb282f6035aa9af24dcb9f96eb81267` |

Receipts: [5ea restoration](5ea34a4500000000000000001123012c/restore.json), [61b restoration](61b0657200000000000000000324012c/restore.json). Each directory also contains the install output and exact command log. The framework reports were `framework-2` on 5ea and `framework-1` on 61b, with identical inventories of 306 framework files. Host replacement did not modify the runtime, framework or APK payloads.

61b's clock was actually in **1970**, not merely hours behind. After the active control driver stopped, the authorized Mac `date` value was applied at epoch `1790585654`. Board/Mac readings differed by at most one second. [Clock receipt](../runs/cx10-controls-clock-20260928-1655/61b0657200000000000000000324012c/clock-sync/clock.json). All earlier 61b attempts are retained with `clock_skew` invalidation. The full control set is rerun after synchronization; no pre-sync visual or network result grants board admission.

The outer loop had already disabled 61b's autostart configuration and stopped broker/keeper/watchdog under #9 (commit `cb23604`, independently accepted under #11). The current read-only inventory found no known demo writer processes and no active system/vendor init configuration referencing these scripts. Keeper/watchdog stop markers exist; the absent broker stop marker is not treated as a running broker. No restart was performed.

R2: host identity and clock synchronization **verified**. Visual admission and the 43-app survey remain separate T0 acceptance gates.
