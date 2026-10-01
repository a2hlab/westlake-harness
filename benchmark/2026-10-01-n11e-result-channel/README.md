# N11e: host-rendered sealed-loader diagnostics

The N11d probe was silent, so its missing output could not distinguish a loader branch from a failed logger. This candidate carries diagnostic fields through the existing host-allocated result and emits them through the already observed host `APPSPAWN` channel. It is a diagnostic candidate; no load failure has been repaired and a diagnostic-only 61b window was completed, then fully restored to U9.

- Child: `3f1e703ca0dfc7cd78300e955166e6da65f4cab69d8316c2c751b8406aa757f4`, two builds identical.
- Baseline: `163da805` reproduced byte-for-byte, including the three rebuilt loader/plugin/manifest objects.
- Internal result ABI: 1 → 2. The original seven fields occupy the same 40-byte prefix; new size is 216 bytes. Loader, plugin and generated manifest share one header. A V1 request receives only prefix writes; ABI/size mismatches remain explicit errors. The runtime-provider public ABI is unchanged.
- Two real-C tests pass: prefix bounds and old-caller canaries; diagnostic errno/branch/index propagation and 159-byte NUL termination; retry clearing; retained fatal `EMIT_RESOLVE`; unconditional entry marker and absence of dynamic TLS.
- Frozen check: frozen: 8 entries, 36 checked, 0 violation(s); (see the recorded output for its exact count). Package changes only the child path. ART, runtime-provider, bridge, JAR and images retain U9 bytes.
- Native preflight: 154 identical approved findings plus two outer-review findings. All 156 findings were approved in master `d68062ff3`; production native dry-run passes. See `outer-review.json` for the intentionally retained N11b namespace behavior.

## Sources and construction

Design: master `bd7a65e84`, corrected by outer ACK 21:47 and master `670a6e7fe`: `benchmark/2026-10-01-n11b-r3-loaderror-analysis/n11e-log-channel.md`. Those corrections override its earlier instruction to delete the logger gate and to use `_Thread_local`.

Loader baseline: `benchmark/2026-10-01-n11b-early-owner/src/sealed_child_provider_loader.c`, SHA `2b5d18d1dad0e083354d56d38e7911e9ef97be9c6ad70136376e0fe76586e4d8`. Host plugin, header and generated manifest come from the retained `westlake-harness-bms-deploy/bms/src/.work/b68-generation/adapter/framework/appspawn-x/security_specialization/stock_child_plugin` source and recorded `out/target/logs/commands.txt`. Recompiling those original objects reproduced their pinned N11b SHA before using the new header. `build.py` reuses the exact remaining link objects and frozen compiler.

Persistent candidate, sources, commands and SHA inventory: `$WORKSPACES/westlake-inputs/generations/n11e-u9-result-channel-v2/`. The first build directory is retained: its plugin selected the original transitive header and failed on missing new fields; the second build forces the common header before all transitive includes. No assertion was relaxed.

## ABI and call-graph evidence

`abi-calls.json`: zero added/removed exports, zero signature drift, zero consumer breaks. SONAME and NEEDED unchanged (`libwestlake_android_child.z.so`, only `libc.so`); no TLS segment or TLS symbols.

Three common functions change calls. `LoadSealedProviderAfterHooks` adds `WlascGateMarkerText` and `snprintf`; `RealOpenLocalNow` adds the failure recorder and errno access. `WLSCPL_LoadSealedProvider` gains diagnostic copies and calls the existing `Fail` cleanup; the compiler outlines cleanup that was previously a direct `dlclose` in this function. The source `Fail` cleanup loop and `RealCloseHandle` are unchanged; this is not removal of cleanup. The complete call report is retained, rather than described as a one-function change.

`EMIT_RESOLVE` (:333) remains fatal and records branch 4 before `dlclose`. Branches 1/2/3 distinguish inheritance, owner NOLOAD and handle mismatch; branch 5 records artifact or owner-preload failure. Diagnostic state is ordinary file-static storage. The host unconditionally emits `[N11e-PROBE] entry`, and emits `fail stage/branch/index/errno/detail` on the existing failure return.

## Diagnostic window and restoration

The outer loop authorized an entry-marker, child-SHA and unchanged-U9-fingerprint activation gate; controls were advisory and no shards ran. Continuous capture began before deployment. Both spawns reached branch 3, index 0 (`liboh_adapter_bridge.so`): the default lookup returned a non-NULL handle different from the JNI owner. This establishes a handle mismatch, not when or where the default copy was first loaded. The `libartbased.so` detail can be stale from an earlier optional lookup; it is not a demonstrated cause. Branch 4 was not reached.

Exact marker lines: [probe-lines.txt](window61b-r1/probe-lines.txt). Candidate facts and restored-control facts are in [ack.txt](window61b-r1/ack.txt). The first restore smoke encountered a residual SceneBoard session and did not spawn HelloWorld; the byte rollback had already succeeded. Reinstall retry passed. Both restored t20 screenshots show their own interfaces; facts report 2/2 captures and alive=yes for each control.

[Final U9 verification](window61b-r1/recovered-final/final-u9.json): 318 assertions / 316 unique paths, no differences or absent paths; runtime `a2919b793eb6`, boot `4db882a81732`, child `dc73a28d`, boot unchanged. Recovery maps retain U9's ART/JVM single copies and bridge/runtime two copies. Lock released at 22:26; `held` empty. This is a diagnostic conclusion, not a repair or a retained candidate.
