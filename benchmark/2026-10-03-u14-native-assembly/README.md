# U14 bridge-only disabled assembly: U13 contents are not the transaction baseline

The prior mistake was treating an unpromoted comparison package as the deployed transaction baseline. This draft has two independent identities: **assembly contents = accepted U13 `91272eaf`**, while the **explicit transaction baseline = currently signed U10.1T8 `190afedd`**. No VM, board, lock, deployment, new build, active-registry write or production replay was performed. A successful report collector is not a successful native gate.

## Pins and composition

| Item | SHA256 |
|---|---|
| Disabled bridge-only bundle | `90de6c7e405667dfc3900ab2960a440a2e72f3c704b919d36f96e869f66b1199` |
| Native manifest | `231525cee3f0ac309a273b79088f3e85a649e535d70d1dbf083fddd4baab3113` |
| Native gate inputs | `ed41df0c85c803624a5d924bb796b9bb4ba9c6362a8d7404a6adc07b40cc972b` |
| Selected bridge, both donor builds | `7daa5435333ab99c2360dfe5ad5b75180ba0b8118d4f69f6750764c01b546452` |
| Replaced bridge | `84695d62f515cfec6bb317c959ec55b1d5085bf82303f792a764cf549a22267a` |

Persistent draft: `$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u14-native-assembly/.artifacts/u14-bridge-only-t8/`. Public manifests and `composition.json` bind it. **Exactly one payload member differs from U13: the root bridge.** Host remains `2a87118e`, runtime `18763dd4`, runtime JAR `bbc3f530`, stubs `615b8bbe`, and U13 images remain untouched. Relative to real T8, preparation has 316 baseline / 319 candidate paths, three additions and 41 replacements. This is an offline transaction plan, not a promotion assertion.

The selected bridge includes inherited e34 R1/R2/R3 changes, **not just M5/M6 relative to 846**. Optional bridge `438bc948` is not selected: accepted U13 runtime `18763dd4` already provides the M1 cross-copy window routing. Donor report `benchmark/2026-10-03-u14-bridge-m5-m6/README.md` has an explicit correction to its older no-M1 prediction; use the correction, not its outdated heading. No new measured app gains are claimed here.

## Explicit baseline, never a default

```sh
python3 benchmark/2026-10-03-u14-native-assembly/assemble.py \
  --transaction-base "$WORKSPACES/westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle" \
  --transaction-base-sha256 190afedd3ddb250752e67b83d19669b6a952eb04cd69db5edf0b06eafe119736 \
  --board-baseline "$WORKSPACES/westlake-harness/benchmark/2026-10-02-u12-final-assembly/recovery-u101t8.json" \
  --out benchmark/2026-10-03-u14-native-assembly/.artifacts/u14-bridge-only-t8
```

The output is immutable: use a new directory for another baseline. Required CLI arguments validate the full bundle SHA, three signed fingerprints and the supplied effective comparison targets; derive runtime/boot references and each of 36 image comparison members from that supplied effective baseline; and call transaction preparation against that baseline's native inventory. This does not replace executor full-native identity validation. Outer 03:30 identified two **61b-local libinstalls** copies (`51e1b525` rather than the common T8 native `2c9a5294`): its dedicated effective baseline is the next task, not silently repaired or approved here. After U13 actually promotes, supply U13's effective bundle and its newly signed board evidence. **Do not silently change this draft's baseline merely because U13 was authorized.** Recompute transaction/static deltas and binding-dependent IDs; additions that are already deployed disappear from that transaction. Slot changes also require a new immutable assembly and fresh gates.

## Fresh Mac evidence, including refusals

All raw outputs have portable copies in `evidence/`; original private output paths and SHA256 are in `report-summary.json` / `details-summary.json`. `deployed-whois-transaction.txt` uses the exact supplied T8 generation; the earlier default whois output explicitly covers historical U9 signed maps only. Signed T8 recovery evidence establishes the actual baseline owner bytes; a historical maps lookup is not current mapping proof.

| Check | Fresh result |
|---|---|
| Ordered DT_NEEDED | **35 unchanged**, no dependency added or removed |
| New UND against 846 | Four, all matched to pinned direct NEEDED providers |
| New UND against e34 | Only `WindowSessionProperty::SetSubWindowZLevel(int)` |
| ABI/calls/consumers | 0 export removals, 4 export additions, 0 signature drift, 219 consumers / 0 breaks; 3 changed call sets |
| Function-normalized diff 846→selected | 2696 common; 2690 equal + 3 residual-equal; 3 changed; 0 missing / 13 new functions |
| Function-normalized diff e34→selected | 2708 common; 2703 equal + 3 residual-equal; 2 changed; 0 missing / 1 new function |
| Open sites | Three on both sides; 0 namespace edges; **DEFAULT-NS 3 and UNRESOLVED 1 retained** |
| U13 native gate | PASS, 55 N1 / 104 N2 approved |
| Candidate active native gate | **REJECT: 94 N1 + 104 N2 unbound**; 159 prior findings match, 39 newly covered N1 rows need review |
| Auto-identical CLI | Exit 3; 159 preview rows, **no `--apply`** |
| Static against U13 | **REJECT**, one ADR diagnostic delta pending review |
| Static against real T8 | **REJECT**, same ADR delta plus three same-object admission bindings not yet active for this manifest |
| VM / production / execution | Deferred / not run / disabled |

