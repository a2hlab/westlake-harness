# Patched adapter-runtime-bcp.jar — #48 Layout -79 clamp (smali surgical)

## Artifacts
- patched jar:  adapter-runtime-bcp.CLAMP48.jar
    sha256 ea5d8b277f1207c928d289196876ad69505d73ab586815daccbda7080169523e  (202502 bytes)
    inner classes.dex sha256 c5bd7fd23b0ed5c8a6d2b8dce0bd387f899b6fd0b58f5423314c3e90983d35cf  (498388 bytes, dex version 039)
- baseline (codex-2 board): adapter-runtime-bcp.jar
    sha256 5731db00562e3b814cfb4d4e32703c40c9e8726a022b28da155fd040fb59019a (198155 bytes)
- WindowSessionAdapter.patched.smali  (full patched class)
- WindowSessionAdapter.smali.clamp48.diff  (smali diff: 0 deletions, 114 additions)

## Where the real logic lives (dex is newer than the .java source)
The deployed jar's relayout() is a thin WindowRelayoutResult wrapper that delegates to
**relayoutLegacy(...)** — that legacy method holds the width/height computation, the
OH_WSA-relayout logs and outMergedConfiguration. It also REFACTORED the width/height
resolution into a static helper: width/height =
resolveRelayoutDimension(attrsDim, requestedDim, sessionInfo[3|4])  (returns
requested>0?requested : attrs>0?attrs : session). On the collapse this returns 1.

## The clamp (smali), functional equivalent of WindowSessionAdapter.relayout-clamp.patch
1. Two static fields added:
     .field private static volatile sLastGoodWidth:I
     .field private static volatile sLastGoodHeight:I
2. Two static helpers added (clampWidth48(I)I / clampHeight48(I)I): if arg>1, cache it
   and return unchanged; else return the cached last-good (>1); else fall back to
   Resources.getSystem().getConfiguration().windowConfiguration.getMaxBounds().width()/
   height() (>1); else return the arg unchanged. Emits a one-line
   "[OH_WSA-relayout] DEGENERATE session rect <axis> clamped [#48 Layout:-79 guard]"
   when it clamps.
3. relayoutLegacy caller: right after each main resolveRelayoutDimension result
     move-result v10   (width)  -> invoke-static clampWidth48(v10)  -> move-result v10
     move-result v11   (height) -> invoke-static clampHeight48(v11) -> move-result v11
   Reuses v10/v11; no new caller registers; .registers unchanged. The clamp sits BEFORE
   the value is consumed by the useWH log, winCfg, outFrames, the IWindow.resized
   reverse-push, and outMergedConfiguration (all read v10/v11).

## Per-axis cache vs source's paired gate (intentional, equivalent)
The .java source cached only when BOTH width>1 AND height>1; the smali caches each axis
independently (width>1 caches width). Functionally equivalent and slightly more robust:
each axis is restored from its own last-good. On Toutiao only width collapses (to 1);
height stays 1920.

## Validation (all local, arch-independent; NOT deployed)
- smali assembled clean (smali 2.5.2, -a 29) -> dex version 039 (matches baseline).
- round-trip baksmali of the patched dex succeeds (structure + bytecode well-formed).
- diff prepatch->patched: 0 deletions, 114 additions (purely additive/surgical).
- healthy 1200 path byte-identical: clampWidth48(1200) hits if-le p0,1 == false ->
  sput cache + return p0 (1200 unchanged) -> outMergedConfiguration still 1200x1920.
- scripts/assert_relayout_clamp.sh: ALL PASS (9/9) — OH_WSA-relayout + -> useWH= (deployed
  match), clampWidth48/clampHeight48, sLastGoodWidth/Height, DEGENERATE marker, guard tag,
  getMaxBounds.

## Deploy (codex-2): this is a BCP jar
adapter-runtime-bcp.jar is on the boot classpath -> stage via boot-image rebuild (not a
webview-t-lib overlay). Overlay the patched jar in place of the baseline, rebuild the boot
image, warm 5x, expect no "Layout: -79 < 0"; a "DEGENERATE ... CLAMPED" log line is proof
the guard fired.
