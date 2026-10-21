# G30 baseline execution checkpoint 01

The original Linux compiler has not produced an observable receipt. One exact baseline launch timed out at the client after 35 seconds (recorded rc124, empty stdout/stderr). The isolated output directory/receipt was not present at collection time. No candidate compilation was attempted. A timeout is not a baseline mismatch or proof that the VM command never began; check for delayed execution before any subsequent launch.

The fixed `build_baseline.py` compiles both original N4 source objects, links with the original version script, and refuses any full-library SHA other than d205. Sources are independent exact copies; the historical tree is read only. Flags preserve original DWARF compilation/source paths. Dependency files and linker trace are emitted into the isolated new output. This metadata mapping has not yet been tested by this run.

Exact private launch: `$REPO/benchmark/2026-10-21-commercial-game/locale-abi-candidate/.private/launch-baseline-01/argv.json` (JSON `argv`). Intended output: sibling `.private/baseline-01`. The launch invokes the existing a2hlab Linux compiler, not a replacement compiler. No service restart, privilege change or automatic retry was attempted.

The frozen check ran rc0: 8 entries, 30 checks, zero violations. It is the existing repository frozen registry check; exact baseline source/tool SHA checks are independently embedded in the build recipe. Full header/link input closure still depends on a completed actual build. Current pinned ELF DWARF was read locally to retain the original compilation identity. No original source, G26 host/ANL or earlier delivery was modified.
