# Native host-window recovery candidate — actual build receipts

**Five actual object compilations and one link completed with rc0. This is an offline, untested-on-device candidate, not a successful white-screen repair.** The linked `liboh_adapter_bridge.so` is 2,150,152 bytes, SHA `158c174067853fd357c1ab2d7dd6a4374684f08d22712bde62018aac8e6a7822`.

| Unit | Actual local time (+08:00) | Object SHA prefix | Result |
| --- | --- | --- | --- |
| WMC | 13:39:16–13:39:24 | 50bb8edb7ccd | rc0 |
| Input | 13:39:24–13:39:28 | b6e7b7792b59 | rc0 |
| Stage | 13:39:28–13:39:33 | a6114502feb4 | rc0 |
| Recovery core | 13:39:33–13:39:35 | 032f0987df21 | rc0 |
| Reader (separate continuation) | 13:40:39–13:40:43 | f2ec096821bc | rc0 |
| Link | 13:41:15–13:41:15 | 158c17406785 | rc0 |

The outer handoff reports that the first wrapper raised `FileExistsError` while creating the fifth output directory: `reader/` already held the reader source. It had **not started reader compilation**. The four successful object receipts were retained, and `reader-build/` was used for the separate reader compilation. The supplied tree has no standalone wrapper traceback/terminal receipt: this interruption is explicitly attributed to the outer handoff, its wrapper rc remains unknown, and it is not mislabeled as a compiler failure or omitted from the history.

## Source and artifact binding

This review independently rehashed the five objects and final library against their receipts, the five link object pins, and all 13 snapshot inputs. The current peer candidate manifest (`review-01-B1-side-table-parent-cache`) contains nine source/header/include files; all nine match both the fixed snapshot and current peer bytes. The four extra snapshot entries are the t1 reader source/header, JSON header and MIT license; all match main t1 bytes. This comparison is pinned in `results.json`, not a promise about later author edits.

The `.d` files show the compiled WMC and stage use the snapshot candidate headers, and all relevant units use the snapshot recovery/reader headers. Full depfile SHA and bounded matching line references are retained in the recipe. WMC/Input/stage emitted `LOG_TAG` redefinition warnings; core and reader have only their transport preamble in stderr. Link stdout/stderr are empty. All original streams and receipts are indexed, unchanged.

## Reproduction records

`recipe.sanitized.json` preserves all six complete argv arrays, working directories, environments, the five original VM transport argv arrays and terminal receipts. It records the exact link delta against the byte-identical baseline original-object link. `$SNAPSHOT`, `$STAGE`, `$PEER`, `$MAIN` and home aliases replace personal paths; substitute them as argv strings for a future authorized replay, not by executing an unreviewed shell expansion. Keep the reader source and output directories distinct. Use fresh outputs and retain stdout/stderr from process start.

The recipe depends on the existing staged compiler, SDK/header closure and unchanged baseline objects from `benchmark/2026-10-24-wmc-build-preparation/outer-baseline-01/`; the latter includes the fixed 792 SDK system-header addition. Only the three changed integration TUs plus two new units were compiled here. Remaining bridge objects were reused; no whole-bridge source rebuild is asserted.

Private originals are under `$HOME/.local/share/westlake/native-host-recovery-build-20261024/snapshot-01/`. `raw-index.json` pins files rather than publishing binaries or full build stderr. This lane only read/hashed receipts and generated this small evidence increment: zero compilation, VM/remote/device calls, source changes or Git writes. No on-device child-read, SSM recovery, surface reuse, input behavior or feed result is established by these build receipts.
