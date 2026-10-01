# J10e split — one fix per file (U10 base), proven behaviour-identical to J10g 238ffc14

The outer loop chose **split** for freezing (AGENTS: split into single-item independent files before a
freeze). `J10eWebView.java` carried four concerns; this splits them so each freeze unit is its own file,
**behaviour unchanged**, and proves it at the bytecode level.

## Split (sources/)
| file | fix (freeze unit) | was |
|---|---|---|
| `J10eViewDelegate.java` | WebView ViewDelegate → `PrivateAccess.super_*` forwarding | `J10eWebView$DelegateForward` |
| `J10eCookieManager.java` | concrete empty `CookieManager` | `J10eWebView$WlCookieManager` |
| `J10fWebSettings.java` (unchanged, in walls) | concrete `WebSettings` | — |
| `J10gWebExtras.java` (unchanged, in walls) | ServiceWorkerController/etc + `sPackageInfo` | — |
| `J10eWebView.java` | the enriched-provider **seed + routing** (install, ProviderEnrich, ProviderInstance, zero) | skeleton kept |

## Equivalence (split-equivalence.md)
`build_split.py` builds the split jar (`oh-adapter-runtime-u10base.jar`, sha `11974b7b…`, deterministic,
on the J10d baseline); `compare_split.py` baksmali-diffs every method body against J10g `238ffc14` with
the two renamed class tokens normalised. **Result: 150 methods instruction-identical; the only real
differences are the relocation of the one `sLoggedDelegate` log-once flag into `J10eViewDelegate`
(accessor→direct field op, `<clinit>` move, 2 dead accessors removed) + an inner→top-level ctor visibility
widening — all behaviour-preserving.** See split-equivalence.md for the per-method verdict.

## This is the U10 base
These split sources are the base of the **U10 JAR**. When cx-bms's `no-fatal-fixplan.json` J-layer entries
land master, merge them with `build_j10g.py --extra-sources A.java B.java …` (one version per window).
Freeze registration (FZ-ids, frozen.json) stays the outer loop's call; the draft entries are in the
parent dir's `frozen-entries-draft.json` (now backed by these single-concern files).

Not done here: no walls source replaced, no frozen.json edit (outer-loop calls).
