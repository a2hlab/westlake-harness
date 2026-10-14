/*
 * directory_ex.h — target-build shim header for the ONE c_utils helper
 * apk_installer.cpp uses across the .so boundary. DECLARATION ONLY.
 *
 * Why: kit's libutils.z.so exports OHOS::ForceCreateDirectory only in the
 * OH-tree libcxx namespace (std::__h); objects built against the OHOS SDK
 * libcxx reference std::__n1, so linking against libutils fails. The
 * definition lives in directory_ex_shim.cpp (single TU, strong symbol),
 * which compile_apk_installer.sh compiles into libapk_installer.so.
 * Same semantics as OH's directory_ex: recursive mkdir -p, POSIX only.
 */
#ifndef APK_INSTALLER_DIRECTORY_EX_SHIM_H
#define APK_INSTALLER_DIRECTORY_EX_SHIM_H

#include <string>

namespace OHOS {

bool ForceCreateDirectory(const std::string& path);
bool ForceRemoveDirectory(const std::string& path);

}  // namespace OHOS

#endif  // APK_INSTALLER_DIRECTORY_EX_SHIM_H
