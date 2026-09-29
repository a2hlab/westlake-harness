#!/usr/bin/env python3
"""One-shot idempotent patch: adapt oh_adapter_install_apk_c_entry.cpp's stale
path-based ReadApkNativeInventory call site to the sealed-fd API that the
full-src tree's apk_native_inventory.h actually declares (wire generation).

Run ON hw248 against /opt/build-runs/2026-09-28-oh6.1.0.31-bms-label-resolve.
"""
import sys
from pathlib import Path

P = Path("/opt/build-runs/2026-09-28-oh6.1.0.31-bms-label-resolve/full-src/src/adapter"
         "/framework/package-manager/jni/oh_adapter_install_apk_c_entry.cpp")
src = P.read_text()

OLD = """    std::vector<oh_adapter::ApkNativeArtifact> artifacts;
    oh_adapter::ApkNativeInventoryLimits inventoryLimits;
    if (!oh_adapter::ReadApkNativeInventory(immutablePath, "arm64-v8a",
        inventoryLimits, &artifacts, &error)) {
        oh_adapter::ApkVerifierClient::Close(&session);
        return OH_ADAPTER_APK_VERIFY_PREPASS_FAILED;
    }"""

NEW = """    // Sealed-fd inventory (wire generation API): length from fstat on the
    // verified sealed fd, digest from the verified identity, profile pinned
    // to the runtime we install for (arm64-v8a, on-device page size).
    struct stat sealedStat {};
    if (fstat(session.sealedFd, &sealedStat) != 0 || sealedStat.st_size <= 0) {
        oh_adapter::ApkVerifierClient::Close(&session);
        return OH_ADAPTER_APK_VERIFY_PREPASS_FAILED;
    }
    oh_adapter::NativeInventoryProfile inventoryProfile;
    inventoryProfile.abis.available = true;
    inventoryProfile.abis.supportedAbis = {"arm64-v8a"};
    inventoryProfile.pageSize = static_cast<uint64_t>(sysconf(_SC_PAGESIZE));
    oh_adapter::ApkNativeInventoryLimits inventoryLimits;
    const oh_adapter::ApkNativeInventory inventory = oh_adapter::ReadApkNativeInventory(
        session.sealedFd, static_cast<uint64_t>(sealedStat.st_size), apkSha256,
        inventoryProfile, inventoryLimits);
    if (inventory.verdict != oh_adapter::NativeInventoryVerdict::MATCHED_NATIVE &&
        inventory.verdict != oh_adapter::NativeInventoryVerdict::NO_NATIVE) {
        oh_adapter::ApkVerifierClient::Close(&session);
        return OH_ADAPTER_APK_VERIFY_PREPASS_FAILED;
    }
    const std::vector<oh_adapter::ApkNativeArtifact>& artifacts = inventory.artifacts;"""

if NEW.splitlines()[3] in src and OLD not in src:
    print("already patched")
    sys.exit(0)
if OLD not in src:
    print("OLD call site not found — file changed, refusing blind patch", file=sys.stderr)
    sys.exit(1)

src = src.replace(OLD, NEW, 1)

# includes for fstat/sysconf (idempotent)
if "#include <sys/stat.h>" not in src:
    src = src.replace('#include <cstdio>', '#include <sys/stat.h>\n#include <unistd.h>\n#include <cstdio>', 1)

P.write_text(src)
print("patched OK")
