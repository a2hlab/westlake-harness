# R8 executor delta review

A changed candidate pin must not inherit an untested rollback fixture, and a read-only collector's exit code must not be mistaken for a matched binding. This packet checks the actual r8 producer against successor-r6 while preserving the disabled entry.

## Reproduce

From a repository checkout containing the pinned MAIN inputs:

```sh
python3 benchmark/2026-10-19-toutiao-rea-methods/r8-executor-review/review_offline.py --main "$WORKSPACES/westlake-harness" --out /tmp/r8-executor-review-fresh
```

The output directory must be new. The script verifies all four source pins before running anything. It reuses the original checker in an isolated temporary directory and changes only its source filename and synthetic r8 fixture fields. Its temporary generated results are copied into the persistent output. It executes the exact UNAPPROVED Python entry three times; all device imports are unreachable. It never runs generated shell text or the binding reader main.

See [results](run-01/results.json), [actual checker stdout](run-01/checker.stdout.txt), [checker rc](run-01/checker.rc.txt), [executor diff](run-01/executor.diff), [fixture adapter diff](run-01/checker-adapter.diff), and [review verdict](ACK.md). The two `offline-*.sh.txt` files are synthetic generated evidence, not authorized command cards.

The previously accepted ELF/build review is `benchmark/2026-10-19-toutiao-rea-methods/video-1919-r8-elf-review/final-review.json`. This review does not repeat its C oracle/build checks or claim actual runtime GOT values.
