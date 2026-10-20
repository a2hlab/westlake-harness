# Exact compiler replay (offline only)

The existing Linux es2abc is pinned by `inputs.lock.json` (`d20db2d4…`). The available Mac compiler generated nonmatching baseline ABCs; those outputs are retained under `.private/baseline-mac-01`. Orb read-only path probe timed out after15s; Docker socket access returned permission denied. No permissions or shared services were changed.

Run the same checked-in source on the existing authorized Linux tool channel, with paths visible **inside that environment**:

```sh
python3 "$LANE/benchmark/2026-10-20-toutiao-launcher-page/compile_abc.py" \
  --compiler "$OH_SDK/ets/build-tools/ets-loader/bin/ark/build/bin/es2abc" \
  --out "$PERSISTENT_FRESH_OUT"
```

`LANE` is this isolated checkout; `OH_SDK` is the already available historical SDK. The program hashes the compiler and all source inputs, rejects a reused output, retains argv/stdout/stderr/rc, requires both old ABCs byte-identical, then compiles only the new Index. No install/sign/deploy/device step is included. Return the output directory (including raw, receipt and ABCs); the next local signing step will recheck every pin. A baseline mismatch is a refusal, not an exception.