The three inherited e34 imports are `DisplayManager::RegisterDisplayListener`, `WindowSessionProperty::SetRequestedOrientation`, and `SetPersistentId`; M5 adds `SetSubWindowZLevel`. The scene provider is cached factory `libwindow_scene_common.z.so` **`9551c7fe2617e032ac0b999695230076331ea644eb0bcf5bb3cbda971ebe2c8f`**, with a GLOBAL DEFAULT FUNC export of size 8 at `0x37560`. Display listener is provided by direct `libdm.z.so` **`ad0137edaf5cdd21641172b8ff6d22b6924f9065adbd0a49804efeb73ee4b218`**. The report reads their exact input-pinned ELF copies, not similarly named SDK libraries. See `imports.json` and provider dynsym outputs. Consumer checking proves only the intersection with replaced bridge exports, not runtime namespace reachability or app gain.

Changed call/function bodies are display width/listener (e34), `createSession` (M5), and `ScheduleAbilityTransaction` (e34 + M6). Every removed-callee set is empty. Fresh normalized comparisons and ABI results retain the inherited changes rather than hiding them under a two-function patch claim.

### ADR diagnostic is not a new loader operation

Raw preload paths are `unknown:adr x0, #-135412` → `unknown:adr x0, #-135984`; the scanner does not currently resolve this ADR. `adr-proof.json` and three raw preload disassemblies independently read the pointed-to ELF rodata: **all resolve `libmali.so.0`, `mov w1,#0x102`, `dlopen`, caller-default**. The two existing runtime lookups retain NOW|NOLOAD then NOW fallback. Namespace APIs and literals have no changes. This is a narrowly scoped proof, not a rewrite of scanner output or a single-owner claim.

Production delta **`87ed7281bbc4375ec5fa65ec42767a38205680aade4538ff84800fa5c915fbea`** remains pending in `static-allowance-draft.json`, with `approved_by=null`. No blanket literal normalization or allowance was applied.

### New N1 coverage is visible

The old bounded manifest did not include bridge sources. This draft adds four actual compilation inputs for namespace checks and one bounded JNI-order entry profile. `needs-outer-review.json` retains **5 unknown + 34 unresolved external-call rows**:

- Existing input-channel runtime NOLOAD at `inputs/u14-bridge-input.cpp:72`.
- Inherited orientation GetStaticMethodID at `inputs/u14-bridge-ability.cpp:471`, and existing generic GetMethodID at `:335`.
- M6 `OhTokenRegistry.findByOhToken` and `isDestroying` at `:163` / `:165`; the custom class-loader helper is not resolved by the current bounded scanner.
- 34 unresolved external calls/macros, listed verbatim in `n1-review-summary.json`.

These are **not 39 proven regressions, and not zero findings**. The helper/class/order assumptions need outer review. `registry-delta.json` contains only 159 identical prior findings as an unapplied preview; `new-native-admissions-draft.json` provides three same-byte U13 object binding previews, also unapplied. No active registry, old approval or production policy has been edited.

### Strings remain a review list

Raw `deployed_strings_diff` exits 1 for all three comparisons: 846→e34 **9 drop / 23 add**, e34→selected **4 drop / 14 add**, 846→selected **9 drop / 33 add**. `strings-review.json` retains every row and gives source lines where text matches. M5/M6 contribute eight source text strings (including an IPC macro-concatenated format); remaining readelf-rendered read-only layout runs are **pending review**, not silently allowed or labeled zero by filtering. Display-listener/orientation text belongs to inherited e34. Source/patch/function evidence permits a scoped review; it does not make the raw strings tool green.

## Slots and provenance

`slots.json` holds two native slots and the JAR slot **unapplied**: app-ns host (cc-wiki), ICU wall-two (cc-wiki), runtime JAR v1 `0349eb83` (cc-t3). Since assembly, outer approved ICU plan b and added Gecko native-ABI and Bluetooth stubs to the planned final U14 batch; `pending-batch-extensions.json` tracks them without changing payload. Final stubs `87cf65cc` need paired image rebaking. No missing candidate is filled with a guessed donor. This is not the final U14 native version.

`provenance.json` binds donor source commit `854c05ae0f50dd61c4da5d355683b35449159aa9`, all **50 compiled source/object pairs**, exact driver, five ordered patches and both teed build logs. The actual window cohort is donor `window-jni/`, not the nearby canonical legacy source. Four scan snapshots are byte-identical to their compiled input bytes. Source closure and headers remain persistent under `$WORKSPACES/westlake-inputs/generations/u14-m5m6-m5m6-{a,b}` and logged persistent input roots. Recipe snapshots are path-portable, with both original and snapshot hashes.

Donor artifacts a/b both equal `7daa5435`; this lane **did not rebuild**. Recipe-path clang/clang++/lld/ar hashes are observed now and explicitly labeled as such: the historical donor log does not independently pin their tool hashes. Do not infer an exact historical compiler identity solely from a path. This provenance limitation is visible rather than fabricated.

## Checks and handoff

```sh
python3 benchmark/2026-10-03-u14-native-assembly/reports.py
python3 benchmark/2026-10-03-u14-native-assembly/details.py
python3 benchmark/2026-10-03-u14-native-assembly/test_assembly.py
cargo test --manifest-path tools/spec-checks/Cargo.toml --test u14_native_assembly
```

The collector preserves expected refusal outputs; unit tests verify the disabled contract, including rejection of baseline drift/unreviewed extra members and cold operation without `.artifacts`. Outer reviews the pending rows, then assembles remaining donors into **one final native version** and rebinds against the then-signed effective transaction baseline. VM/production replay must be fresh after the window; no historical green output or prior authorization can arm this draft.
