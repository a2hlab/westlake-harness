# #48 Toutiao BCP jar handoff for Layout clamp

The exact board artifact containing `adapter.window.WindowSessionAdapter` is **adapter-runtime-bcp.jar**, not a file named oh-adapter-framework.jar and not framework.jar. This read-only handoff does not deploy a patch or start the app. Board: `61b0657200000000000000000324012c` only.

## Exact original and shared copy

- Actual runtime root: `/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d`
- Exact board jar: `<runtime>/fw/adapter-runtime-bcp.jar`
- SHA256: `5731db00562e3b814cfb4d4e32703c40c9e8726a022b28da155fd040fb59019a`, 198155 bytes.
- Shared Mac **and VM** path: `/Users/zhaoyue/orca/workspaces/westlake-harness-framework48/benchmark/2026-09-26-toutiao-framework-handoff-48/adapter-runtime-bcp.jar`.
- Device framework candidate `/data/local/tmp/a2hlab-framework-operator45-v7/fw/adapter-runtime-bcp.jar` has the same SHA. The actual app runtime copy is authoritative for this handoff.
- `framework.jar` was also pulled to this directory (local shared file, gitignored, 16201098 bytes), SHA `4a3d1688fe3753e7ac5164d2404cca3be1217c698ad7ce8383238713be44b0dd`.

`jar-class-proof.json` records a DEX **class_defs** check: `adapter-runtime-bcp.jar/classes.dex` defines `Ladapter/window/WindowSessionAdapter;` plus five nested classes, and contains the OH_WSA-relayout marker. None of those class definitions are in framework.jar. Board SHA and pulled bytes match. This is not a filename inference or merely a reference-string match.

## Actual BCP and image evidence

`launch-config.json` shows source_app_namespace starts the runtime's run.sh. The helper bind-mounts the runtime root onto `/data/local/tmp/asx` in its private mount namespace (source_app_namespace.c lines 37–41). Therefore the child's `/data/local/tmp/asx/fw/...` resolves to the exact runtime above; no system partition file replacement is involved.

`parent-bcp-image.txt` is extracted from the current board parent.log, the last hollow run (parent13011/child13042). It records:

- BCP order: core-oj, core-libart, core-icu4j, conscrypt, okhttp, bouncycastle, apache-xml, framework, **adapter-runtime-bcp**.
- Physical BCP: `/data/local/tmp/asx/fw/<name>.jar`.
- Logical dex locations: `/system/framework/<name>.jar`.
- `-Ximage:/data/local/tmp/asx/boot/boot.art`.
- Successful loading of all nine image components, including `boot-framework.art` and **boot-adapter-runtime-bcp.art**.

No live process was started to inspect a class loader; this combines current on-board file SHA, actual saved parent startup/image-load logs, and DEX class definitions. Historical hollow child logs contain the OH_WSA-relayout output. Do not label this a new clamp runtime validation.

## BCP staging method (not executed in this handoff)

The existing #38 staging scripts, `../2026-09-25-ability-focus/scripts/stage38.py` and `stage_timeline38.py`, stage **fw jar + matching boot/*.art/.oat/.vdex as a set**, run the framework preload check and update the report. They are documentation references: their old board IDs/timeouts must not be copied into this board61 task without adapting the bounded helper.

1. Patch this exact adapter-runtime-bcp.jar, preserving the other adapter classes and existing #38 behavior. It is boot-class-path code; adding a child runtime overlay cannot replace the class already resolved from the boot image.
2. Rebuild the matching affected boot image set using the westlake host dex2oat (oat247), the actual nine-jar BCP and unchanged logical dex locations. Keep compiler-filter=verify, the existing arm64 target/base, and all other jars unchanged. This is required boot-image consistency work, **not the withdrawn app speed-AOT/JIT experiment**. No native-runtime chain rebuild is needed.
3. Back up the current actual runtime jar and boot image set before any deployment. Stage a separate candidate framework directory, check matching jar/image hashes, then update the app runtime's `fw/adapter-runtime-bcp.jar` and corresponding `boot` set together while parent/child are stopped. Merely editing `/data/local/tmp/a2hlab-framework-operator45-v7` does not update the existing app runtime copy. Preserve native patch libraries, run.sh, consent/data and guardian stop markers.
4. Next launch must show correct BCP/image loading and new clamp behavior, then run the authorized five warm rounds including ArticleInflow. Do not use an old boot image or claim a jar copy alone proves the clamp is running.

The prior host image invocation is archived in `../2026-09-25-ability-focus/evidence/build/appvis/boot-image.log`; it uses source-closure host dex2oat, nine `--dex-file/--dex-location` pairs, `--instruction-set=arm64 --compiler-filter=verify --base=0x70000000`, and `/system/framework/arm64/boot.oat` as the oat location. Use current board inputs, not the old build inputs by name alone.

## State and verification

No board mutation, app launch, data reset, AOT installation, or JIT cache setup occurred. pidof app/appspawn-x was empty. Actual shim85c789f4, hollow npth9966e296 and run.sh ffb324e4 remain unchanged. `board-hashes.txt` includes all nine jars and 27 image-component hashes for the follow-up rebuild, plus baseline checks. Previous memsponge/mc/sysopt and consent are untouched. R2=verified for artifact identity/BCP handoff; clamp behavior remains untested.
