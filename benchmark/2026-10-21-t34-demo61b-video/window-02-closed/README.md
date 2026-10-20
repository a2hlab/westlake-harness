# T34 W-02: failed candidate, rollback completed

The original `close.json` called the restored homepage healthy. Direct inspection contradicts that label: the final image shows “网络异常，请稍后重试” and “重试”, with no feed cards. `close-correction.json` preserves the original SHA and the root R2 correction; the original receipt remains untouched.

Candidate apply returned 0 and rebooted to `dc603250`. The candidate image is white/gray, with no feed or video demonstrated. The parent log records child 10218 creation and signal 11. Capture/event ordering and cause are unknown; this review does not attribute the failure to the candidate or investigate intermittent exits. Root rejected retention and signed rollback at 1192.821805 seconds.

Rollback returned 0; restore boot is `fdddd5c4`. Local receipts confirm the five physical original hashes, compat absence, unchanged HAP, 18/18 controls, power 30000/86400000 and debug absence (error 106). The later evidence13 real shell argv and rc0 bracket all five private hashes plus explicit compat absence with identical boot and parent5098/b12873 stat; mnt3005/WID30 are recorded. The earlier evidence12 placeholder argv remains not accepted. See `private-restoration-addendum.json`; this does not claim child namespace, additional metadata, network or feed health. The restored login screen and homepage network-error screen prove rendered UI, not healthy feed or video.

LOCK 02:05:27 to UNLOCK 02:33:19 is **1672 seconds at second precision**. Unlock rc is 0; holder absence is root-reported. This is not a retained candidate, successful 61b migration, video pass, audio confirmation, new public API freeze, or ordinary-app/BoatAttack regression result.

## Selected original images

- [Candidate white screen](candidate-white.jpeg)
- [Restored login promotion](restored-login.jpeg)
- [Restored homepage network error](restored-network-error.jpeg)

These are three selected original-byte images, not a total window capture count. `private-source-index.json` pins the persistent originals without publishing raw logs or personal paths. `log-excerpt.json` contains only the relevant bounded lines.

## API proposal

`api-proposal.json` supplies observation 46 against the main 45-row input. The isolated-tree table now appends that row; main remains untouched. All 45 original objects, top-level metadata, 315 historical semantics and 8 frozen entries are preserved. Source/build references reuse the existing T34 mapping; runtime references point to this failed-window evidence. A public archive receipt remains pending. The private-state evidence13 is an explicit addendum; it does not erase the earlier unknown verdict or flawed evidence12. The existing renderer passed: 46 observations and 1134 exact references. Before landing, its read-only source view contains byte copies of pinned main references plus this unpublished peer delta. Root can rerun with `--source-root` set to main after landing. `api-final-check.json` records the scope; `checks.json` retains the initial draft review.
