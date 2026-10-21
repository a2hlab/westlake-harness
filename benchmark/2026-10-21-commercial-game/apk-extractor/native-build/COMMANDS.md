# Replay the actual G09 production recipe

Native-03 was executed by outer(codex), not by an inner Orb retry. Keep one build executor. Its exact private argv is `G09_PRIVATE/exact-launch-native-03.argv.json`; do not rerun it because those scratch/log directories already exist. No device command is part of this card.

Restore the exact kit archive and real host libxml2 listed in `inputs.lock.json`. Use the repository's accepted G08 sources/patch, Linux x86_64, Python 3.10+ and ccache. Choose new persistent scratch/log directories. The compiler, linker and Ninja come from the kit; never substitute a system compiler.

```sh
# From the repository, preserve this command's actual stdout/stderr/rc:
python3 scripts/lab/check_frozen.py --git
# FROZEN_STDOUT points at that successful original stdout, not a reconstructed message.
python3 "$G09/build_native.py" \
  --archive "$EXACT_KIT_ARCHIVE" --scratch "$NEW_SCRATCH" --logs "$NEW_LOGS" \
  --g08-dir "$G08" --frozen-receipt "$FROZEN_STDOUT" --apk "$EXACT_APK" \
  --host-lib-dir "$PINNED_HOST_LIBRARY_DIRECTORY"
python3 "$G09/check_receipt.py" --build-run "$NEW_LOGS"
G09_BUILD_RUN="$NEW_LOGS" cargo test --manifest-path tools/spec-checks/Cargo.toml \
  --test commercial_game_extractor_build commercial_game_extractor_build_receipt -- --exact
```

`G09` is this directory; `G08` is its parent. Supply variables explicitly. The host-library directory must contain exact real `libxml2.so.16` bytes (`2fc8478b…`); recipe SHA-checks it and records actual `ldd` paths/hashes. It makes no system-library symlink and no shared mount change.

The original 246 command arguments are preserved. The effective 247 arguments differ only by the proven debug compilation directory option; both arrays are recorded. Cache is disabled, the old zip object is removed, and baseline compilation must reproduce the complete original object before Ninja can link. Baseline library must reproduce the complete original library before the patch is applied. Only the new scratch ThinLTO cache is cleared. Candidate uses the same effective compile and link commands. Any failure stops, retaining dual streams and rc.

`native-01` (object mismatch), outer `metadata-probe-01` (exact reproduction), `native-02` (missing linker host library), and `native-03` (complete build) are different immutable executions. The earlier exact argv files are historical receipts, not recommended retries. Final recipe SHA is in `results.json`; no pending process should run while changing it.
