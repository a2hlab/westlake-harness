# Read-only selfcheck entry routing delta

The wrapper previously sent explicit realizations to the original collector, which loses NUL bytes in host cmdline transport. This delta routes explicit realization and activation checks through the already reviewed R5 binary collector adapter. The original default implementation and its offline observed-input path are byte-identical. No validator, comparison, proof, seal, executor, or collector source changes.

## Landing

Land only `landing-paths.txt`. `sources.json` pins the two already-landed R5 dependency files; they are prerequisites, not duplicated by this delta. The wrapper replaces only the corresponding wrapper item of the earlier delivery; all historical frozen records remain unchanged. `wrapper.diff` is the complete source delta against the main-tree wrapper observed before editing. No commit or device execution is performed by this delivery.

## Offline verification

```sh
bash -n scripts/lab/demo_selfcheck.sh
python3 benchmark/2026-10-12-exact-realization/r6-selfcheck-entry/test_dispatch.py
```

Eight dispatch checks passed: split/equal realization, offline realization, split/equal activation, offline activation, legacy default, and legacy offline. Every check uses a fake `python3`, verifies exact argv and propagates its exit code 23. The legacy heredoc is byte-identical. These results verify routing only, not a new live selfcheck or seal acceptance.

## Outer read-only entrypoints (not executed here)

Keep the existing frozen checker arguments. Each invocation needs an unused output path; the serial, current boot, and binding SHA must come from the outer's actual evidence.

```sh
bash scripts/lab/demo_selfcheck.sh --realization "$PROOF" --serial "$SERIAL" --boot-id "$BOOT_ID" --hdc "$HDC" --out "$OUT"
bash scripts/lab/demo_selfcheck.sh --activation-binding "$BINDING" --binding-sha256 "$BINDING_SHA256" --serial "$SERIAL" --boot-id "$BOOT_ID" --hdc "$HDC" --out "$OUT"
```

For an offline recorded comparison, replace `--hdc "$HDC"` with `--observed "$OBSERVED"`. The checker retains its existing offline status; this wrapper does not upgrade that status to live PASS. Default `--seal` invocations remain unchanged.
