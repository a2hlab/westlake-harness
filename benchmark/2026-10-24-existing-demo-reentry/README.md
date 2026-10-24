# T123 existing 61b reentry observation — one successful slow reopening
The previous local recorder blocked observation before any app-icon click. With revision 4, one ordinary desktop click on unchanged 61b produced a new article child and a readable text feed by the +60s sample; images loaded by +90s. The +10s and +30s images remained white. The outer viewed all four samples. The page was preserved; power was restored to 30000/10000 and the owned lock released at 11:08:26.565. This is an observed slow reopening, not a runtime repair, video test, cold-boot guarantee or seal. Exact run: `run-20261024-110541-e2b1c729`.

## Earlier attempts


Two initial observation windows made **zero Home actions and zero app-icon clicks**. They do not establish whether the existing reentry behavior works. A current child was absent; the same host/appspawn identities and 21 historical control hashes were confirmed. The outer viewed the [unlocked blank app region](initial-white.jpeg).

The first window closed before a late outer approval could be recorded. The second received an outer review at T+66.388 seconds, but its local waiting loop never consumed the review file and cleaned up at T+120. A later continuation found the lock released. This is a local UI-recording handoff defect, not evidence that a desktop launch failed. Both windows restored base/override timeouts to 30000/10000 and released their locks.

Some same-named stage/held files were overwritten by the late second continuation. The preserved snapshot explicitly records this limitation and does not recover earlier bytes. Original restoration and unlock receipts remain available. See `outer-observations.json` for the persistent private archive and SHA pin. The next action is offline repair and testing of the actual single-worker entry before another board window. No runtime patch or white-screen repair has been delivered.

## Local recorder correction and review

The fixed review-consumption candidate and full-entry synthetic tests are preserved in [recorder-fix](recorder-fix/README.md). Independent review passed 15 tests but blocked device use because the planned failure return to Home was missing; see [exact review](peer-review/final-review.md). This candidate is retained as an intermediate version, not an accepted board driver. A separate launch-package revision will implement that cleanup. The independent Claude review of local atomic JSON publication passed 9 tests and was independently rerun by the outer reviewer; see [publication review](../2026-10-24-local-json-publication-review/README.md). No device behavior was accepted from these offline tests.

## Revision 3 board observation

The frozen v3 package passed 12 complete offline cases and independent review. The actual run `run-20261024-110011-c09c25ef` ended at T+29.145s before Home or icon click because the post-swipe layout still contained `ScreenLockRootComponent`. Power was restored to base 30000 / override 10000 and the owned lock was released. This is not a reopening result. Comparison exposed an invalid predicate: the prior 103406 layout contains the same node with visible=true and opacity=1 even though its subsequently captured image (SHA 950622b1cb45c00e4143fc46286fa991990cf6af600d14d06b98f52080909f55) is white. A retained layout node alone is not evidence of a displayed lock screen. The next minimal revision must capture the post-swipe image before deciding, retain credential stops, and require outer visual approval before Home.

## Observed revision 4 result

[Exact facts](final-v4/facts.txt) and [receipts](final-v4/results.json) retain the six received screenshots, four actual post-click samples, single icon click and restored power/lock state. The reviewed public images show [initial white host](final-v4/screenshots/host-white.jpeg), [text feed at the +60s sample](final-v4/screenshots/s60.jpeg), and [loaded feed images at +90s](final-v4/screenshots/s90.jpeg). Source and replay tests are pinned by [v4 manifest](launch-package-v4/manifest.json); author commits `3e73c63629792d50e4569a5d8b845343b3b8c068` and `72be78567` supply the implementation and dynamic facts correction.

## Startup delay evidence

[Same-child creation timing and log counterexample](peer-review/successful-child-22035/outer-addendum/README.md) estimate child creation at approximately 44 seconds after the click using device uptime, measured CLK_TCK=100 and bounded command timestamps. Creation precedes the first sampled text feed; subsequent work cannot all be labeled rendering. The same HTML-title302/JSON exception appears in this successful child, so its presence alone is not a sufficient explanation for persistent white screen. Whole-log stability was rejected because the file grew; only the two identical 512KiB prefixes are compared.
