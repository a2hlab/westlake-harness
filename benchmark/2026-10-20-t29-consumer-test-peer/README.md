# T29 real consumer-method host peer

A logger-only test cannot establish consumer method transparency. This fixture directly includes both complete, SHA-pinned original translation units and calls their actual methods. Only external JNI/OH services are fake. No method body is copied, rewritten, or extracted, and no logger stub is provided.

The baseline passes 40 cases: 27 attach/detach/update cases and 13 producer creation/destruction cases. Observations contain real call order, provider incoming errno, method result, final errno, exception state, field writes, texture/detached state and producer identity. The full original `GetState` and producer getter execute. Source and fixture inputs are snapshotted before compilation; drift during compilation refuses the result. stderr is a real regular file so a supplied production logger can pass its sink gate.

Run from this repository root, with MAIN containing the pinned source snapshot and design inputs:

```sh
python3 benchmark/2026-10-20-t29-consumer-test-peer/replay.py \
  --source-root "$MAIN" \
  --out "$HOME/.local/share/westlake/t29-consumer-test-peer/new-baseline"
```

Compare a ready CC method package with its actual C logger:

```sh
python3 benchmark/2026-10-20-t29-consumer-test-peer/replay.py \
  --source-root "$MAIN" \
  --consumer-source-dir "$CC_CONSUMER/derived" \
  --extra-source "$CC_CONSUMER/logger/observe29c.c" \
  --include-dir "$CC_CONSUMER/logger" \
  --out "$HOME/.local/share/westlake/t29-consumer-test-peer/new-comparison"
```

`--extra-source` and `--include-dir` are repeatable. C logger sources compile as C11, consumer TUs as C++17. Each raw argv/stdout/stderr/rc and input snapshot is retained under the requested new output directory. Missing inputs, compilation failure and behavioral mismatch are failures; no candidate argument yields `BASELINE_PASSED_DERIVED_PENDING`.

Baseline facts that must not be silently repaired by observation: attach/detach do not reject `released` when state/image remain valid; update does reject it. Producer replacement first destroys the old field, including aliases, then calls the real getter once. Reference/unreference errors do not change the original field-write policy. Existing exceptions remain present. The fixture tests these actual behaviors rather than imposing a new policy.

Two Python tests exercise the real compile/run path, a same-source comparison control, semantic-oracle rejection and missing-source rejection. The Rust wrapper and strict lifecycle pass. `baseline-observations.json` and `results.json` report the stable baseline. `partial-comparison.json` records only a transient, incomplete CC snapshot: SurfaceTexture changed, TextureView still identical to the original. Its behavior matched, but it is not final instrumentation acceptance.

Limitations: host seams do not establish production ABI, JNI runtime races, device provider instances, logger budget/sink correctness or playback. Final method observation must separately check each method's phase/called/valid mask and separate ref/unref return fields. Arbitrary WL-R29 output is not coverage evidence. CC retains logger concurrency/budget testing ownership. No production build or device operation was performed.
