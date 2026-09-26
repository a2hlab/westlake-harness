# 2026-09-26 operator layout79 FIX (#48)

Implements the width-clamp fix for `IllegalArgumentException: Layout: -79 < 0`
(root cause in sibling dir 2026-09-26-operator-layout79-48): the OH_WSA relayout
propagates a degenerate 1px session width into the app-visible Configuration.

## Layout

| Path | What |
|------|------|
| src/WindowSessionAdapter.java | Patched base-adapter source (clamp added in relayout()). |
| src/WindowSessionAdapter.java.orig | Unpatched canonical source (md5 db49ecca…), for diff. |
| WindowSessionAdapter.relayout-clamp.patch | Unified diff (the exact change). |
| evidence/layout79-fix-clamp-48.txt | Change spec, clamp-point rationale, static-safety proof, build status. |
| BUILD.md | Two build routes (source rebuild / surgical smali) + assert. |
| scripts/assert_relayout_clamp.sh | Validates a built jar carries the clamp. |

## Change (one method)
`WindowSessionAdapter.relayout()` — after `width/height` are computed from
`requested>0 ? requested : sessionInfo[3/4]`, clamp any axis `<=1` to the last
healthy (`>1`) value (cached in two new static fields), falling back to the display
real max bounds before any healthy relayout. Normal 1200-wide path is byte-identical
(only the two cache stores run). Fires a `DEGENERATE ... -> CLAMPED` log when it acts.

## Build status
ROUTED: jar rebuild needs the westlake framework build env ($BRIDGE_SRC/$BRIDGE_ARM64,
framework.jar) which is not present on this Mac or the orb VM. Source patch + spec are
complete; codex-2 (build env / board owner) rebuilds via BUILD.md. Not deployed.

## UPDATE 2026-09-26 — DELIVERED (patched jar built)
codex-2 handed the exact board baseline `adapter-runtime-bcp.jar`
(sha256 5731db00…, 198155 B). Applied the clamp as a surgical smali patch on that exact
jar (WindowSessionAdapter lives in `relayoutLegacy`, not the WindowRelayoutResult wrapper;
width/height are resolved via a `resolveRelayoutDimension` helper — clamp inserted right
after each result, reusing v10/v11). Product:
- `out/adapter-runtime-bcp.CLAMP48.jar` — sha256 ea5d8b277f1207c928d289196876ad69505d73ab586815daccbda7080169523e (202502 B); inner classes.dex sha256 c5bd7fd23b0ed5c8a6d2b8dce0bd387f899b6fd0b58f5423314c3e90983d35cf (dex 039).
- `out/CHANGE-NOTES.md`, `out/WindowSessionAdapter.patched.smali`, `WindowSessionAdapter.smali.clamp48.diff` (0 deletions / 114 additions).
Validated: smali reassembles to dex 039, round-trip baksmali OK, healthy 1200 path byte-
identical, `scripts/assert_relayout_clamp.sh` ALL PASS (9/9). BCP jar → codex-2 deploys via
boot-image rebuild (not overlay). Not deployed by me.
