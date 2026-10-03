# U16 t2: rasterize XML-only adaptive launcher icons in the installer — design

## The layer (where the desktop tile's icon is produced)
The **installer** (`libapk_installer.so`, FZ-001), not BMS/the hap toolchain, produces the published icon:
`bms/src/adapter/framework/package-manager/jni/apk_installer.cpp :: ReadIconByManifest()` resolves the
manifest `android:icon` to the highest-density arsc entry and, when that entry is an XML drawable descriptor,
calls `adaptive_icon.cpp :: ComposeAdaptiveIcon()` to compose a PNG; on failure it falls back to
`ClassifyIconlessApk` → **DECLARED_XML_ONLY** → the template **placeholder** icon.

### Current handling of `res/*.xml` icons (the gap)
`ComposeAdaptiveIcon` (`adaptive_icon.cpp`) already composes `<adaptive-icon>` into a PNG with `lodepng`:
- background: a PNG layer **or** a solid `TYPE_INT_COLOR_ARGB8` fill — handled;
- foreground: a **PNG** layer — handled.
- **vector/webp layers: NOT handled.** `ResolveLayer` (`adaptive_icon.cpp:116-132`): if a layer reference
  resolves to a nested `.xml` (a `<vector>` drawable) it logs *"nested XML (vector) unsupported"* and returns
  `false`; `DecodePngToRgba` fails on non-PNG. → `ComposeAdaptiveIcon` returns false → `ReadIconByManifest`
  falls back → DECLARED_XML_ONLY placeholder.

frequent-habits hits exactly this: its `<adaptive-icon>` (res/BW.xml) layers are **both vector drawables**
(`res/0w.xml` = black bg square, `res/Qr.xml` = purple ring/check), and the APK has **no raster launcher icon
in any bucket** → placeholder → no desktop tile → `app_failed` (the app never launches; `aa start` works).

## The minimal fix — rasterize the vector layers (offline, existing chain, no new on-device native dep)
Extend the installer's adaptive-icon path so the `ResolveLayer` **`.xml` (vector) branch rasterizes the
`<vector>` drawable** instead of returning false:
1. Parse the compiled `<vector>` (viewport + `<path>` elements: `pathData`, `fillColor`, `strokeColor`,
   `strokeWidth`, `strokeLineCap/Join`, `fillAlpha/strokeAlpha`, optional `<group>` transforms).
2. Emit the equivalent **SVG** (`pathData` is SVG path syntax; Android `#AARRGGBB` → `#RRGGBB` + opacity;
   `strokeLineCap` 0/1/2 → butt/round/square) and rasterize with the **existing Mac-side rasterization chain
   (`rsvg-convert`)** to an RGBA buffer.
3. Hand the rasterized layer back to the existing `ComposeAdaptiveIcon` compositor (fg src-over bg → PNG), then
   the existing `icon_normalize` full-bleed pass. Set `iconId`/`iconPath` to the produced PNG.

Per the spec, rasterization runs **offline / at install-prep (APK-side)**, so **no new native dependency is
added to the on-device `libapk_installer.so`**: the install pipeline pre-rasterizes the vector layers and the
on-device compositor consumes raster layers it already supports. The `ResolveLayer` change is therefore "if the
layer is a vector, use the pre-rasterized PNG the prep step produced" rather than `return false`.

### Prototype (this benchmark) — `recipe/raster_adaptive_icon.py`
A standalone offline rasterizer implementing steps 1-3 (VectorDrawable→SVG→`rsvg-convert`→composite). Run on
frequent-habits it produces `evidence/frequent-habits-icon/icon.png` — **108×108, non-transparent**, the app's
real purple-ring/white-check icon (viewed). Fallback (spec scenario 3): a non-XML icon → `raster-skip` (raster
path unchanged); a non-`<adaptive-icon>` XML or a vector with no paths or an `rsvg-convert` failure →
`raster-failed: <reason>` + `rasterized:false` in the record (caller keeps the XML placeholder; install not
broken). Acceptance scenario 1 (iconPath→PNG, exists, ≥48×48, non-transparent) is met offline.

## Frozen? YES — FZ-001 (`libapk_installer.so` 7048c7c5). "Add feature, preserve old behaviour"
The installer is frozen (FZ-001 artifacts: `libbms.z.so` 6aadb8b4, `libapk_installer.so` 7048c7c5, status
`frozen`). The change is **additive**: the only existing code path it alters is the `ResolveLayer` vector branch
that **today returns `false`** (a dead-end → placeholder). Every other path is byte-identical:
- `android:icon` is a raster (PNG/webp) → unchanged;
- `<adaptive-icon>` with a PNG layer or a solid-colour background → the existing `ComposeAdaptiveIcon`/
  `DecodePngToRgba` path, unchanged;
- the icon resource has a raster config at any bucket → the arsc resolver still returns the raster (preferred),
  unchanged.
So FZ-001's four evidence apps (Tusky, K-9, Thunderbird, File Manager — all raster/alias-raster icons) take the
identical path and their START_ABILITIES_FROM_BACKGROUND behaviour is untouched. Per AGENTS 做事方式 3 /
FROZEN.md the outer registers a new version for reason **extension** (new behaviour added, old kept), after a
single-board reverify of the 4 FZ-001 evidence apps + frequent-habits with zero regression; the installer
`foundation` restart (USB risk) is the outer's to window. New-version registry note: version bump + `change` +
previous version in `history`.

## Beneficiaries (evidence/corpus-scan.txt)
- Confirmed currently-placeholdered → gets a correct tile after the fix: **frequent-habits (+1 testable key)** —
  the only `app_failed` cluster (U16 cluster S).
- Corpus: **60 apks** have an XML/vector top-density launcher icon (59 adaptive-vector-only + 1 plain-vector);
  most already tile via a raster bucket or a raster launcher-alias icon (wikipedia/fd-notes/fd-calendar/etc. are
  lit), so the fix removes their dependence on that and directly composes from the vector art, and covers any
  other vector-only-no-raster app that would otherwise placeholder.

## Verification plan (on board — not run here)
1. install-prep rasterizes frequent-habits' icon → the installer publishes the PNG (iconId/iconPath set).
2. U16 window: launch; the desktop tile is present and matches → runner clicks → app process + t20 (icon located;
   t20 content judged by the outer). 3. Reverify the 4 FZ-001 apps unchanged (zero regression) before registering.
