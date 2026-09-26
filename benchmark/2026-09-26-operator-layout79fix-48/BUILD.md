# Build & apply the relayout width-clamp (#48 Layout -79)

The fix is a source change to `WindowSessionAdapter.java` (package `adapter.window`,
the sole `IWindowSession.relayout` override). Patched source + unified diff are in
`src/`. `oh-adapter-runtime.jar` is dex, non-BCP, architecture-independent — a jar
rebuild, not a native/boot-image rebuild.

## Route 1 — canonical source rebuild (preferred; needs $BRIDGE_SRC/$BRIDGE_ARM64)
1. Apply `WindowSessionAdapter.relayout-clamp.patch` onto the westlake adapter tree
   at `$BRIDGE_SRC/.../adapter/framework/window/java/WindowSessionAdapter.java`
   (the tree whose build emits the `[OH_WSA-relayout]` logs; the local base-adapter
   source it was cut from is md5 db49ecca867897f20beb823da13263b5).
2. Rebuild the adapter jar with the normal framework build (the same step that
   produces `${BRIDGE_ARM64}/fwjars/oh-adapter-framework.jar` /
   the non-BCP `oh-adapter-runtime.jar` — whichever your westlake build packages
   WindowSessionAdapter into; confirm with:
     `unzip -p <jar> classes*.dex | strings | grep -c OH_WSA-relayout`).
3. `sha256sum` the rebuilt jar; run `scripts/assert_relayout_clamp.sh <jar>`.
4. Overlay onto the staged framework (webview-t-lib / framework stage), warm 5x.

## Route 2 — surgical smali patch (if only the DEPLOYED jar is in hand, no rebuild)
Arch-independent, no framework classpath needed. Tools present on this Mac:
baksmali/smali 2.5.2 (orca/workspaces/westlake-inputs/tools + SDK 3.0.9), d8.
1. `baksmali d <deployed.jar-or-classesN.dex> -o out-smali`
2. Open `out-smali/adapter/window/WindowSessionAdapter.smali`, find `.method public
   relayout(...)`. Right after the two locals equivalent to
     int width  = requestedWidth>0  ? requestedWidth  : sessionInfo[3];
     int height = requestedHeight>0 ? requestedHeight : sessionInfo[4];
   (they feed the `[OH_WSA-relayout] ... -> useWH=` println), insert the clamp:
   for each axis, `if-le vWidth, 1` -> load static sLastGoodWidth (add the two
   `.field private static volatile sLastGoodWidth:I` / `sLastGoodHeight:I` to the
   class), `if-gt` cache>1 move into the width local; on the healthy path
   `sput` width/height into the cache. Mirror the else-branch display-maxBounds
   fallback + the DEGENERATE println. Keep register count consistent (bump
   `.locals`). The Java in `src/WindowSessionAdapter.java` is the reference.
3. `smali a out-smali -o classes.dex`; replace the dex in the jar (`zip <jar>
   classes.dex`); sha256sum; `scripts/assert_relayout_clamp.sh <jar>`.
NOTE: register allocation is per-build, so Route 1 (source rebuild) is preferred and
less error-prone; Route 2 is the fallback when only the binary jar exists.

## Assert
`scripts/assert_relayout_clamp.sh <jar>` PASSes when the jar's dex contains the
`DEGENERATE session rect` clamp marker AND the `-> useWH=` relayout log (proving it
is the relayout-logging adapter, i.e. the deployed-matching version) AND `getMaxBounds`.
