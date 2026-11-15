# module-fd probe

Tests whether Westlake's loaders take a module through a descriptor path (ADR-0005). A Play host can hand its clients module files as read-only descriptors, which a client names `/proc/self/fd/<n>`. The probe opens its own APK read-only and, through that path only, loads:

- its `Marker` class, with a `PathClassLoader` whose parent is the system class loader, so the class can only come from the descriptor;
- the same class with a `DelegateLastClassLoader`, the loader Play services' module loader uses;
- its asset `wl-marker.txt`, with an `AssetManager` given the descriptor path.

It prints one line per test (`[WL-MODFD-PROBE] <name> = <value>`) and `verdict = PASS_ALL` when all three pass. Native libraries inside an APK (`<apk>!/lib/<abi>/...`) are not tested, since the probe has none.

    ./build.sh      # out/module-fd-probe.apk (pure Java, one asset)

## First run (2026-11-14, framework 262)

Every test passed. The path is a file of the APK's length. Both class loaders defined `Marker` themselves, and the asset manager added the path (cookie 2) and read the asset.
