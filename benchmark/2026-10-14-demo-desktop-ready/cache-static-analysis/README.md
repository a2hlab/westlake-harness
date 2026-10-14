# Actual SceneBoard persistent icon cache

**The three stale placeholders are stored in the actual SceneBoard EL1 `Launcher.db.icon_info` cache, which the actual packaged bytecode consults before BMS. Restarting SceneBoard clears memory but reloads this persistent value.** Updating BMS master rows and sidecar PNGs alone does not invalidate these cached rows. This conclusion is specific to the captured SceneBoard HAP; it must not be generalized to other launchers.

The copied HAP SHA-256 is `9c11b9f038b9ada284d039af5b156746c3c5fd57faf363b1ca4085289d3612a2`; its `ets/modules.abc` is `4fa98da8a77465cb423f5c0011dbf45a49814bebc86fe7d2ed4ee71be7052443`. The installed SDK `ark_disasm` completed with exit 0, empty stdout/stderr. REA binary tools were unavailable in this active session; no REA success is claimed. `actual-artifact-pins.json` pins the tool, original DB/WAL/SHM, bytecode, and complete assembly.

## Actual packaged consumption chain

The `abc-functions/*.pa` files are exact function excerpts from the completed assembly; filenames are the original assembly start line. `abc-functions-index.json` records full identifiers and bounds.

| Function | Assembly evidence | Result |
| --- | --- | --- |
| `MainAbility.initIconResourceCache` | [6220426.pa](abc-functions/6220426.pa) | Adds `memoryCache`, then `dbCache`; initializes `bundleManagerFwk` as fallback. |
| `AppIconResConfig.loadIconResourceByCache` | [1955037.pa](abc-functions/1955037.pa) | Passes bundle/module/ability/appIndex to `IconResourceManager.getCombIcon`. |
| `IconResourceManager.getCombIcon/getCombineIcon` | [1161515.pa](abc-functions/1161515.pa), [1161598.pa](abc-functions/1161598.pa) | Iterates cache list, accepts nonempty `combinePicSrc` subject to version guard, fills earlier cache, returns it. Calls `getAppIconDirectly` only after misses. |
| `DbCache.createRdbStore` and callback | [1166252.pa](abc-functions/1166252.pa), [1170735.pa](abc-functions/1170735.pa) | Opens the database in EL1, configured MAIN_REPLICA. |
| `DbCache.getTableName/getIconResource` | [1167773.pa](abc-functions/1167773.pa), [1167236.pa](abc-functions/1167236.pa) | Selects normal `icon_info`, queries exact bundle/module/ability, reads `COMBINE_PIC`, converts base64 to pixel map `combinePicSrc`. |
| `BundleManagerFwk.getIconResource` | [1174766.pa](abc-functions/1174766.pa) | The framework fallback calls BMS `getLauncherAbilityResourceInfo` or `getBundleResourceInfo`. |
| `IconResourceManager.deleteIconResource` | [1159514.pa](abc-functions/1159514.pa) | Existing per-bundle invalidation deletes from cache list in reverse order and can send `EVENT_ICON_RESOURCE_REFRESH`. This is an in-process API, not an exposed shell command. |

The copied DB was analyzed only after duplicating all three DB/WAL/SHM files. WAL was applied normally; original received files were not modified. uNote, PostWriter and Tasks have **six rows**, two per package, all with identical 10,042-character `combine_pic`: data URI SHA `c57e7b16cecf7f724906310a11d9cc6350a9ae11435bac378931f7016be655bf`, decoded 7,514-byte PNG SHA `3554d69ae22fe60a485a56e6099cb873943fc34f461b42898d2f8e42c5c0fc7f`. The decoded [image](cached-placeholder.png) was visually inspected: blue grid background with a white four-petal placeholder.

`launcher-three-icons.json` provides exact six keys and field hashes. `launcher-eight-icons.json` expands the check to all eight repair packages: **17 icon rows and 8 current grid ability keys**, preserving nulls and all unrelated field values. BMS should prepare its existing exact compare-and-swap and rollback workflow against these keys; it must validate fresh row values because this is a captured snapshot. No whole database replacement, all-cache deletion, slave write, foundation restart, or HAP rewrite is justified. Clear only the matching process-memory entries (through a supported app path, or the already bounded outer SceneBoard process refresh after exact persistent updates). Final screenshots remain required; **no repair was executed or accepted by this analysis lane**.

## Earlier candidate analysis (superseded where indicated)

The public applications_launcher 6.0 HAP-resource route below was a candidate before actual SceneBoard arrived. Actual bytecode above establishes its own persistent cache and BMS fallback, so the public candidate is not the root-cause evidence. The normal NativeRdb master-versus-slave analysis remains supporting source evidence, with deployed native equality unknown.

The original hypothesis, “the old BMS slave database explains the old icon after restarting SceneBoard”, is not supported by the normal NativeRdb query path. Thirteen pinned upstream source files establish the branches below. They are reference implementations, **not a proof of equality with the deployed binaries**. No device command or production mutation was performed by this analysis lane.

## Evidence

1. BMS configures MAIN_REPLICA, but `RdbDataManager::QueryByStep` calls the normal `RdbStore` query. `RdbStoreImpl::QueryByStep` creates a `StepResultSet` with `pool->AcquireRef(true)`; `StepResultSet` calls normal `CreateStatement`. Reader and writer connections share the configured path. Normal statements use `dbHandle_`; `CreateReplicaStatement` is an explicitly separate path. See `rdb_data_manager.cpp:551`, `rdb_store_impl.cpp:1526`, `step_result_set.cpp:82`, `connection_pool.cpp:430`, and `sqlite_connection.cpp:578`. A stale slave is compatible with external SQLite updates bypassing replication; it is not evidence that normal reads use the slave.
2. BMS launcher resource getters read `bundleResource`, then can override icons from matching dynamic/theme `bundleIconResource` rows (`bundle_resource_manager.cpp:174–215`). The copied database in `../cache-readonly/` has no `bundleIconResource` rows. Normal row conversion reads ICON text (`bundle_resource_rdb.cpp:495–518`). No icon-value memory cache has been identified in the examined manager path; this does not prove that every deployed caller lacks caching.
3. Official `applications_launcher` takes a different candidate route: `ResourceManager.ts:106–145` retrieves `getMediaBase64(iconId)` from a module context after a cache miss. `updateIconCache` first returns when a cached value exists, otherwise obtains a drawable or media from the module resource manager (`70–102`). If the actual SceneBoard uses this route, process restart can reload the unchanged HAP placeholder. **Actual SceneBoard linkage is still unknown.**
4. Do not infer persistence from a class name: the pinned launcher's `DiskLruCache` uses `Map`, and `initMap()` is empty. It contains no filesystem persistence. This corrects an initial provisional interpretation of its name.
5. Actual EL1 evidence now identifies `phone_sceneboard/rdb/Launcher.db` (7,028,736 bytes) and a nonempty WAL (3,790,432 bytes). `UpdatedIcon`, `image_file_cache`, and theme `cache_json` are empty in the captured listing. EL2 emptiness cannot rule out this EL1 data. The actual module is `/system/app/SceneBoard/SceneBoard.hap`; see `../launcher-cache-el1-list/bundle.txt` and `directories.txt`.

## Reproducibility

`source-pins.json` records all original upstream paths, commit pins, SHA-256 values, and sizes. BMS and NativeRdb use OpenHarmony 6.1 release commits; the public launcher reference uses its available 6.0 release branch and is explicitly unbound to the running SceneBoard. Original Apache-2.0 headers are retained. `results.json` separates established source facts, actual read-only observations, and unknowns.
