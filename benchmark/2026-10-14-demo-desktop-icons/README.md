# Desktop artwork: exact resources, not placeholder tiles

## Evidence first

The incorrect assumption was that a desktop tile, a successful click, or an
`android/icon.png` filename proves original artwork. It does not. Ten XML-selected
APKs had the same 6,790-byte four-flower template, SHA
`53ce1f45f81705a84f05aa0d6956a64180d1fd6984a79b7a784f3931a311bd6f`.
Eight are retained; JsLab and K-9 are excluded by the T0 inventory. The three
received sidecars and both PNG members of each corresponding HAP matched that
template byte-for-byte. The original APKs instead contain distinct vector art.

`evidence/before-audit-final/results.json` binds the T0 inventory, before desktop
layout, resource-selection CSV and original 128 records. Inventory SHA is
`0594a19c3d8d36b4630b68c27b7d35243eb763f1860330fb903ff0cb7bc33714`:
116 keep, one protected Toutiao route and 13 remove. All 130 exact tile identities
occurred in the sampled before pages, including the explicit IME host launch
package for Route B. This is not a claim that partial paging exhausts the desktop
or that every current icon/label is matched by bytes.

The original 128 resource selections match all 128 APK hashes: 102 PNG, 16 WebP,
10 XML. Historical `desktop` clicks are distinct from ability fallbacks.
CircuitTraining, BeeCount and SimpleNotes now have root's actual desktop-click
and visible-startup evidence in
`benchmark/2026-10-14-demo-desktop-ready/manual-launch-3/outer-visual-review.json`.
This closes those three launch-path gaps only, not function/stability acceptance.

## Original artwork candidates

The existing U16 XML-to-SVG-to-`rsvg-convert` install-preparation method is reused;
no native runtime or installer is rebuilt. `render_known_icons.py` handles the
first three exact resources, including tint, alpha, group transforms and solid
background references. `render_five.py` adds only the source constructs needed
by the five remaining packages: clip paths and line caps, vector backgrounds,
and a solid shape background. Unsupported constructs fail rather than inventing
artwork. Every candidate is 256x256; SVG preserves source viewports and aspect
ratio. The PNGs themselves were viewed individually without portrait stretching.

| Package | Source-selected artwork | Candidate |
|---|---|---|
| app.varlorg.unote | `res/r2.xml`, original notebook vector | `candidates/app.varlorg.unote.png` |
| com.alxgnon.postwriter | adaptive color `#FF26A69A`, white tinted foreground | `candidates/com.alxgnon.postwriter.png` |
| org.tasks | adaptive color `#FF2196F3`, `res/Gg.xml` check mark | `candidates/org.tasks.png` |
| com.kaajjo.libresudoku | adaptive dark background, original outlined grid | `five-candidates-r2/com.kaajjo.libresudoku.png` |
| com.lcdcode.moodcairns | original clipped colored stones and smiling face | `five-candidates-r2/com.lcdcode.moodcairns.png` |
| com.paperknifeplus.app | original light background/red arrow vector | `five-candidates-r2/com.paperknifeplus.app.png` |
| com.groce.app | historical selected `res/Ps.xml`, solid dark shape/cart vector | `five-candidates-r2/com.groce.app.png` |
| org.fossify.calendar | original green vector background/white calendar | `five-candidates-r2/org.fossify.calendar.png` |

Each directory contains decoded XML, SVG and receipts with APK/resource/renderer
hashes. Both generations were repeated and receipts/PNG hashes were identical.
The Groce selection is the historical installer's resource-table selection, not
an unrelated density filename chosen by counting directories.

## Bounded metadata transactions

Actual read-only master DB schema is `bundleResource(NAME PRIMARY KEY,
UPDATE_TIME,LABEL,ICON,SYSTEM_STATE,FOREGROUND,BACKGROUND)`. First three packages
have 80 rows (10/2/68); remaining five have 49. `prepare_cache.py` generates exact
full-row compare-and-swap SQL, read-only main-DB verifiers, original row backup
and reverse full-after-CAS SQL. Only ICON and FOREGROUND change. Labels, all other
columns, unrelated rows and the other resource tables remain unchanged.

Real 60 MB disposable-copy replay results:

- First three: 80 changed, 3,261 non-target rows have identical digest; rollback
  restores all 3,341 original row tuples exactly.
- Remaining five: 49 changed, 3,292 non-target rows have identical digest;
  rollback likewise restores all rows exactly.
- SQL/table snapshots and received DB/WAL/SHM stay under `.artifacts` or MAIN,
  **not Git**. Reproduce using pinned inputs and the checked-in compiler.

`execute-three.sh` is frozen at
`caf56ca759592b9bb35b0dc56da502f5d9735096d0ef70b9a735ac60408dde8c`.
`execute-five.sh` differs only in the exact package list, PNG hashes and 49-row
count. Both default to preview, enforce current boot/root/private staging,
source hashes and sidecar metadata, use same-directory atomic replacement, and
attempt exact rollback on failure. Unknown resource rows or foreign sidecar
content are not overwritten. HAPs are deliberately untouched: no signature
assumption, APK reinstall, user-data deletion or shared-runtime replacement.

Root stages four SQL files, script and `before/after/<package>.png` in its unique
root-owned 0700 `/data/local/tmp/demo-icons-*` directory. Root alone owns the
board lock and transport. The on-board argv is:

```sh
sh execute-three.sh preview STAGE BOOT APPLY_SHA ROLLBACK_SHA BEFORE_SHA AFTER_SHA
sh execute-three.sh apply STAGE BOOT APPLY_SHA ROLLBACK_SHA BEFORE_SHA AFTER_SHA
sh execute-three.sh rollback STAGE BOOT APPLY_SHA ROLLBACK_SHA BEFORE_SHA AFTER_SHA
```

