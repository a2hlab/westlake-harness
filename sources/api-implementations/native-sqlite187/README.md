# Exact SQLite JNI source units

The old Boat libandroid has four weak SQLite registrars that return success without registering methods. These eight files are the **actual t2c runtime187 compiler inputs**, not that shim and not guessed upstream replacements. Every copied byte matches the 6,347-file inventory recorded in [source.json](source.json). Apache headers are retained; no license is inferred for a file without one.

`android_database_SQLiteConnection.cpp` registers 27 SQLiteConnection methods. The CursorWindow, SQLiteGlobal and SQLiteDebug files implement the other three registrars. `AndroidRuntime.cpp` contains their registration dispatch. This delivery adds implementation files to the repository; it does not vendor all AOSP/OH headers, SQLite, link objects or compiler dependencies.

Use the existing [runtime build instructions](../../../benchmark/2026-10-10-adapter-buildchain/README.md), [cold preparation](../../../benchmark/2026-10-10-adapter-buildchain/prepare_runtime_cold.py), and their pinned archive inventory. In a restored scratch workspace:

```sh
python3 benchmark/2026-10-10-adapter-buildchain/prepare_runtime_cold.py --workspaces "$WORKSPACES" --out "$REPRO_RUN"
DOCKBUILD_MOUNTS="$WORKSPACES/westlake-harness-bms-deploy:$WORKSPACES/westlake-harness-t3" "$WORKSPACES/westlake-inputs/tools/dockbuild.sh" run -n t2c-runtime-next -- bash "$REPRO_RUN/run.sh" > "$REPRO_RUN/build.stdout.txt" 2> "$REPRO_RUN/build.stderr.txt"
```

The first command prepares the original producer; it does not compile. The full build consumes the retained author-path layout and toolchain. Historical runtime187 two-build equality remains in its original receipts. No build was run for this source delivery. Final V2 f28 uses the later split graphics unit, whose separate recipe preserves this SQLite source set.
