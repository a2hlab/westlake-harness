/*
 * arsc_resolver.h
 *
 * Minimal Android resources.arsc (ResTable) resolver.
 *
 * Maps a resource ID (such as the value of android:icon) to the best raster
 * file path inside an APK, so the APK installer can extract the *correct*
 * launcher icon instead of blindly grepping for a file literally named
 * "ic_launcher". See doc/helloworld_icon_diff_analysis.html for the root cause
 * this addresses.
 */
#ifndef OH_ADAPTER_ARSC_RESOLVER_H
#define OH_ADAPTER_ARSC_RESOLVER_H

#include <cstdint>
#include <string>

namespace oh_adapter {

// Resolve a resource ID to a file path inside the given APK's resources.arsc.
//
//   apkPath     APK whose resources.arsc holds the entry. For framework
//               references (package id 0x01) pass framework-res.apk; for app
//               resources (package id 0x7f) pass the app APK itself.
//   resId       e.g. 0x0108009b (@android:drawable/ic_dialog_info) or
//               0x7f020000 (@mipmap/ic_launcher).
//   outFilePath On success, the zip entry name, e.g.
//               "res/drawable-xhdpi-v4/ic_dialog_info.png".
//
// Picks the highest-density, non-XML (raster) candidate among all config
// variants. Handles sparse / offset16 / dense entry-offset encodings and
// multiple ResTable_package chunks sharing the same package id.
//
// Returns true on success. Returns false (and leaves outFilePath untouched)
// when the arsc cannot be read/parsed, the id is absent, or the entry only has
// XML/complex values.
bool ResolveResourceIdToFile(const std::string& apkPath, uint32_t resId,
                             std::string& outFilePath);

// Resolve a resource ID to a *string value* (e.g. android:label="@string/app_name"
// -> "My App"). Same walk as ResolveResourceIdToFile, but the expected value
// type is a string entry and config-variant selection prefers the default
// (zero-locale) configuration -- the label Android shows when no locale
// qualifier matches -- falling back to the first candidate otherwise.
// Decodes UTF-16 pool strings to proper UTF-8 (labels are often non-ASCII).
// Returns false when the arsc cannot be read, the id is absent, or the entry
// is not a plain string.
bool ResolveResourceIdToString(const std::string& apkPath, uint32_t resId,
                               std::string& outString);

// Resolve an Android resource reference using the APK that owns app resources
// and framework-res.apk for @android references. Callers parsing an APK must
// keep this source-selection rule identical for application and activity
// labels; otherwise resource-backed labels silently degrade to package names.
bool ResolveApkResourceIdToString(const std::string& apkPath, uint32_t resId,
                                  std::string& outString);

}  // namespace oh_adapter

#endif  // OH_ADAPTER_ARSC_RESOLVER_H