The five-package argv uses `execute-five.sh` and its separately generated SQL
pins. It is metadata-ready, **not an admitted solution to the unresolved UI
cache source**; compose it with the native lane's actual cache repair rather
than repeating an ineffective restart.

## First-window execution and historical unresolved boundary

This section records the original unsuccessful UI refresh; it is superseded by
the resolved cache source and actual final eight-icon acceptance below.

Root's first-three apply is real rc0 with sidecar and 80-row readback.
`icon-repair/results.json` records the exact rollback entry. It is **not** an
icon visual PASS: Home and the subsequent SceneBoard-only TERM/restart still
showed the original four-flower icons. SceneBoard 2385 became 22751 while host
4583, Toutiao 6789, appspawn processes and boot remained unchanged.

Read-only `cache-path-readonly` then showed changed master values, unchanged
slave values, and foundation's master path at the same dev:inode. Thus a simple
namespace-path mismatch and a purely SceneBoard in-memory explanation are not
sufficient. Whether BMS reads a replica/cache, or launcher persistence/HAP
resource fallback provides the image, remains a source question. No repeated
restart, foundation restart, cache-directory deletion or whole-DB replacement
is authorized by these scripts. `source-cache-handoff.json` gives the native
lane exact source hashes/lines, current evidence and bounded missing getter
sources; old installer comments are not current runtime proof.

## Tests and delivery

`cargo test --manifest-path tools/spec-checks/Cargo.toml --test demo_desktop_icons
-- --nocapture` runs 11 evidence, six SQL, three supplementary-vector and four
actual-shell-predicate known answers plus four launcher CAS cases (28 total), plus the Rust selector. Raw
output is `evidence/tests-final.txt`. Late row drift and foreign rollback content
reject without partial commit; prefix collisions and symlink/missing predicates
reject even in conditional shell contexts. Real replay digests are recorded in
`evidence/cache-real-copy-replay.json` and
`evidence/five-cache-real-copy-replay.json`.

`landing-paths.txt` explicitly includes eight PNGs (force-add ignored assets),
their small source XML/SVG/receipts, code, evidence and the Rust wrapper. It excludes
all DB copies, multi-megabyte SQL and failed/incomplete rendering attempts.
At the first checkpoint human acceptance was pending; actual final eight-icon
acceptance follows below. Author device/VM/SSH calls are zero; no push or index changes.

## Resolved persistent cache source (supersedes the earlier unknown)

Native lane exact SceneBoard HAP/ABC evidence establishes MainAbility memoryCache
-> DbCache -> `icon_info.combine_pic` for normal icons before BMS fallback.
MAIN `benchmark/2026-10-14-demo-desktop-ready/cache-static-analysis/` contains the
authoritative chain and per-field pins. HAP SHA is
`9c11b9f038b9ada284d039af5b156746c3c5fd57faf363b1ca4085289d3612a2`;
ABC SHA is `4fa98da8a77465cb423f5c0011dbf45a49814bebc86fe7d2ed4ee71be7052443`.

The eight packages have 17 actual `normal` rows with null fore/back. Their
10042-character combined URI decodes to the same 7514-byte template SHA
`3554d69ae22fe60a485a56e6099cb873943fc34f461b42898d2f8e42c5c0fc7f`.
`prepare_launcher_cache.py` changes **only combine_pic in those 17 exact rows**,
with all-column before/after CAS and per-package counts. No grid/layout changes.
The actual DB/WAL-copy replay passes: all other data in all 18 tables has an
identical digest, and reverse SQL restores every original icon row. See
`evidence/launcher-cache-real-copy-replay.json`.

`execute-launcher-cache.sh` reuses the root/private-stage, boot, SQL-pin, preview,
CAS and exact failure-rollback pattern. Root stages the four SQL files under
`.artifacts/launcher-cache-plan` and runs the same argv pattern above. The tool
does not clear data, replace a DB, change a HAP or send a signal. Root must reload
SceneBoard's current memory cache and review fresh pictures after this persistent
cache update. No previous failed restart is reclassified as successful.

## Actual final eight-icon acceptance

Root executed five sidecars/49 BMS rows and 17 Launcher combine_pic rows with
preview/apply rc0, then guarded only SceneBoard 22751 -> 5817. Host4583,
Toutiao6789 and appspawn4782/10651 stayed unchanged on boot086d. Root's actual
`desktop-final-icons/outer-icon-review.json` and BMS's independent views of
pages01/03/04/06/08 confirm all eight original-resource artworks. `final-receipt.json`
pins actual execution and pictures. These eight are now **visually confirmed**,
not pending root. Failed earlier restart pictures remain failures. This is not
a complete alpha/artwork-source audit of every remaining desktop/117 package.

Frequent Habits is a separate blank suspect outside demo117. Its current sidecar
is the exact original malformed UTF8-expanded WebP. Strict inverse encoding and
PNG conversion preserve all decoded 48x48 RGBA bytes; 1779 pixels have nonzero
alpha. Both FFmpeg and native macOS ImageIO show a cyan/green pixel pattern.
The earlier blue-ring/check description was wrong and immediately withdrawn.
Valid decoding is **not artwork design acceptance**. The read-only tool
`restore_utf8_webp.py` and `frequent-habits-readonly-conclusion.json` preserve the
evidence. Outer stopped out-of-manifest repair: no device sidecar/BMS/cache
write, no insert, no further board reads requested, and no mixing with the
signed eight. Original received files remain unchanged. Derived diagnostics
stay local and are not delivered as an approved device candidate.
