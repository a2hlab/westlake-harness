/*
 * icon_normalize.h
 *
 * Task #65 launcher-icon unification: make APK icons read at the same visual
 * size as native full-bleed icons on the OH desktop grid.
 * Some APKs ship icons whose content does not fill the canvas:
 *   - Genshin-style: wide TRANSPARENT margins inside the canvas
 *     (158x159 content in 192x192) -> renders ~18% smaller;
 *   - StarRail-style: adaptive-icon composite with the safe-zone padding
 *     PAINTED OPAQUE into the pixels (no alpha channel) -> renders with a
 *     built-in border, again smaller than the grid.
 */
#ifndef OH_ADAPTER_ICON_NORMALIZE_H
#define OH_ADAPTER_ICON_NORMALIZE_H

#include <cstdint>
#include <vector>

namespace oh_adapter {

// Normalize a launcher icon PNG in place, two stages:
//   Stage 1 (transparent margins): find the content bounding box (alpha above
//     threshold), crop the margins, scale the content back up to fill the
//     canvas (aspect preserved, centered) — the full-bleed look.
//   Stage 2 (painted adaptive padding): reached only when stage 1 no-ops.
//     If the image is effectively opaque (no usable alpha anywhere), treat it
//     as an adaptive-icon composite and apply the Android-adaptive convention:
//     the visible safe zone is the central 72dp of the 108dp canvas, so crop
//     1/6 from each side and scale the center back to full canvas. This is
//     what Android launchers themselves render for adaptive icons; legacy
//     icons were designed to the same centered safe-area convention, so the
//     worst case is a bounded cosmetic zoom. Detection-based padding finders
//     (corner sampling / edge variance) were measured and abandoned: real
//     adaptive backgrounds are detailed art (ring energy ~= center energy),
//     no detector separates them from real content. Spec ratio is used
//     instead — deterministic, zero false-negative for adaptive composites.
//
// Fail-open contract: returns false and leaves `pngBytes` untouched unless a
// valid normalized PNG was produced. Specifically a no-op for:
//   - non-decodable input (e.g. the webp fallback candidates),
//   - fully transparent images,
//   - stage 1: largest transparent margin already < 4 px,
//   - stage 2: image has any real transparency (min alpha <= 250) — icons
//     with genuine transparent structure are never speculatively zoomed.
// Cosmetic line only: normalization must never break an install, so callers
// ignore the return value and consume `pngBytes` either way.
bool NormalizeLauncherIconPng(std::vector<uint8_t>& pngBytes);

}  // namespace oh_adapter

#endif  // OH_ADAPTER_ICON_NORMALIZE_H
