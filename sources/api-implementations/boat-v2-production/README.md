# Boat V2 production source and replay

The historical NATIVE-138 package delivered deployment scripts, not the production sources of its three
private libraries. Calling all three a missing Unity engine source was inaccurate. This package supplies
the actual production-version signal shim and extracts the already validated transformations without
importing or invoking any device code.

| Component | Original signed SHA prefix | Delivered implementation | New execution |
|---|---|---|---|
| C7 `libunity.so` | `1bea0fae` | Fixed original engine input plus signal rename, two dependency edges and three exact instruction patches | Exact output match, rc0 |
| C4 `libil2cpp.so` | `f6b806b5` | Fixed BoatAttack game-generated input plus signal rename and two dependency edges | Exact output match, rc0 |
| `libwestlake_bionic_signal_box.so` | `7a931c79` | Two original C units, header, export map, real compile/link/strip argv | Compile/link/strip rc0; new `0987e589`, comparison rc2 |

`build.py` is the executable offline entry. It requires exact sources and dependency hashes, a fresh output
directory and explicit input paths. `check` performs only the small source lock verification.

```sh
S=sources/api-implementations/boat-v2-production
python3 "$S/build.py" check
python3 "$S/build.py" transform --apk "$BOAT_APK" --patchelf "$PATCHELF" --out "$NEW_TRANSFORM"
python3 "$S/build.py" signal --sdk "$OH_SDK_NATIVE" --out "$NEW_SIGNAL"
```

Exit **0** means all produced hashes equal the signed expectations. Exit **2** means compilation completed
but at least one output differs. Exit **1** records an actual precondition/process failure. Never replace
the signed signal library with this newly built file merely because its source compiled.
Each tool invocation records its argv, raw stdout/stderr hashes, timestamps and actual return code.
Aliases `$SOURCE`, `$OUT`, `$OH_SDK`, `$BOAT_APK`, `$PATCHELF` in receipts refer to explicit CLI inputs.
Raw streams and binary outputs are preserved in the closeout archive; no historical logs are invented.

The new signal file differs in 19 bytes, all within `.note.gnu.build-id`; every other ELF section and the
file size match. This narrows the output mismatch, but is not a new runtime test or historical provenance
proof. The historical tool invocation/debug paths are unknown; the old build-id was not copied into the
new output. The source used here is `bb7732fa…`; MAIN's U10/U12 snapshots are `ddae7366…` and are not silently
substituted. Both two-unit production source behavior and its export namespace are preserved unchanged.

See [DEPENDENCIES.md](DEPENDENCIES.md) for fixed inputs and acquisition, [source.lock.json](source.lock.json)
for provenance, and the [execution results](../../../benchmark/2026-10-14-verified-source-closeout/boat/results.json).
The independent game project recipe in `project/` exposes the original upstream commit, camera patch,
Unity version, package locks and Editor method. No large Unity build was run here and no engine source
license acquisition is required to replay the already signed C7/C4 transforms.

## Licensing and scope

`project/LICENSE.md` preserves BoatAttack's original Unity Companion License notice. Unity editor/runtime
inputs remain separately licensed dependencies. The inspected Westlake signal-source directory has no
standalone license notice; origin and exact Git blobs are retained, and no new license is invented here.
No signing credentials, APK, compiled SO or toolchain binary is committed. The shared bridge8ab, JAR633,
ADC and f28 runtime are separate components and were not modified or rebuilt by this lane.
