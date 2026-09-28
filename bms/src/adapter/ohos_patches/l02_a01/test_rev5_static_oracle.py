#!/usr/bin/env python3
"""Static contract gate for the OH6.1 L02.A01 revision-5 patch."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
PATCH = ROOT / "oh610_game_min_rev5.patch"
MANIFEST = ROOT / "OH610_GAME_MIN_REV5_PREIMAGES.tsv"

text = PATCH.read_text(encoding="utf-8")
added = "\n".join(
    line[1:] for line in text.splitlines()
    if line.startswith("+") and not line.startswith("+++")
)
targets = re.findall(r"^--- a/([^\t]+)", text, re.MULTILINE)
manifest_targets = [
    line.split("\t", 1)[1]
    for line in MANIFEST.read_text(encoding="utf-8").splitlines()[1:]
]
if targets != manifest_targets:
    raise SystemExit("patch target order/set differs from exact preimage manifest")

required = [
    "ATOMIC_PUBLISH_VERIFIED_APK = 77",
    "oh_adapter_verify_and_parse_apk_v1",
    "oh_adapter_close_game_install_plan_v1",
    "oh_adapter_game_install_plan_abi_v1",
    "AtomicPublishVerifiedApk(",
    "F_DUPFD_CLOEXEC",
    "WriteObject<IPCFileDescriptor>",
    "ReadObject<IPCFileDescriptor>",
    "GetOffsetsSize() == 1",
    "ContainFileDescriptors()",
    "GetReadableBytes() == 0",
    "MessageOption::TF_SYNC",
    'PersistInstallJournal("PREPARED"',
    'PersistInstallJournal("COMMITTED"',
    "F_SEAL_WRITE | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_SEAL",
    "rename(stageRoot.c_str(), finalRoot.c_str())",
]
for needle in required:
    if needle not in added:
        raise SystemExit(f"missing rev5 invariant: {needle}")

for forbidden in [
    "oh_adapter_install_apk_with_manifest",
    "ReadFileDescriptor()",
    "WriteFileDescriptor(",
    "F_SETFD",
    "/proc/self/fd",
    "ExtractFiles(APK_RESOURCES_HAP)",
    "ExtractFiles(APK_NATIVE_SO)",
]:
    if forbidden in added:
        raise SystemExit(f"forbidden active rev5 route: {forbidden}")

method_signatures = "\n".join(
    line for line in added.splitlines() if "AtomicPublishVerifiedApk" in line
)
for forbidden in ("targetPath", "sourcePath", "uid", "gid"):
    if forbidden in method_signatures:
        raise SystemExit(f"caller-owned field leaked into publish ABI: {forbidden}")

interface_pos = added.index("virtual ErrCode AtomicPublishVerifiedApk")
if "return ERR_APPEXECFWK_INSTALLD_COPY_FILE_FAILED;" not in added[interface_pos:]:
    raise SystemExit("old/new vtable default is not fail-closed")

prepared = text.index('PersistInstallJournal("PREPARED"')
publish = text.index("ec = installd->AtomicPublishVerifiedApk")
committed = text.index('PersistInstallJournal("COMMITTED"')
if not prepared < publish < committed:
    raise SystemExit("transaction order is not PREPARED -> publish -> COMMITTED")
commit_hunk = text.find("@@ -2067,")
if commit_hunk < 0 or not commit_hunk < committed < commit_hunk + 1600:
    raise SystemExit("COMMITTED is not inserted after the pinned Save/state gates")

if 'j["hasNativeLibraries"] = false;' not in added:
    raise SystemExit("A01 game-min must not activate native extraction")
if "moduleInfo.hapPath = finalDeployedApk;" not in added:
    raise SystemExit("A01 metadata must bind verified base.apk, not resource HAP")

print("L02.A01 rev5 static oracle PASS")
