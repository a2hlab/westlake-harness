# N11b R3 failed-launch capture

The previous capture ended 18.365 seconds before the failed launch. R3 captures the failure and the following t20 interval, but still cannot identify the rejecting guard. The candidate child is not accepted and 61b is restored to U8.

## Evidence

- Only the child bytes changed: `d240f8d2` to `163da805`; production dry-run passed all 312 identity checks.
- Continuous capture ran from 17:58:46 through 18:08:14. Raw stream sizes and SHA256 are in `results.json`; raw private-off logs remain local and are excluded from landing.
- PID 6203 entered admission at 18:04:53.322, reported `WLCGATE:LSP:LOAD_ERROR:10` at .740 and exited with code 123 at .753. See `evidence/candidate-6203-hilog.txt`.
- Error 10 means an `open_local_now` callback returned NULL. The reported `VALIDATED_COUNT:26` is the total closure `order_count`, not a count of successfully opened libraries. The pinned source excerpt and its SHA256 are included.
- Neither owner success marker appears. The new inheritance/NOLOAD/handle-identity guards do not log their individual outcomes, so the exact failed operation remains unknown. The earlier `libartbased.so` warnings and two Mali preload messages do not establish a root cause.
- The child survived only 0.431 seconds. The watcher captured its initial maps before ART/JVM/bridge/runtime were mapped; its periodic repeat was too late. Failure-time copy counts are **unknown**. No new faultlogger file was captured; the observed exit is code 123, not an observed signal crash.
- No activation-smoke or app batch ran after deployment failed. No facts file or t20 screenshot was produced for this candidate; screenshot and survival counts are **unknown**.

## Recovery and next diagnostic

The first automatic recovery failed control-child verification. The `before_unlock` recovery retry passed: all 312 U8 identities, runtime `e953c0921536`, boot image `4db882a81732`, parent 12716, child 13384, and the required parent/child maps checks. The board did not reboot and was unlocked. `evidence/final-u8.json` preserves that receipt.

This meets the plan's refutation branch: full launch coverage without a precise guard/dlopen failure diagnostic. Another experiment needs a diagnostic at each NULL-return branch, including the requested path, namespace, return value and `dlerror`, and rapid maps repeats during the first second. No new native probe was built or deployed in R3. The collector remains archived unchanged to make its sampling limitation reproducible.
