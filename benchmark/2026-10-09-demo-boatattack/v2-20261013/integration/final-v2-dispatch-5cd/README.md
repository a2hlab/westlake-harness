# Explicit5cd wrapper successor, independently reviewable

The landed wrapper SHAf274 routes `--v2-recipe` to61b only. Calling it a5cd rehearsal entry would be wrong. This independent successor adds exactly one explicit alias and preserves the entire predecessor bytes below the insertion. It does not modify either frozen53-file package or the current repository wrapper.

| User argv | Dispatched entry / argv |
| --- | --- |
| `--v2-5cd-recipe FILE` | `final-v2-rehearsal-5cd/entry/restore_entry.py --v2-recipe FILE` |
| `--v2-5cd-recipe=FILE` | same entry, `--v2-recipe=FILE` |
| `--v2-recipe FILE` | unchanged61b entry |
| directory / realization / default | unchanged original entry |

All remaining arguments, including recipe SHA, fresh output and optional execute, are forwarded byte-for-byte. Duplicate5cd selectors or mixed route selectors reject before python dispatch. The wrapper does not infer a board from filenames, rewrite a recipe, enable execution, manufacture authorization or bypass the child serial/activation gates.

`demo_restore.sh.candidate` is intended for the actual `scripts/lab/demo_restore.sh` location in a separately reviewed successor revision; do not run it from this artifact directory, because the original script resolves tools relative to its install location. Its SHA is `2fc1ddada1d42120a7cf079b16fbb95b488b25bfa62aecf746cff0bb3117ba8b`. The original frozen wrapper SHA is `f274b76304983f61b7e383f3eaaeb402ac2b0701f7d010d91c203295c28d3c08` and remains a historical predecessor. This package's landing list only lands the proposal and tests, not a replacement at scripts/lab.

Root can reproduce the candidate from the exact main predecessor:

```sh
python3 benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/final-v2-dispatch-5cd/render_wrapper.py \
  --base scripts/lab/demo_restore.sh --out "$FRESH_WRAPPER_CANDIDATE"
```

After root reviews and installs that exact successor in its own revision, the one-command5cd entry is:

```sh
bash scripts/lab/demo_restore.sh --v2-5cd-recipe "$MAIN_BOUND_RECIPE" \
  --recipe-sha256 "$RECIPE_SHA" --out "$FRESH_OUT"
```

This defaults to offline preview. Only later outer authorization adds execute to an enabled, independently pinned recipe. Until the wrapper successor is installed, the already landed explicit5cd entry is usable directly:

```sh
python3 benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/final-v2-rehearsal-5cd/entry/restore_entry.py \
  --v2-recipe "$MAIN_BOUND_RECIPE" --recipe-sha256 "$RECIPE_SHA" --out "$FRESH_OUT"
```

Three offline tests cover8 exact argv cases,5 conflict negatives, shell syntax and original-body equality. Fake python exits without device access. The previous23 tests were not rerun after reconnect. `ACK-freeze.md` is the exact5cd53-file freeze ACK for root to relay to canonical PROGRESS; this session cannot write the main blackboard.
