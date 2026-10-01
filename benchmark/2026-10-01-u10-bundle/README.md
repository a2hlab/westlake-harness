# U10 assembly over signed U9

The first host candidate turned a lazy application lookup into a fatal namespace fence. Outer review rejected it. This replacement uses cx-bms host r2 from master `e04a108bc`: only resident/default views are queried with NOLOAD, the helper is optional, and application lookup is deferred. No application-view NOLOAD is compiled.

## Composition and identities

Persistent package: `$WORKSPACES/westlake-inputs/generations/u10-j37465d6d-c015aa3a6-p621caec4-v3/bundle`. Old v1/v2 directories are evidence only, explicitly not for deployment.

- JAR: `37465d6d`; U11 JAR `277d4641` is excluded.
- Rebound host: `71901abc`, two builds identical. Actual U9 child `dc73a28d` and runtime generation `74d1d6d4` retained.
- Compat: `015aa3a6`, both Android and route-a aliases.
- NativeLoader policy: `621caec4`, both aliases, adds only `libstdc++.so` to the shared policy.
- Exactly six board paths differ: host, JAR, and two aliases each for compat/policy. ART/provider/child/bridge/runtime/27 images/stubs/installer remain U9 bytes. OpenSLES and libjnigraphics are deferred to U11.
- Runtime and boot references are regenerated from the full signed U9 effective view, including JAR/image overlays; rollback does not accidentally use the older U8 reference.

`composition.json` records the complete native manifest and bundle SHA. `composition.json.identity_count` is the 172-path declared bundle view. `expected-run.json` expands the native effective view and installation chain to each board's 318 assertions / 316 unique paths. Runtime fingerprints (123 files): 5ea/5cd `fe5d9e139746`, 61b `519148f0f41a`; their installer libinstalls bytes still differ. Boot (36 files): all `4db882a81732`. These are offline predictions, not observed activation.

## Checks and limits

Fresh ABI/calls: host only adds `U10ShareResidentCompat` at `StockCreateConfiguredNamespaces`; policy only changes the two six-to-seven template readers; compat adds `__gnu_strerror_r` and `android_dlopen_ext`, zero changed common calls. No removals, signature drift or consumer breaks. Twelve exact pinned DSO consumers pass; the current VM Firefox APK differs from the pinned input, so this does not certify that changed full APK. See `consumer-replay.json`.

Artifact identity passes for all six changed board paths, including both aliases. Freeze check: 8 entries, 44 source/package/fingerprint checks, zero violations. N1/N2: 154 semantically identical findings registered automatically, plus the two outer-approved r2 NOLOAD sites (lines 13/29), all 156 bound to this manifest in master `eea0e3acc`. No application-view finding remains. Production dry-run now passes G1/G2, N1/N2 for candidate and U9 rollback, and frozen checks; rollout-ready remains false pending window review. The earlier refusals remain on disk as evidence. No board was accessed by U10. Three-board proposals are in [window/README.md](window/README.md); testing always rolls back U9. Public dry-run snapshots normalize recording paths; raw originals remain in the durable directory.

Host build closure: 107 resolved source/header/object/library/map inputs, 6,329,633 bytes; trace relink reproduces `71901abc`. The original pinned compiler SHA and commands are recorded. Sources and recipes are persisted with `source-SHA256SUMS.json`, compiled objects and twelve exact consumers under `build/`. Reused objects are explicit, not represented as a clean full rebuild. Archived source relocation can change debug paths and requires ABI/call verification before use.

## Reproduction

Run `build_host.py --out <fresh-build>` (default r2 receipt), then `prepare.py --host <fresh-build>/appspawn-x-1 --out <fresh-bundle>`. Both require the exact recorded compiler and retained input object hashes. `archive_build.py` captures the actual resolved closure. Any absent or drifted input fails rather than substituting a newer generation.
