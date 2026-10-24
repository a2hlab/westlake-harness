# T123 local recorder correction — offline only

The second observation **did not test reopening**: no Home or icon click was executed. Its valid `outer-review.json` at T+66.388396 was ignored because private `run-20261024-103406/initial_stage.py:31–33` only checked `cleanup-now` and T+120. Cleanup completed at T+120.622380. The separate `continue_stage.py:10` arrived at T+132.029 and failed before UI; its fixed host-PID transfer at line 16 was also an unsuitable lifecycle handoff.

The late attempt overwrote `stage-result.json` and the `cleanup-held` / `cleanup-before-unlock` receipt stems. Those former bytes are unavailable. The original restore, power readback, unlock and final-held receipts remain: override restored to 10000, base 30000, final held rc1 and empty stdout/stderr. `results.json` pins these surviving originals. Neither old run directory was written after the preservation instruction. The external snapshot is later than the known overwrite; no reconstruction is claimed.

## Concrete corrected path

`initial_stage_candidate.py` retains one owner and one final cleanup region. It captures the initial image/layout, requires a SHA-bound `inner-unlock-review.json` for a detected noncredential lock screen, performs one reserved ordinary swipe, and finishes unlocked layout/image capture before writing `final-image-ready.json`. The final filename and SHA are then fixed. It polls `outer-review.json`, consumes a valid receipt, and calls its existing P4/P5 function **in the same process**. No new process or fixed-PID termination transfers responsibility.

The internal review requires `run_id`, `serial`, `boot`, initial `image_sha256`, reviewer `inner-codex`, and verdict `clock_wallpaper_no_credentials`. It cannot authorize Home/click. The final outer review requires matching `run_id`, `serial`, `boot`, `image`, `image_sha256`, nonempty reviewer, timezone-bearing timestamp within the original review window, and a recognized verdict. If the legacy `initial_image_sha256` alias is present it must also match. Only `desktop` / `host_white` allow continuation; credential, usable UI or unknown clean up. Partial/malformed JSON never grants permission. Receipt must be observed before original T+120; claimed `elapsed` does not override monotonic time. T+180/360/480 remain unchanged.

`receipt_candidate.py` reserves a unique command label exclusively before execution, opens stdout/stderr with `xb`, and publishes separate immutable begin/end JSON. `publish_once` writes/fsyncs a temporary file and atomically links complete bytes into an absent destination, then removes the temporary name. This intentionally uses create-if-absent hard-link publication instead of overwriting `rename/replace`: same-name publication raises `FileExistsError`, preserving existing bytes.

## Verification and limits

`tests-04.stderr`: **15 test methods pass**, including four full candidate CLI scenarios. `fixture_cli.py` runs the actual candidate as `__main__` with its P4 body intact and the real layout selector; only ordinary command I/O is synthetic. The positive sequence is initial lock image → later unlocked image → outer receipt at 66.388396s → exactly one Home/click → five samples → one cleanup, all recorded under one PID. Negative CLI cases cover absent review, wrong boot, and a continuation command error. Other checks cover the original loop counterexample, half JSON, stale/bad binding, original deadlines, repeated consumption, and actual receipt-helper duplicate rejection before a second command executes.

Earlier tests using a P4 spy are not the integration proof. The unused `reviewed_tail` helper's component tests do not substitute for the full CLI test. No third window, board calls, deployment or stopped implementation was performed/read during this correction. Candidate awaits outer review and fresh-run wiring; do not execute it against either preserved directory.

```sh
python3 benchmark/2026-10-24-existing-demo-reentry/recorder-fix/test_review_wait.py
```
