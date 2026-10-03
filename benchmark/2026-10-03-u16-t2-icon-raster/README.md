# U16 t2: rasterize XML-only adaptive launcher icons into the desktop tile (frequent-habits)

#90, offline prototype, no deploy. Per `specs/u16-batch/t2-icon-raster.spec.md`. frequent-habits is `app_failed`
because its launcher icon is a vector-only `<adaptive-icon>` the installer can't rasterize → a placeholder tile →
the runner never finds/clicks it. This pins the layer, defines the minimal fix (rasterize the vector layers),
ships a working offline rasterizer prototype, gives the FZ-001 frozen argument, and scans the corpus.
(`design/design-note.md` = layer + fix + frozen; `recipe/raster_adaptive_icon.py` = the prototype;
`evidence/` = the rendered icon + corpus scan.)

## The layer, and its current handling of `res/*.xml` icons
The **installer** (`libapk_installer.so`, **FZ-001**) — not BMS or the hap toolchain — produces the tile icon:
`apk_installer.cpp::ReadIconByManifest()` → when `android:icon` resolves to an XML drawable, calls
`adaptive_icon.cpp::ComposeAdaptiveIcon()`. That function **already composes** `<adaptive-icon>` with PNG layers
or a solid-colour background (via `lodepng`), **but vector-drawable layers are unsupported**: `ResolveLayer`
(`adaptive_icon.cpp:116-132`) logs *"nested XML (vector) unsupported"* and returns `false` → `ReadIconByManifest`
falls back → `ClassifyIconlessApk` → **DECLARED_XML_ONLY** → template **placeholder**.
frequent-habits' `<adaptive-icon>` layers are **both vector** (`res/0w.xml` black bg, `res/Qr.xml` purple
ring/check) with **no raster launcher icon in any bucket** → placeholder → no tile → `app_failed`.

## The minimal fix — rasterize the vector layers (offline chain, no new on-device native dep)
Extend the `ResolveLayer` vector branch to **rasterize the `<vector>` drawable** instead of returning false:
parse the compiled vector (viewport + `<path>` `pathData`/`fill`/`stroke`/caps/alpha), emit the equivalent **SVG**
(`pathData` is SVG path syntax; `#AARRGGBB`→`#RRGGBB`+opacity; cap 0/1/2→butt/round/square), rasterize with the
**existing Mac rasterization chain (`rsvg-convert`)**, hand the raster layer to the existing `ComposeAdaptiveIcon`
compositor + `icon_normalize` full-bleed. Done **offline / at install-prep** so **no new native dependency is
added to the on-device `libapk_installer.so`** (the prep pre-rasterizes; the on-device compositor consumes raster
layers it already supports). Non-XML / PNG-layer / colour-bg / raster-bucket paths are untouched.

## Prototype — works (`recipe/raster_adaptive_icon.py`, `evidence/frequent-habits-icon/`)
Run on frequent-habits it produces `icon.png` **108×108, non-transparent** — the app's real purple-ring/white-
check icon (VectorDrawable→SVG→`rsvg-convert`→composite; `icon.svg` is the intermediate). Satisfies spec
acceptance scenario 1 (iconPath→PNG, exists, ≥48×48, non-transparent). **Fallback (scenario 3):** a non-XML icon
→ `raster-skip` (raster path unchanged); a non-`<adaptive-icon>` XML / a vector with no paths / an `rsvg-convert`
failure → `raster-failed: <reason>` + `rasterized:false` (caller keeps the XML placeholder; install not broken) —
demonstrated in `evidence/fallback-*.log` + the synthetic no-paths case.

## Frozen? YES (FZ-001) — "add feature, preserve old behaviour"
`libapk_installer.so` (7048c7c5) is in FZ-001 (status `frozen`). The change is **additive**: the only existing
path it alters is the `ResolveLayer` vector branch that **today returns `false`** (dead-ends to placeholder).
Every other path is **byte-identical** — raster `android:icon`, adaptive-icon with a PNG layer or solid-colour
bg, and any icon resource with a raster bucket (the arsc resolver still prefers the raster). So FZ-001's four
evidence apps (Tusky, K-9, Thunderbird, File Manager) take the identical path; START_ABILITIES_FROM_BACKGROUND is
untouched. Register as reason **extension** (new behaviour added, old kept) after a single-board reverify of the
4 FZ-001 apps + frequent-habits with zero regression (installer `foundation` restart USB risk = outer's window).

## Beneficiaries (`evidence/corpus-scan.txt`)
- **Confirmed +1 testable key: frequent-habits** — the only `app_failed` cluster (U16 cluster S); its icon is
  vector-only-no-raster; the prototype rasterizes it to a correct tile.
- **Corpus: 60 apks** have an XML/vector top-density launcher icon (59 adaptive-vector-only + 1 plain-vector) —
  the literal "XML-only icon" count. But **most already tile** via a raster bucket or a raster launcher-alias
  icon (wikipedia/fd-notes/fd-calendar/anki/… are lit despite vector top-density icons), so the currently-
  placeholdered set is small; **frequent-habits is the one confirmed by run outcome**. (A second "desktop icon
  absent" mention, privacyfriendlyminesweeper, was outer-marked "not an app run" and has a raster icon → a
  transient launcher miss, not counted.) The fix additionally composes a correct icon directly from the vector
  art for all 60, covering any future vector-only-no-raster app.

## This round's rule
The tile icon is the **installer's** (`ComposeAdaptiveIcon`), which already handles PNG/colour adaptive layers;
the only gap is **vector layers** (the `ResolveLayer` `return false`). Fix exactly that one branch — rasterize via
the existing offline `rsvg-convert` chain (no new on-device native dep) — and nothing else changes, which is what
makes the FZ-001 "extension, old behaviour byte-identical" argument hold. Count beneficiaries by **run outcome
(app_failed)**, not by a top-density-icon scan: 60 apks are vector-icon but only the no-raster-anywhere subset
(confirmed: frequent-habits) actually lacks a tile.

## Files
- `recipe/raster_adaptive_icon.py` — the offline VectorDrawable adaptive-icon rasterizer (the prototype/install-prep step).
- `recipe/icon_corpus_scan.py`, `recipe/icon_refine.py` — the corpus XML-icon scan + per-resource raster-config refine.
- `design/design-note.md` — layer, current handling, the fix, FZ-001 extension argument, verification plan.
- `evidence/frequent-habits-icon/{icon.png,icon.svg,icon-record.json}` — the rendered tile + record;
  `evidence/raster-run.log`, `evidence/fallback-*.log`, `evidence/corpus-scan.txt`.
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline prototype; no deploy; no push; the frozen `libapk_installer.so` is **not** edited here (the fix is the
design + the offline prototype; the on-device change + registration are the outer's, FZ-001 extension path).
On-board tile location + t20 content are the outer's (spec scenario 2, human review). Sources read read-only: the
installer source (`westlake-harness/bms/.../package-manager/jni/{apk_installer,adaptive_icon,icon_normalize}`),
the APKs (`westlake-inputs`), the frozen registry (`westlake-harness/knowledge/frozen/frozen.json`), the U16
cluster + stage-A decision (`westlake-harness`).
