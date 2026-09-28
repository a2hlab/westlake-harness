/*
 * apk_installer.cpp
 *
 * APK file deployment implementation.
 * Handles: APK copy, native lib extraction, dex2oat, data directory creation.
 */
#include "apk_installer.h"
#include "apk_label_resolver.h"
#include "apk_manifest_parser.h"  // android:icon resolution
#include "arsc_resolver.h"        // resource ID -> file path
#include "icon_normalize.h"       // task #65 launcher-icon unification

#include <cerrno>
#include <cstring>
#include <fstream>
#include <algorithm>
#include <limits>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <unzip.h>  // minizip
#include <zip.h>    // minizip writer

#include "hilog/log.h"
#include "directory_ex.h"  // OHOS::ForceCreateDirectory
#include "template_entry_hap.h"  // ohos_adapter_template_resources_hap[]

namespace oh_adapter {

namespace {

#undef LOG_DOMAIN
#undef LOG_TAG
constexpr unsigned int LOG_DOMAIN = 0xD001802;
constexpr const char* LOG_TAG = "ApkInstaller";

#define LOGI(...) OHOS::HiviewDFX::HiLog::Info({LOG_CORE, LOG_DOMAIN, LOG_TAG}, __VA_ARGS__)
#define LOGW(...) OHOS::HiviewDFX::HiLog::Warn({LOG_CORE, LOG_DOMAIN, LOG_TAG}, __VA_ARGS__)
#define LOGE(...) OHOS::HiviewDFX::HiLog::Error({LOG_CORE, LOG_DOMAIN, LOG_TAG}, __VA_ARGS__)

// Buffer size for file copy and ZIP extraction
constexpr size_t COPY_BUFFER_SIZE = 65536;

bool MkdirRecursive(const std::string& path, mode_t mode) {
    (void)mode;
    bool ok = OHOS::ForceCreateDirectory(path);
    if (!ok) {
        LOGE("MkdirRecursive FAIL path=%{public}s errno=%{public}d (%{public}s)",
             path.c_str(), errno, strerror(errno));
    }
    return ok;
}

}  // namespace

NativePayloadInfo ApkInstaller::InspectNativePayload(const std::string& apkPath) {
    return InspectApkNativePayload(apkPath);
}

std::string ApkInstaller::SelectPrimaryAbi(const std::string& apkPath) {
    const NativePayloadInfo payload = InspectNativePayload(apkPath);
    if (payload.state == NativePayloadState::SUPPORTED) {
        LOGI("Selected ABI: %{public}s for %{public}s", payload.primaryAbi.c_str(), apkPath.c_str());
        return payload.primaryAbi;
    }
    return "";
}

ApkInstaller::InstallResult ApkInstaller::DeployApk(
        const std::string& srcApkPath,
        const std::string& packageName,
        int32_t uid, int32_t gid) {

    InstallResult result;
    std::string installDir = std::string(ANDROID_INSTALL_DIR) + "/" + packageName;

    LOGI("DeployApk: package=%{public}s, src=%{public}s",
         packageName.c_str(), srcApkPath.c_str());

    // 1. Create installation directories
    if (!CreateInstallDirs(packageName)) {
        result.errorMsg = "Failed to create installation directories";
        LOGE("%{public}s", result.errorMsg.c_str());
        return result;
    }

    // 2. Copy APK to install directory
    std::string destApk = installDir + "/base.apk";
    if (!CopyApk(srcApkPath, destApk)) {
        result.errorMsg = "Failed to copy APK file";
        LOGE("%{public}s", result.errorMsg.c_str());
        return result;
    }
    result.installedApkPath = destApk;

    // 3. Extract native libraries
    const NativePayloadInfo nativePayload = InspectNativePayload(destApk);
    if (nativePayload.state == NativePayloadState::UNREADABLE ||
        nativePayload.state == NativePayloadState::UNSUPPORTED) {
        result.errorMsg = std::string("Invalid native payload state: ") +
            NativePayloadStateName(nativePayload.state);
        LOGE("%{public}s (%{public}s)", result.errorMsg.c_str(), nativePayload.error.c_str());
        return result;
    }
    const std::string& primaryAbi = nativePayload.primaryAbi;
    if (nativePayload.state == NativePayloadState::SUPPORTED) {
        std::string libDir = installDir + "/lib/" + primaryAbi;
        if (!ExtractNativeLibs(destApk, libDir, primaryAbi)) {
            result.errorMsg = "Failed to extract native libraries";
            LOGE("%{public}s", result.errorMsg.c_str());
            return result;
        }
        result.nativeLibPath = libDir;
    }

    // 4. DEX optimization (dex2oat)
    std::string isa = "arm64";
    std::string oatDir = installDir + "/oat/" + isa;
    MkdirRecursive(oatDir, 0755);
    if (!RunDexOpt(destApk, oatDir, uid, isa, "speed")) {
        // DEX opt failure is non-fatal; app can still run in interpreted mode
        LOGW("DEX optimization failed, app will run in interpreted mode");
    } else {
        result.oatDir = oatDir;
    }

    // 5. Create Android data directories
    if (!CreateDataDirs(packageName, uid, gid)) {
        result.errorMsg = "Failed to create data directories";
        LOGE("%{public}s", result.errorMsg.c_str());
        return result;
    }

    // 6. Set ownership on install directory
    SetPermissions(installDir, uid, gid, 0755);

    result.success = true;
    LOGI("DeployApk completed: package=%{public}s, apk=%{public}s",
         packageName.c_str(), result.installedApkPath.c_str());
    return result;
}

// ============================================================================
// ExtractAndPackResourceHap — synthesize OH "resources HAP" from APK icon
// (方案 2b: template + ZIP byte-level replacement, see appendix C of
// doc/apk_installation_design.html)
// ============================================================================
//
// Steps:
//   1. Open APK, find the launcher icon (try mipmap-xxxhdpi → xxhdpi → hdpi
//      → mdpi). Read bytes into memory.
//   2. Write embedded template HAP bytes to a temp file (minizip needs file IO).
//   3. Open temp file as ZIP READ, open outHapPath as ZIP WRITE.
//   4. For each entry in template:
//        - If name is resources/base/media/{icon,app_icon}.png →
//          write the APK icon bytes instead of template's placeholder
//        - Else copy bytes verbatim
//   5. Close, remove temp file, chmod outHapPath to 0644.
//
// Why a temp file:
//   minizip's unzOpen takes a file path, not memory. Could use ioapi_mem.c
//   for in-memory read, but it's not always linked into OH minizip. File-based
//   path keeps integration simple (~10 ms overhead for 15KB write+read).
//
// Why we replace BOTH icon.png AND app_icon.png:
//   resources.index has two media entries (one app-level, one ability-level).
//   Both should render the same APK icon for visual consistency. The
//   template's placeholder PNG is ~6KB, the APK icon is ~25KB.

namespace {

constexpr size_t kZipBufSize = 65536;

// APK launcher icon search order. Higher density first.
// Most modern APKs ship xxxhdpi as primary; older ones may only have hdpi.
const std::vector<std::string>& GetApkIconCandidates() {
    static const std::vector<std::string> paths = {
        "res/mipmap-xxxhdpi-v4/ic_launcher.png",
        "res/mipmap-xxhdpi-v4/ic_launcher.png",
        "res/mipmap-xhdpi-v4/ic_launcher.png",
        "res/mipmap-hdpi-v4/ic_launcher.png",
        "res/mipmap-mdpi-v4/ic_launcher.png",
        "res/mipmap-xxxhdpi-v4/ic_launcher.webp",
        "res/mipmap-xxhdpi-v4/ic_launcher.webp",
        "res/mipmap-xhdpi-v4/ic_launcher.webp",
        "res/mipmap-hdpi-v4/ic_launcher.webp",
        "res/mipmap-mdpi-v4/ic_launcher.webp",
        // Drawable fallback (older APKs without mipmap)
        "res/drawable-xxxhdpi-v4/ic_launcher.png",
        "res/drawable-xxhdpi-v4/ic_launcher.png",
        "res/drawable-xhdpi-v4/ic_launcher.png",
        "res/drawable-hdpi-v4/ic_launcher.png",
        "res/drawable-mdpi-v4/ic_launcher.png",
    };
    return paths;
}

bool ReadApkLauncherIcon(const std::string& apkPath, std::vector<uint8_t>& out) {
    unzFile zf = unzOpen(apkPath.c_str());
    if (zf == nullptr) {
        LOGE("ReadApkLauncherIcon: cannot open APK %{public}s", apkPath.c_str());
        return false;
    }
    bool found = false;
    for (const auto& candidate : GetApkIconCandidates()) {
        if (unzLocateFile(zf, candidate.c_str(), 0) != UNZ_OK) continue;
        unz_file_info info{};
        if (unzGetCurrentFileInfo(zf, &info, nullptr, 0, nullptr, 0, nullptr, 0) != UNZ_OK) continue;
        if (unzOpenCurrentFile(zf) != UNZ_OK) continue;
        out.resize(info.uncompressed_size);
        int n = unzReadCurrentFile(zf, out.data(), info.uncompressed_size);
        unzCloseCurrentFile(zf);
        if (n != static_cast<int>(info.uncompressed_size)) {
            LOGE("ReadApkLauncherIcon: short read for %{public}s (got %{public}d, want %{public}lu)",
                 candidate.c_str(), n, static_cast<unsigned long>(info.uncompressed_size));
            continue;
        }
        LOGI("ReadApkLauncherIcon: extracted %{public}s (%{public}zu bytes)",
             candidate.c_str(), out.size());
        found = true;
        break;
    }
    unzClose(zf);
    return found;
}

bool CopyZipEntry(unzFile src, zipFile dst, const std::string& name,
                  const unz_file_info& info,
                  const std::vector<uint8_t>* overrideData = nullptr) {
    zip_fileinfo zfi{};
    // Preserve mtime if available (info.dosDate); leave as 0 otherwise — OH
    // restool-built HAPs use epoch 1981-01-01 placeholders too.
    if (zipOpenNewFileInZip(dst, name.c_str(), &zfi,
                            nullptr, 0, nullptr, 0, nullptr,
                            Z_DEFLATED, Z_DEFAULT_COMPRESSION) != ZIP_OK) {
        LOGE("CopyZipEntry: zipOpenNewFileInZip failed for %{public}s", name.c_str());
        return false;
    }

    bool ok = true;
    if (overrideData) {
        if (zipWriteInFileInZip(dst, overrideData->data(), overrideData->size()) != ZIP_OK) {
            LOGE("CopyZipEntry: zipWriteInFileInZip override failed for %{public}s", name.c_str());
            ok = false;
        }
    } else {
        if (unzOpenCurrentFile(src) != UNZ_OK) {
            LOGE("CopyZipEntry: unzOpenCurrentFile failed for %{public}s", name.c_str());
            ok = false;
        } else {
            std::vector<uint8_t> buf(kZipBufSize);
            int n;
            while ((n = unzReadCurrentFile(src, buf.data(), kZipBufSize)) > 0) {
                if (zipWriteInFileInZip(dst, buf.data(), n) != ZIP_OK) {
                    LOGE("CopyZipEntry: zipWriteInFileInZip failed for %{public}s", name.c_str());
                    ok = false;
                    break;
                }
            }
            if (n < 0) {
                LOGE("CopyZipEntry: unzReadCurrentFile error for %{public}s n=%{public}d",
                     name.c_str(), n);
                ok = false;
            }
            unzCloseCurrentFile(src);
        }
    }
    zipCloseFileInZip(dst);
    (void)info;  // info unused for now; reserved for future mtime preservation
    return ok;
}

// Read a named zip entry from an APK/HAP into memory.
bool ReadZipEntry(const std::string& apkPath, const std::string& entryName,
                  std::vector<uint8_t>& out) {
    unzFile zf = unzOpen(apkPath.c_str());
    if (zf == nullptr) return false;
    bool ok = false;
    if (unzLocateFile(zf, entryName.c_str(), 0) == UNZ_OK) {
        unz_file_info info{};
        if (unzGetCurrentFileInfo(zf, &info, nullptr, 0, nullptr, 0, nullptr, 0) == UNZ_OK &&
            unzOpenCurrentFile(zf) == UNZ_OK) {
            out.resize(info.uncompressed_size);
            int n = out.empty() ? 0
                                : unzReadCurrentFile(zf, out.data(), info.uncompressed_size);
            unzCloseCurrentFile(zf);
            ok = (n == static_cast<int>(info.uncompressed_size));
        }
    }
    unzClose(zf);
    return ok;
}

uint16_t ReadLe16(const std::vector<uint8_t>& bytes, size_t off)
{
    return static_cast<uint16_t>(bytes[off] | (bytes[off + 1] << 8));
}

uint32_t ReadLe32(const std::vector<uint8_t>& bytes, size_t off)
{
    return static_cast<uint32_t>(bytes[off]) |
        (static_cast<uint32_t>(bytes[off + 1]) << 8) |
        (static_cast<uint32_t>(bytes[off + 2]) << 16) |
        (static_cast<uint32_t>(bytes[off + 3]) << 24);
}

void WriteLe32(std::vector<uint8_t>& bytes, size_t off, uint32_t value)
{
    bytes[off] = static_cast<uint8_t>(value & 0xff);
    bytes[off + 1] = static_cast<uint8_t>((value >> 8) & 0xff);
    bytes[off + 2] = static_cast<uint8_t>((value >> 16) & 0xff);
    bytes[off + 3] = static_cast<uint8_t>((value >> 24) & 0xff);
}

bool ReadCurrentZipEntry(unzFile src, const unz_file_info& info, std::vector<uint8_t>& out)
{
    if (unzOpenCurrentFile(src) != UNZ_OK) {
        return false;
    }
    out.resize(info.uncompressed_size);
    int n = out.empty() ? 0 : unzReadCurrentFile(src, out.data(), info.uncompressed_size);
    unzCloseCurrentFile(src);
    return n == static_cast<int>(info.uncompressed_size);
}

// Resolve a label resource ID to its string. Framework refs (pkg 0x01) live
// in framework-res.apk on the device; app refs (pkg 0x7f) in the app APK --
// same arsc source selection as ReadIconByManifest.
std::string ResolveLabelResId(const std::string& apkPath, uint32_t labelResId)
{
    if (labelResId == 0) {
        return "";
    }
    const std::string s = oh_adapter::ResolveApkLabel(apkPath, "", labelResId, "");
    if (s.empty()) {
        LOGW("ResolveLabelResId: cannot resolve label 0x%{public}08x from %{public}s",
             labelResId, apkPath.c_str());
        return "";
    }
    LOGI("ResolveLabelResId: @string 0x%{public}08x -> %{public}s", labelResId, s.c_str());
    return s;
}

std::string ReadApkLauncherLabel(const std::string& apkPath)
{
    oh_adapter::ApkManifestParser::ManifestData md;
    if (!oh_adapter::ApkManifestParser::Parse(apkPath, md)) {
        LOGW("ReadApkLauncherLabel: manifest parse failed for %{public}s", apkPath.c_str());
        return "";
    }
    for (const auto& activity : md.activities) {
        bool hasMain = false;
        bool hasLauncher = false;
        for (const auto& filter : activity.intentFilters) {
            hasMain = hasMain || std::find(filter.actions.begin(), filter.actions.end(),
                "android.intent.action.MAIN") != filter.actions.end();
            hasLauncher = hasLauncher || std::find(filter.categories.begin(), filter.categories.end(),
                "android.intent.category.LAUNCHER") != filter.categories.end();
        }
        if (hasMain && hasLauncher) {
            if (!activity.label.empty()) {
                return activity.label;
            }
            // TYPE_REFERENCE label (@string/app_name) -- the common case for
            // real APKs. Resolve via resources.arsc.
            const std::string s = ResolveLabelResId(apkPath, activity.labelResId);
            if (!s.empty()) {
                return s;
            }
        }
    }
    if (!md.appLabel.empty()) {
        return md.appLabel;
    }
    return ResolveLabelResId(apkPath, md.appLabelResId);
}

bool PatchResourceIndexLabels(const std::vector<uint8_t>& input, const std::string& label,
                              std::vector<uint8_t>& output)
{
    if (input.size() < 0xcc || label.empty() ||
        label.size() > std::numeric_limits<uint16_t>::max() - 1 ||
        std::memcmp(input.data() + 0x88, "KEYS", 4) != 0 ||
        std::memcmp(input.data() + 0x94, "IDSS", 4) != 0) {
        return false;
    }
    const uint32_t count = ReadLe32(input, 0x98);
    const size_t table = 0x9c;
    const size_t tableEnd = table + static_cast<size_t>(count) * 8;
    if (count == 0 || tableEnd > input.size()) {
        return false;
    }

    struct EntryRef {
        uint32_t id;
        uint32_t oldOff;
        std::vector<uint8_t> entry;
    };
    std::vector<EntryRef> entries;
    entries.reserve(count);
    for (uint32_t i = 0; i < count; ++i) {
        const uint32_t id = ReadLe32(input, table + i * 8);
        const uint32_t off = ReadLe32(input, table + i * 8 + 4);
        if (off + 4 > input.size()) {
            return false;
        }
        const uint32_t len = ReadLe32(input, off);
        if (off + 4 + len > input.size()) {
            return false;
        }
        entries.push_back({id, off, std::vector<uint8_t>(input.begin() + off, input.begin() + off + 4 + len)});
    }

    const std::vector<uint8_t> labelBytes(label.begin(), label.end());
    bool patched = false;
    for (auto& entryRef : entries) {
        if (entryRef.id != 0x01000000 && entryRef.id != 0x01000003) {
            continue;
        }
        auto& entry = entryRef.entry;
        if (entry.size() < 14) {
            return false;
        }
        const uint32_t type = ReadLe32(entry, 4);
        const uint32_t idInEntry = ReadLe32(entry, 8);
        const uint16_t oldValueLen = ReadLe16(entry, 12);
        const size_t valueStart = 14;
        const size_t valueEnd = valueStart + oldValueLen;
        if (type != 9 || idInEntry != entryRef.id || oldValueLen == 0 || valueEnd > entry.size()) {
            return false;
        }
        std::vector<uint8_t> rebuilt;
        rebuilt.reserve(entry.size() + labelBytes.size());
        rebuilt.insert(rebuilt.end(), entry.begin() + 4, entry.begin() + 12);
        const uint16_t newValueLen = static_cast<uint16_t>(labelBytes.size() + 1);
        rebuilt.push_back(static_cast<uint8_t>(newValueLen & 0xff));
        rebuilt.push_back(static_cast<uint8_t>((newValueLen >> 8) & 0xff));
        rebuilt.insert(rebuilt.end(), labelBytes.begin(), labelBytes.end());
        rebuilt.push_back(0);
        rebuilt.insert(rebuilt.end(), entry.begin() + valueEnd, entry.end());
        entry.assign(4, 0);
        WriteLe32(entry, 0, static_cast<uint32_t>(rebuilt.size()));
        entry.insert(entry.end(), rebuilt.begin(), rebuilt.end());
        patched = true;
    }
    if (!patched) return false;

    const uint32_t firstOff = entries.front().oldOff;
    output.assign(input.begin(), input.begin() + firstOff);
    for (uint32_t i = 0; i < entries.size(); ++i) {
        const uint32_t newOff = static_cast<uint32_t>(output.size());
        WriteLe32(output, table + i * 8, entries[i].id);
        WriteLe32(output, table + i * 8 + 4, newOff);
        output.insert(output.end(), entries[i].entry.begin(), entries[i].entry.end());
    }
    WriteLe32(output, 0x80, static_cast<uint32_t>(output.size()));
    return patched;
}

// Resolve the launcher icon the way Android does: read android:icon from the
// manifest, resolve that resource ID to a real file via resources.arsc — in
// framework-res.apk for framework references (pkg 0x01) or in the app APK for
// app resources (pkg 0x7f) — and read those bytes. Returns false (so the caller
// falls back to the legacy ic_launcher path-grep) when the manifest has no
// android:icon or the id cannot be resolved.
// See doc/helloworld_icon_diff_analysis.html for why this matters.
bool ReadIconByManifest(const std::string& srcApkPath, std::vector<uint8_t>& out) {
    oh_adapter::ApkManifestParser::ManifestData md;
    if (!oh_adapter::ApkManifestParser::Parse(srcApkPath, md)) {
        LOGW("ReadIconByManifest: manifest parse failed for %{public}s, falling back",
             srcApkPath.c_str());
        return false;
    }
    const uint32_t iconId = static_cast<uint32_t>(md.appIcon);
    if (iconId == 0) {
        LOGI("ReadIconByManifest: manifest declares no android:icon, falling back");
        return false;
    }
    const uint32_t pkg = (iconId >> 24) & 0xff;
    // Framework refs (@android:...) live in framework-res.apk on the device.
    const std::string arscApk = (pkg == 0x01)
        ? std::string("/system/android/framework/framework-res.apk")
        : srcApkPath;

    std::string entryPath;
    if (!oh_adapter::ResolveResourceIdToFile(arscApk, iconId, entryPath)) {
        LOGW("ReadIconByManifest: cannot resolve icon 0x%{public}08x via %{public}s, falling back",
             iconId, arscApk.c_str());
        return false;
    }
    // Adaptive icons resolve to an XML drawable descriptor, not image bytes —
    // publishing that as icon.png would render as garbage. Fall back to the
    // legacy path-grep which only matches real image entries.
    if (entryPath.size() >= 4 && entryPath.compare(entryPath.size() - 4, 4, ".xml") == 0) {
        LOGW("ReadIconByManifest: icon 0x%{public}08x resolves to XML %{public}s (adaptive icon?), falling back",
             iconId, entryPath.c_str());
        return false;
    }
    if (!ReadZipEntry(arscApk, entryPath, out) || out.empty()) {
        LOGW("ReadIconByManifest: cannot read %{public}s from %{public}s, falling back",
             entryPath.c_str(), arscApk.c_str());
        return false;
    }
    LOGI("ReadIconByManifest: android:icon 0x%{public}08x -> %{public}s!%{public}s "
         "(%{public}zu bytes)", iconId, arscApk.c_str(), entryPath.c_str(), out.size());
    return true;
}

// --- Iconless-APK classification (2026-08-05, G1 HelloWorld install wall) ---
//
// Why this exists: ExtractAndPackResourceHap used to fail closed whenever no
// launcher icon bytes could be produced, which killed the whole install for
// legitimately icon-less APKs (D600: G1 HelloWorld.apk, 9 zip entries, no
// res/mipmap|drawable icon at all -> bm install 9568260). The placeholder
// refusal exists to prevent silently publishing a CROSS-PACKAGE icon; it must
// not punish an APK that simply has no icon of its own.
//
// The classifier is only consulted AFTER both byte sources
// (ReadIconByManifest, ReadApkLauncherIcon) failed, and decides between:
//   ALLOW template placeholder  — the APK is provably icon-less:
//     * NOT_DECLARED: manifest parses and declares no android:icon, and no
//       physical icon entry exists at any candidate path;
//     * DECLARED_MISSING_ALL_BUCKETS: manifest declares android:icon but the
//       id resolves in NO density bucket of the owning package's arsc, and no
//       physical icon entry exists either (declaration is a dead reference).
//   KEEP fail-closed — anything that smells like tampering or a real icon we
//   merely failed to read:
//     * manifest unparseable (nothing can be proven about the package);
//     * declared id DOES resolve to an existing entry (corrupt/truncated
//       bytes, or an adaptive-icon XML descriptor — the icon exists, only our
//       raster path can't consume it);
//     * any candidate icon path physically present in the zip but unreadable
//       (zip damage = tampered package).
enum class IconlessApkClass {
    NOT_DECLARED,
    DECLARED_MISSING_ALL_BUCKETS,
    FAIL_CLOSED,
};

const char* IconlessApkClassName(IconlessApkClass cls)
{
    return cls == IconlessApkClass::NOT_DECLARED ? "NOT_DECLARED"
        : cls == IconlessApkClass::DECLARED_MISSING_ALL_BUCKETS
            ? "DECLARED_MISSING_ALL_BUCKETS" : "FAIL_CLOSED";
}

// Physical presence probe for the candidate icon paths. A present-but-
// unreadable entry means the package is damaged, not icon-less. An
// unopenable zip is tampering evidence, so it also answers "present".
bool ZipHasAnyIconEntry(const std::string& apkPath)
{
    unzFile zf = unzOpen(apkPath.c_str());
    if (zf == nullptr) {
        return true;
    }
    bool any = false;
    for (const auto& candidate : GetApkIconCandidates()) {
        if (unzLocateFile(zf, candidate.c_str(), 0) == UNZ_OK) {
            any = true;
            break;
        }
    }
    unzClose(zf);
    return any;
}

IconlessApkClass ClassifyIconlessApk(const std::string& srcApkPath)
{
    oh_adapter::ApkManifestParser::ManifestData md;
    if (!oh_adapter::ApkManifestParser::Parse(srcApkPath, md)) {
        return IconlessApkClass::FAIL_CLOSED;  // tampered: cannot prove iconless
    }
    if (md.appIcon != 0) {
        const uint32_t iconId = static_cast<uint32_t>(md.appIcon);
        const uint32_t pkg = (iconId >> 24) & 0xff;
        const std::string arscApk = (pkg == 0x01)
            ? std::string("/system/android/framework/framework-res.apk")
            : srcApkPath;
        std::string entryPath;
        if (oh_adapter::ResolveResourceIdToFile(arscApk, iconId, entryPath)) {
            return IconlessApkClass::FAIL_CLOSED;  // declared AND present, but unusable
        }
        return ZipHasAnyIconEntry(srcApkPath)
            ? IconlessApkClass::FAIL_CLOSED
            : IconlessApkClass::DECLARED_MISSING_ALL_BUCKETS;
    }
    return ZipHasAnyIconEntry(srcApkPath)
        ? IconlessApkClass::FAIL_CLOSED
        : IconlessApkClass::NOT_DECLARED;
}

// Extracts the template HAP's OWN placeholder icon bytes. Using the
// template's built-in placeholder keeps the "no cross-package icon"
// invariant: the published icon is generic by construction, never borrowed
// from another installed package. Bytes are read from a throwaway temp copy
// because minizip is path-based; the temp file is always unlinked.
bool ReadTemplatePlaceholderIcon(const std::string& outHapPath, std::vector<uint8_t>& out)
{
    const std::string probeTmp = outHapPath + ".iconprobe.tmp";
    {
        std::ofstream f(probeTmp, std::ios::binary | std::ios::trunc);
        if (!f) {
            LOGE("ReadTemplatePlaceholderIcon: cannot open %{public}s errno=%{public}d (%{public}s)",
                 probeTmp.c_str(), errno, strerror(errno));
            return false;
        }
        f.write(reinterpret_cast<const char*>(ohos_adapter_template_resources_hap),
                ohos_adapter_template_resources_hap_len);
        f.flush();
        if (!f) {
            LOGE("ReadTemplatePlaceholderIcon: template write failed");
            ::unlink(probeTmp.c_str());
            return false;
        }
    }
    const bool ok = ReadZipEntry(probeTmp, "resources/base/media/icon.png", out) && !out.empty();
    ::unlink(probeTmp.c_str());
    if (!ok) {
        LOGE("ReadTemplatePlaceholderIcon: template has no readable placeholder icon");
    }
    return ok;
}

}  // anonymous namespace

bool ApkInstaller::ExtractAndPackResourceHap(const std::string& srcApkPath,
                                             const std::string& outHapPath) {
    LOGI("ExtractAndPackResourceHap: apk=%{public}s out=%{public}s",
         srcApkPath.c_str(), outHapPath.c_str());

    std::vector<uint8_t> apkIconBytes;
    // This legacy carrier is not an Fn01.A08 verdict source.  It fails closed
    // when icon bytes cannot be produced for a package that provably HAS (or
    // may have) an icon — otherwise template bytes would silently publish a
    // cross-package placeholder.  A provably icon-less APK (no declaration,
    // or a dead declaration missing in every density bucket) instead gets the
    // template's own generic placeholder under a loud typed alarm; see
    // ClassifyIconlessApk for the exact boundary.
    if (!ReadIconByManifest(srcApkPath, apkIconBytes) &&
        !ReadApkLauncherIcon(srcApkPath, apkIconBytes)) {
        const IconlessApkClass iconlessClass = ClassifyIconlessApk(srcApkPath);
        if (iconlessClass == IconlessApkClass::FAIL_CLOSED) {
            LOGE("ExtractAndPackResourceHap: no launcher icon; refusing template placeholder");
            return false;
        }
        if (!ReadTemplatePlaceholderIcon(outHapPath, apkIconBytes)) {
            LOGE("ExtractAndPackResourceHap: icon-less APK but template placeholder unreadable");
            return false;
        }
        LOGE("ICONLESS_APK_TEMPLATE_PLACEHOLDER: apk=%{public}s class=%{public}s — "
             "APK provably has no launcher icon; packaging the template's own generic "
             "placeholder so install can proceed. Desktop icon will be generic; "
             "reinstall an icon-bearing build to replace it.",
             srcApkPath.c_str(), IconlessApkClassName(iconlessClass));
    }
    // task #65: unify launcher-icon footprint — crop transparent margins and
    // scale content to fill the canvas (full-bleed, like StarRail). Cosmetic
    // only: fail-open, any error leaves the original bytes untouched. Placed
    // at the source so both consumers (template-pack + deployedDir side-write)
    // get the same normalized bytes.
    NormalizeLauncherIconPng(apkIconBytes);
    std::string apkLabel = ReadApkLauncherLabel(srcApkPath);
    if (apkLabel.empty()) {
        // Same boundary as the icon rule: an unparseable manifest stays
        // fail-closed (nothing can be proven), while a parseable manifest
        // that simply yields no label falls back to the package name —
        // Android's own label-less fallback — never a cross-package template
        // string. Loud typed alarm, install proceeds.
        oh_adapter::ApkManifestParser::ManifestData labelMd;
        if (!oh_adapter::ApkManifestParser::Parse(srcApkPath, labelMd) ||
            labelMd.packageName.empty()) {
            LOGE("ExtractAndPackResourceHap: no launcher label; refusing template label");
            return false;
        }
        apkLabel = labelMd.packageName;
        LOGE("LABELLESS_APK_PACKAGE_NAME_LABEL: apk=%{public}s — manifest parses but yields "
             "no launcher label anywhere; using package name %{public}s as label.",
             srcApkPath.c_str(), apkLabel.c_str());
    }
    LOGI("ExtractAndPackResourceHap: launcher label=%{public}s", apkLabel.c_str());

    // Side-write the raw icon for the BMS patch: post-registration it reads
    // <deployedDir>/icon.png (= dirname(outHapPath) + "/android/icon.png") to
    // build the launcher RDB data-URI. Fail closed — a missing icon.png means
    // the desktop icon silently falls back to a generic placeholder. The
    // caller (BuildApkResourcesHap via base_bundle_installer) always creates
    // the android/ dir before ExtractFiles(APK_RESOURCES_HAP).
    {
        const std::string iconPath =
            outHapPath.substr(0, outHapPath.find_last_of('/')) + "/android/icon.png";
        std::ofstream icf(iconPath, std::ios::binary | std::ios::trunc);
        if (!icf) {
            LOGE("ExtractAndPackResourceHap: cannot open deployedDir icon %{public}s errno=%{public}d (%{public}s)",
                 iconPath.c_str(), errno, strerror(errno));
            return false;
        }
        icf.write(reinterpret_cast<const char*>(apkIconBytes.data()),
                  static_cast<std::streamsize>(apkIconBytes.size()));
        icf.flush();
        if (!icf) {
            LOGE("ExtractAndPackResourceHap: deployedDir icon write failed %{public}s", iconPath.c_str());
            return false;
        }
        icf.close();
        ::chmod(iconPath.c_str(), 0644);
        LOGI("ExtractAndPackResourceHap: wrote deployedDir icon %{public}s (%{public}zu bytes)",
             iconPath.c_str(), apkIconBytes.size());
    }

    // 1. Write embedded template HAP to a temp file so minizip can read it.
    // Use the same dir as outHapPath — caller is expected to pass a path that
    // foundation can write (typically /data/app/android/<pkg>/_resources.hap).
    std::string templateTmp = outHapPath + ".template.tmp";
    {
        std::ofstream f(templateTmp, std::ios::binary | std::ios::trunc);
        if (!f) {
            LOGE("ExtractAndPackResourceHap: cannot open template tmp %{public}s errno=%{public}d (%{public}s)",
                 templateTmp.c_str(), errno, strerror(errno));
            return false;
        }
        f.write(reinterpret_cast<const char*>(ohos_adapter_template_resources_hap),
                ohos_adapter_template_resources_hap_len);
        f.flush();
        if (!f) {
            LOGE("ExtractAndPackResourceHap: template write failed");
            ::unlink(templateTmp.c_str());
            return false;
        }
    }

    // 2. Open template (read) and outHap (write).
    unzFile src = unzOpen(templateTmp.c_str());
    if (src == nullptr) {
        LOGE("ExtractAndPackResourceHap: cannot open template hap as zip");
        ::unlink(templateTmp.c_str());
        return false;
    }
    // APPEND_STATUS_CREATE appends when the path already exists.  Remove any
    // prior carrier first so replay cannot accumulate duplicate ZIP entries.
    ::unlink(outHapPath.c_str());
    zipFile dst = zipOpen(outHapPath.c_str(), APPEND_STATUS_CREATE);
    if (dst == nullptr) {
        LOGE("ExtractAndPackResourceHap: cannot create output hap %{public}s",
             outHapPath.c_str());
        unzClose(src);
        ::unlink(templateTmp.c_str());
        return false;
    }

    // 3. Iterate template entries; replace icon entries with APK icon bytes.
    bool ok = true;
    size_t iconReplacementCount = 0;
    bool labelPatched = false;
    int rc = unzGoToFirstFile(src);
    while (rc == UNZ_OK) {
        char name[512];
        unz_file_info info{};
        if (unzGetCurrentFileInfo(src, &info, name, sizeof(name),
                                  nullptr, 0, nullptr, 0) != UNZ_OK) {
            ok = false;
            break;
        }
        std::string entryName(name);

        std::vector<uint8_t> patchedResourceIndex;
        const std::vector<uint8_t>* overrideData = nullptr;
        if (entryName == "resources/base/media/icon.png" ||
            entryName == "resources/base/media/app_icon.png") {
            overrideData = &apkIconBytes;
            ++iconReplacementCount;
        } else if (entryName == "resources.index") {
            std::vector<uint8_t> originalIndex;
            if (ReadCurrentZipEntry(src, info, originalIndex) &&
                PatchResourceIndexLabels(originalIndex, apkLabel, patchedResourceIndex)) {
                overrideData = &patchedResourceIndex;
                labelPatched = true;
                LOGI("ExtractAndPackResourceHap: patched resources.index label=%{public}s",
                     apkLabel.c_str());
            } else {
                LOGE("ExtractAndPackResourceHap: resources.index label patch failed");
                ok = false;
                break;
            }
        }

        if (!CopyZipEntry(src, dst, entryName, info, overrideData)) {
            ok = false;
            break;
        }
        rc = unzGoToNextFile(src);
    }

    zipClose(dst, nullptr);
    unzClose(src);
    ::unlink(templateTmp.c_str());

    if (!ok || iconReplacementCount != 2 || !labelPatched) {
        LOGE("ExtractAndPackResourceHap: incomplete typed replacement "
             "icons=%{public}zu label=%{public}d",
             iconReplacementCount, labelPatched ? 1 : 0);
        ::unlink(outHapPath.c_str());
        return false;
    }

    ::chmod(outHapPath.c_str(), 0644);
    struct stat st{};
    if (::stat(outHapPath.c_str(), &st) == 0) {
        LOGI("ExtractAndPackResourceHap: wrote %{public}s (%{public}lld bytes)",
             outHapPath.c_str(), static_cast<long long>(st.st_size));
    }
    return true;
}

bool ApkInstaller::RemoveApk(const std::string& packageName) {
    LOGI("RemoveApk: package=%{public}s", packageName.c_str());

    std::string installDir = std::string(ANDROID_INSTALL_DIR) + "/" + packageName;
    std::string dataDir = std::string(ANDROID_DATA_DIR) + "/" + packageName;
    std::string extDir = std::string(ANDROID_EXT_DIR) + "/" + packageName;

    bool success = true;
    if (!OHOS::ForceRemoveDirectory(installDir)) {
        LOGW("Failed to remove install dir: %{public}s", installDir.c_str());
        success = false;
    }
    if (!OHOS::ForceRemoveDirectory(dataDir)) {
        LOGW("Failed to remove data dir: %{public}s", dataDir.c_str());
        success = false;
    }
    if (!OHOS::ForceRemoveDirectory(extDir)) {
        LOGW("Failed to remove ext dir: %{public}s", extDir.c_str());
        success = false;
    }

    return success;
}

bool ApkInstaller::CreateInstallDirs(const std::string& packageName) {
    std::string installDir = std::string(ANDROID_INSTALL_DIR) + "/" + packageName;
    std::string libDir = installDir + "/lib";
    std::string oatDir = installDir + "/oat";

    return MkdirRecursive(installDir, 0755) &&
           MkdirRecursive(libDir, 0755) &&
           MkdirRecursive(oatDir, 0755);
}

bool ApkInstaller::CopyApk(const std::string& src, const std::string& dst) {
    std::ifstream in(src, std::ios::binary);
    if (!in) {
        LOGE("CopyApk: failed to open source: %{public}s", src.c_str());
        return false;
    }

    std::ofstream out(dst, std::ios::binary | std::ios::trunc);
    if (!out) {
        LOGE("CopyApk: failed to create destination: %{public}s", dst.c_str());
        return false;
    }

    char buffer[COPY_BUFFER_SIZE];
    while (in.read(buffer, sizeof(buffer)) || in.gcount() > 0) {
        out.write(buffer, in.gcount());
        if (!out) {
            LOGE("CopyApk: write failed");
            return false;
        }
    }

    // Set read-only for APK file
    chmod(dst.c_str(), 0644);
    return true;
}

bool ApkInstaller::ExtractNativeLibs(const std::string& apkPath,
                                      const std::string& libDir,
                                      const std::string& primaryAbi) {
    MkdirRecursive(libDir, 0755);

    unzFile zip = unzOpen(apkPath.c_str());
    if (zip == nullptr) {
        LOGE("ExtractNativeLibs: failed to open APK");
        return false;
    }

    std::string prefix = "lib/" + primaryAbi + "/";
    int extractedCount = 0;

    if (unzGoToFirstFile(zip) == UNZ_OK) {
        do {
            char filename[512];
            unz_file_info fileInfo;
            if (unzGetCurrentFileInfo(zip, &fileInfo, filename, sizeof(filename),
                                       nullptr, 0, nullptr, 0) != UNZ_OK) {
                continue;
            }

            std::string entryName(filename);
            if (entryName.compare(0, prefix.size(), prefix) != 0) continue;
            if (entryName.size() <= prefix.size()) continue;  // Skip directory entry

            // Extract .so filename
            std::string soName = entryName.substr(prefix.size());
            if (soName.find('/') != std::string::npos) continue;  // Skip subdirectories

            // Extract file
            if (unzOpenCurrentFile(zip) != UNZ_OK) {
                LOGW("ExtractNativeLibs: failed to open entry: %{public}s", entryName.c_str());
                continue;
            }

            std::string outPath = libDir + "/" + soName;
            std::ofstream out(outPath, std::ios::binary | std::ios::trunc);
            if (!out) {
                LOGW("ExtractNativeLibs: failed to create: %{public}s", outPath.c_str());
                unzCloseCurrentFile(zip);
                continue;
            }

            char buffer[COPY_BUFFER_SIZE];
            int bytesRead;
            while ((bytesRead = unzReadCurrentFile(zip, buffer, sizeof(buffer))) > 0) {
                out.write(buffer, bytesRead);
            }

            out.close();
            unzCloseCurrentFile(zip);

            // Set executable permission for .so files
            chmod(outPath.c_str(), 0755);
            extractedCount++;

            LOGI("Extracted: %{public}s", soName.c_str());
        } while (unzGoToNextFile(zip) == UNZ_OK);
    }

    unzClose(zip);
    LOGI("ExtractNativeLibs: extracted %{public}d files from %{public}s",
         extractedCount, primaryAbi.c_str());
    return true;
}

bool ApkInstaller::RunDexOpt(const std::string& apkPath, const std::string& oatDir,
                              int32_t uid, const std::string& isa,
                              const std::string& compilerFilter) {
    std::string oatFile = oatDir + "/base.odex";

    std::vector<std::string> args = {
        DEX2OAT_PATH,
        "--dex-file=" + apkPath,
        "--oat-file=" + oatFile,
        "--instruction-set=" + isa,
        "--compiler-filter=" + compilerFilter,
        "--boot-image=" + std::string(BOOT_IMAGE_PATH),
        "--android-root=" + std::string(ANDROID_ROOT),
    };

    LOGI("RunDexOpt: %{public}s -> %{public}s (filter=%{public}s)",
         apkPath.c_str(), oatFile.c_str(), compilerFilter.c_str());

    pid_t pid = fork();
    if (pid < 0) {
        LOGE("RunDexOpt: fork failed: %{public}s", strerror(errno));
        return false;
    }

    if (pid == 0) {
        // Child process
        setuid(uid);

        std::vector<const char*> argv;
        for (const auto& arg : args) {
            argv.push_back(arg.c_str());
        }
        argv.push_back(nullptr);

        execv(argv[0], const_cast<char**>(argv.data()));
        // execv failed
        _exit(127);
    }

    // Parent: wait for dex2oat to finish
    int status;
    waitpid(pid, &status, 0);

    if (WIFEXITED(status) && WEXITSTATUS(status) == 0) {
        LOGI("RunDexOpt: success");
        return true;
    }

    LOGE("RunDexOpt: dex2oat exited with status %{public}d", WEXITSTATUS(status));
    return false;
}

bool ApkInstaller::CreateDataDirs(const std::string& packageName,
                                   int32_t uid, int32_t gid) {
    std::string baseDir = std::string(ANDROID_DATA_DIR) + "/" + packageName;

    // Android-style subdirectories
    const std::vector<std::pair<std::string, mode_t>> dirs = {
        {"",              0771},
        {"/cache",        0771},
        {"/code_cache",   0771},
        {"/databases",    0771},
        {"/files",        0771},
        {"/shared_prefs", 0771},
        {"/lib",          0755},
    };

    for (const auto& [sub, mode] : dirs) {
        std::string path = baseDir + sub;
        if (!MkdirRecursive(path, mode)) {
            LOGE("CreateDataDirs: failed to create: %{public}s", path.c_str());
            return false;
        }
        chmod(path.c_str(), mode);
        chown(path.c_str(), uid, gid);
    }

    // External storage directory
    std::string extDir = std::string(ANDROID_EXT_DIR) + "/" + packageName;
    MkdirRecursive(extDir, 0771);
    chown(extDir.c_str(), uid, 1015);  // sdcard_rw GID

    LOGI("CreateDataDirs: created for %{public}s", packageName.c_str());
    return true;
}

bool ApkInstaller::SetPermissions(const std::string& path,
                                   int32_t uid, int32_t gid, mode_t mode) {
    if (chmod(path.c_str(), mode) != 0) {
        LOGW("SetPermissions: chmod failed for %{public}s: %{public}s",
             path.c_str(), strerror(errno));
        return false;
    }
    if (chown(path.c_str(), uid, gid) != 0) {
        LOGW("SetPermissions: chown failed for %{public}s: %{public}s",
             path.c_str(), strerror(errno));
        return false;
    }
    return true;
}

}  // namespace oh_adapter
