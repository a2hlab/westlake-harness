# Fix (proposal) — mcdonalds: add com.mcdonalds.app to the already-in-U12 private-zlib whitelist (one line)

Owner to integrate: cx-bms (route-A host lineage). cc-wiki delivers the exact edit; NOT landed to bms/src here.
Verdict: **ALIVE**. Layer: **native namespace** (per-package private closure via the host, NOT a root alias).

## What is missing (static)
`librealmc.so` (com.mcdonalds.app's own Realm native lib) has `DT_NEEDED libz.so`; the app musl namespace cannot
resolve `libz.so`, so `dlopen_ns` fails (hilog:30948 `MUSL-LDSO: Error loading shared library libz.so (needed by
librealmc.so)`; hilog:30968 androidx.startup ULE), and the DI graph is never built -> the :31141 NPE. The missing
thing is **libz.so visibility in com.mcdonalds.app's namespace** — a namespace/path gap, not a missing symbol.

## The one line — add the package to the westlake_native whitelist
The private-zlib route (IN U12 final: DIGEST 682 `private zlib50b9/ab082+host2a871`) already prepends
`/system/android/lib64/westlake_native` (which holds the r109c `libz.so` alias, SONAME=libz.so NEEDED=libshared_libz.z.so,
donor SHA 50b9ab6a; provider libshared_libz.z.so SHA ab0820c6) to the search/permitted paths of WHITELISTED packages.
Current whitelist (`missing-library-route.h` MissingLibraryRoot, westlake_native branch):
```c
    const char *packages[] = {"im.vector.app", "com.emn8.mobilem8.nativeapp.bk"};
+   const char *packages[] = {"im.vector.app", "com.emn8.mobilem8.nativeapp.bk", "com.mcdonalds.app"};
```
(Apply against whatever the DEPLOYED U12 host 2a87118e actually carries — the u12-private-zlib `route.patch` is the
reviewed r3 version; add the one package string there. No other change.)

## Why NOT a root alias (keep the scoping)
A root `/system/android/lib64/libz.so` is FORBIDDEN (DIGEST 459, the N7/ZigZag regression: libtuanjie finds the root
libz shell first, its dep libshared_libz.z.so invisible -> `inflateInit2_: symbol not found` -> SIGABRT). The per-package
host route only exposes westlake_native to the named packages, so ZigZag/others are untouched. Adding com.mcdonalds.app
stays within that safe scoping.

## Prediction (move + evidence)
- **First fatal MOVES.** With westlake_native on com.mcdonalds.app's search path, `librealmc.so` resolves `libz.so`
  (the r109c alias -> libshared_libz.z.so provider), `dlopen_ns` succeeds, androidx.startup InitializationProvider
  succeeds, the DI graph builds, and the :31141 `DataSourceHelper.getOrderingManagerHelper` NPE in
  `SplashActivity.onCreate` no longer fires.
- **Next fatal / t20: UNKNOWN.** librealmc may have further unmet deps/symbols beyond libz (BurgerKing's libmmkv only
  needed crc32, which libshared_libz.z.so exports; librealmc's full import set is not inspectable from the hilog alone
  -> confirmation gap: read librealmc.so's DT_NEEDED + undefined before the window, or let the window show the next wall).
- Acceptance before any window: N1/N2 on com.mcdonalds.app's namespace resolving libz->private provider, the
  `[U9-LIB-ROUTE] ... root=/system/android/lib64/westlake_native` activation marker, and HelloWorld/ZigZag still lit
  (guard the former root-alias regression).
