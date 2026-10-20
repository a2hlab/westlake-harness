# T30 independent real-route replay

The exact original T29 route reproduces the persistent refusal: the first lock returns -5, the next lock returns -16, but Request was called only once. Map/Unmap/Flush/Abort counts are zero. The first report preserves raw40601000 and retained1; R26 state4 is FAILED, and refs stay3 rather than returning to the cached steady-state2. Host build and run both returned0. This is the expected baseline failure, not a repair pass.

`replay.py` reuses the complete original `shim/test_route.c`. Its only provider change injects40601000 with NULL buffer and fd=-1 on the first Request, then normal behavior. An added scenario calls the actual exported route twice and records calls, refs and state. Real R14/R26/entry/provider adapter and actual T29 production pair/geometry are compiled. Fake resolver ELF projections use the production's five actual owner offsets; no business method is reconstructed. Existing observation code and the actual T27 observer are linked, with stderr captured to a regular file.

```sh
python3 benchmark/2026-10-20-t30-recovery-peer/replay.py \
  --repo "$WORKSPACES/westlake-harness" \
  --out "$HOME/.local/share/westlake/t30-recovery-peer/baseline-new"
# After the author's complete derived source is ready:
python3 benchmark/2026-10-20-t30-recovery-peer/replay.py \
  --repo "$WORKSPACES/westlake-harness" \
  --window-module /path/to/derived/window_module.c --expect recovery \
  --out "$HOME/.local/share/westlake/t30-recovery-peer/candidate-new"
```

Candidate mode requires the same first error, then real successful lock/unlock, two Request calls, one Map/Unmap/Flush, zero Abort, refs2 after the cycle and refs1 after final cleanup. It has not run yet. Candidate source dependencies, if added by the author, must be included explicitly before replay; no missing behavior will be stubbed. The raw baseline stdout uses999 solely as the not-called unlock sentinel.

`baseline-results.json`, original stdout/stderr, source pins and the persistent raw index preserve the actual baseline. No device calls or production builds occurred; this narrow host case does not replace the contract's real switch-before/after visual acceptance or other author regression obligations.
