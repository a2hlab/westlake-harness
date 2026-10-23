# T95B independent bounded review

Log order and the last printed timestamp cannot establish whole-startup duration. This review reads only the specified private 4 MiB prefix, independently of the owner output. SHA-256 matches `2ee3a988406296170b4ce6511b097a8d3836a21d456f21ca6a18b2bf53219cc6`; 50,179 lines, final line incomplete.

- First explicit wall-clock prefix: `head.stdout:22`, `10-23 17:22:00`, PID/TID `6291/6291`. Last: `head.stdout:34517`, `10-23 17:22:25`, `6291/6302`. The 38 timestamped records form 8 PID/TID groups, all PID 6291; every anchor and group boundary is in `results.json`. Year/timezone are not printed. The remaining lines do not extend the proven wall-clock range.
- Three explicitly logged verifier operations: `:345` ServiceFinder.findService **288.259ms**; `:432` X.MIG.b **226.991ms**; `:435` X.MIG.c **137.893ms**, all TID 6311. Nine other records contain original `paused`/`total`/`for` scalars; these are retained separately without payload interpretation, summation, or startup attribution.
- No explicit ordinary first-frame or Activity-completion record was identified. `:1172` says a hold was released **before onCreate**, and `:4326` is a `MainActivity.lambda$doOnResume$4` stack-frame reference; neither establishes completion. The prefix ends at `:50179` in a partial `[TOUCH21-POLL]` record, with no wall-clock bound for that endpoint. First-frame time and total stage latency remain **unknown**; missing markers do not prove missing execution.

Line references are to `$HOME/.local/share/westlake/startup-stage-coverage-20261023/extended-01/head.stdout`. No private raw payload is copied. No devices, REA, native source, binary or fault analysis was used. No git action.

Reproduce the structured extraction: `python3 benchmark/2026-10-23-startup-stage-coverage/extended-review/review.py`. UI near-match assessment is a bounded manual finding, not a proof that every possible completion vocabulary is absent.
