# OH 6.1 V7 SceneSession bridge source snapshot

- Owner: `Bridge/src/adapter`
- Target: OpenHarmony 6.1.0.31, AOSP 14, ARM64 only
- Historical source:
  `/opt/10.Project/16-WestLake/16.12-HanBing/_YUETRACK/adapter`
- Frozen source anchors before the two fixes:
  - `oh_window_manager_client.cpp`: MD5 `b2133b5b08e048d2aaa64722954a37f1`
  - `session_stage_adapter.cpp`: MD5 `8a5a299418b8e9eaf94bf3ea07887bc7`
- Build recipe and 6.1.0.31 header mirror:
  `/opt/10.Project/16-WestLake/16.13-Yue/local-arm64-build`
- External inputs are toolchain/sysroot/source headers only. All compiled
  adapter code and the resulting artifact remain in this directory.

The generation changes exactly two runtime behaviors:

1. Resolve the Java peer at `adapter/window/SessionStageBridge` and clear a
   failed lookup exception.
2. Keep `WindowSessionProperty.tokenState` equal to whether the final remote
   token argument is non-null.

The `ScheduleMemoryLevel` and
`NotifyAppForceLandscapeConfigEnableUpdated` declarations are expressed with
their OH 6.1.0.31 ABI signatures (one argument and zero arguments,
respectively). These match the already-deployed `a5be507c` bridge and are build
compatibility declarations, not additional generation behavior changes.
Four callbacks newer than the 6.1.0.31 `ISessionStage` vtable are retained as
plain no-op members without `override`, also matching `a5be507c`.

ART, boot jars, appspawn-x, package-manager libraries, and application payload
are not built by this recipe.
