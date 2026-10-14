/*
 * adaptive_icon.h — B3: compose an Android <adaptive-icon> XML into a PNG.
 *
 * apk_installer's ReadIconByManifest falls back when the manifest icon id
 * resolves to an XML descriptor (adaptive/vector icon); for icon-obfuscated
 * APKs (fd-seal, toutiao, x) that dead-ends in ClassifyIconlessApk ->
 * FAIL_CLOSED -> bm install 9568260. This module parses the compiled AXML,
 * resolves the foreground/background references through the same
 * highest-density arsc path, composes the layers with lodepng, and returns
 * publishable PNG bytes.
 */
#ifndef ADAPTER_PACKAGE_MANAGER_ADAPTIVE_ICON_H
#define ADAPTER_PACKAGE_MANAGER_ADAPTIVE_ICON_H

#include <cstdint>
#include <string>
#include <vector>

namespace oh_adapter {

// Compose the adaptive icon described by |xmlBytes| (a compiled AXML
// <adaptive-icon> document read from |apkPath|; resource references resolve
// inside |arscApk|, which may be the app APK or framework-res).
// On success fills |outPng| with RGBA8 PNG bytes and returns true.
// Layer rules:
//   foreground: TYPE_REFERENCE -> highest-density raster via arsc
//   background: TYPE_REFERENCE -> raster, or TYPE_INT_COLOR_ARGB8 solid
// Composition: both layers scaled to a common square canvas (max of the
// layer dims, min 108px), foreground centered src-over background.
// Non-PNG layers (webp/vector) fail decode -> false (caller falls back).
bool ComposeAdaptiveIcon(const std::string& apkPath, const std::string& arscApk,
                         const std::vector<uint8_t>& xmlBytes,
                         std::vector<uint8_t>& outPng);

}  // namespace oh_adapter

#endif  // ADAPTER_PACKAGE_MANAGER_ADAPTIVE_ICON_H
