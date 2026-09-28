#!/usr/bin/env python3
"""Host-only contract tests for the generic D600 APK lifecycle harness."""

import importlib.util
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("run_apk_lifecycle.py")
SPEC = importlib.util.spec_from_file_location("apk_lifecycle", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


assert MODULE.exact_package_seen('bundleName: com.example.app', 'com.example.app')
assert not MODULE.exact_package_seen('bundleName: com.example.application', 'com.example.app')
assert MODULE.safe_name('Game / one') == 'Game___one'
assert MODULE.bundle_tool_success(subprocess.CompletedProcess([], 0, 'install successfully.\n', ''), 'install')
assert MODULE.bundle_tool_success(subprocess.CompletedProcess([], 0, 'install bundle successfully.\n', ''), 'install')
assert MODULE.bundle_tool_success(subprocess.CompletedProcess([], 0, 'uninstall bundle successfully.\n', ''), 'uninstall')
assert not MODULE.bundle_tool_success(subprocess.CompletedProcess([], 0, 'error: install internal error.\n', ''), 'install')
assert not MODULE.bundle_tool_success(subprocess.CompletedProcess([], 0, 'uninstall bundle successfully.\n', ''), 'install')
assert MODULE.ability_tool_success(subprocess.CompletedProcess([], 0, 'ability start success\n', ''))
assert not MODULE.ability_tool_success(subprocess.CompletedProcess([], 0, 'error: failed to start ability. Error Code:10104001\n', ''))

bms_dump = """com.example.x:
{
  "name": "com.example.x",
  "applicationInfo": {
    "bundleName": "com.example.x",
    "bundleType": 10,
    "codePath": "/data/app/el1/bundle/public/com.example.x/android/base.apk",
    "cpuAbi": "arm64-v8a"
  },
  "hapModuleInfos": [{
    "moduleName": "entry",
    "abilityInfos": [{
      "name": "com.example.x.MainActivity",
      "bundleName": "com.example.x",
      "enabled": true,
      "isLauncherAbility": true,
      "skills": [{
        "actions": ["android.intent.action.MAIN"],
        "entities": ["android.intent.category.LAUNCHER"]
      }]
    }, {
      "name": "com.example.x.SettingsActivity",
      "bundleName": "com.example.x",
      "enabled": true,
      "skills": []
    }]
  }]
}
"""
bms_identity = MODULE.derive_bms_identity(
    MODULE.extract_bms_json(bms_dump, "com.example.x"),
    "com.example.x",
    "com.example.x.MainActivity",
)
assert bms_identity.selected_activity == "com.example.x.MainActivity"
assert bms_identity.selected_module == "entry"
assert bms_identity.bundle_type == 10
try:
    MODULE.extract_bms_json("install bundle successfully.\n", "com.example.x")
except MODULE.HarnessError:
    pass
else:
    raise SystemExit("install receipt was accepted as BMS metadata")
try:
    MODULE.derive_bms_identity({"name": "com.example.other"}, "com.example.x", "com.example.x.MainActivity")
except MODULE.HarnessError:
    pass
else:
    raise SystemExit("mismatched BMS identity was accepted")

source = SCRIPT.read_text(encoding="utf-8")
for forbidden in ('EXPECTED_SERIAL', 'EXPECTED_APK_SHA256', 'EXPECTED_APPSPAWN_SHA256', 'com.example.helloworld'):
    if forbidden in source:
        raise SystemExit(f"legacy hardcode remains in generic harness: {forbidden}")
if "awk '$1" in source or "| awk" in source:
    raise SystemExit("generic harness must not depend on awk inside D600 shell PID verification")
for generation_field in (
    '"package_artifact_sha256"',
    '"bms_apk_transaction_markers"',
    "/system/lib64/libbms.z.so",
    "/system/lib64/libapk_installer.so",
):
    if generation_field not in source:
        raise SystemExit(f"missing generation preflight field: {generation_field}")


class FakePidD600:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def shell(self, name: str, command: str):
        self.calls.append((name, command))
        if "pidof com.example.x" in command:
            return subprocess.CompletedProcess(["fake", name], 0, "", "")
        if "AppSpawnClientSendMsg" in command:
            return subprocess.CompletedProcess(
                ["fake", name], 0,
                "AppSpawnClientSendMsg end result:0x0 pid:222\n"
                "AppSpawnClientSendMsg end result:0x0 pid:111\n",
                "",
            )
        if command == "ps -A -o PID,PPID,UID,NAME,CMDLINE":
            return subprocess.CompletedProcess(
                ["fake", name], 0,
                "  111 1 200000 com.ohos.settings com.ohos.settings\n"
                "  222 1 200001 com.example.x com.example.x\n",
                "",
            )
        if command == "ps -ef":
            return subprocess.CompletedProcess(["fake", name], 0, "", "")
        raise AssertionError(command)


pid_fake = FakePidD600()
assert MODULE.poll_pid(pid_fake, "pid-test", "com.example.x", attempts=1) == "222"
assert all("awk" not in command for _, command in pid_fake.calls)


class FakeUnboundPidD600:
    def shell(self, name: str, command: str):
        if "pidof com.example.x" in command:
            return subprocess.CompletedProcess(["fake", name], 0, "", "")
        if "AppSpawnClientSendMsg" in command:
            return subprocess.CompletedProcess(
                ["fake", name], 0,
                "AppSpawnClientSendMsg end result:0x0 pid:333\n",
                "",
            )
        if command == "ps -A -o PID,PPID,UID,NAME,CMDLINE":
            return subprocess.CompletedProcess(
                ["fake", name], 0,
                "  333 1 200123 com.ohos.settings com.ohos.settings\n",
                "",
            )
        if command == "ps -ef":
            return subprocess.CompletedProcess(
                ["fake", name], 0,
                "root 333 1 0 00:00:00 com.ohos.settings\n",
                "",
            )
        raise AssertionError(command)


assert MODULE.poll_pid(FakeUnboundPidD600(), "pid-unbound-test", "com.example.x", attempts=1) == ""

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    apk = root / "x.apk"
    with zipfile.ZipFile(apk, "w") as archive:
        archive.writestr("AndroidManifest.xml", b"manifest")
        archive.writestr("lib/arm64-v8a/libdemo.so", b"so")
    src = root / "src"; src.mkdir()
    old_root = MODULE.ROOT
    MODULE.ROOT = root.resolve()
    try:
        manifest = root / "m.yaml"
        manifest.write_text("""schema_version: 1\napps:\n  - name: x\n    apk: x.apk\n    source_root: src\n    package: com.example.x\n    activity: com.example.x.MainActivity\n    module: entry\n""", encoding="utf-8")
        assert len(MODULE.load_manifest(manifest)) == 1
        manifest.write_text(f"""schema_version: 1\napps:\n  - name: x\n    apk: x.apk\n    source_root: src\n    package: com.example.x\n    activity: com.example.x.MainActivity\n    module: entry\n    sha256: {MODULE.sha256(apk)}\n""", encoding="utf-8")
        assert len(MODULE.load_manifest(manifest)) == 1
        manifest.write_text("""schema_version: 1\napps:\n  - name: x\n    apk: x.apk\n    source_root: src\n    package: com.example.x\n    activity: com.example.x.MainActivity\n    module: entry\n    sha256: 0000000000000000000000000000000000000000000000000000000000000000\n""", encoding="utf-8")
        try:
            MODULE.load_manifest(manifest)
        except MODULE.HarnessError:
            pass
        else:
            raise SystemExit("sha256 mismatch was accepted")
        manifest.write_text("""schema_version: 1\napps:\n  - name: x\n    apk: x.apk\n    source_root: missing\n    package: com.example.x\n    activity: com.example.x.MainActivity\n    module: entry\n""", encoding="utf-8")
        try:
            MODULE.load_manifest(manifest)
        except MODULE.HarnessError:
            pass
        else:
            raise SystemExit("missing source root was accepted")
    finally:
        MODULE.ROOT = old_root

    class FakeD600:
        """Makes launch fail after a verified install to test finalization."""

        def __init__(self, evidence: Path) -> None:
            self.evidence = evidence
            self.calls: list[str] = []

        def shell(self, name: str, command: str):
            self.calls.append(name)
            stdout = ""
            rc = 0
            if name.endswith("after-install-bms"):
                stdout = bms_dump
            elif name.endswith("uninstall"):
                stdout = "uninstall successfully.\n"
            elif name.endswith("install"):
                stdout = "install successfully.\n"
            elif name.endswith("launch"):
                rc = 1
            elif name.endswith("after-uninstall-bms"):
                stdout = ""
            elif name.endswith("remote-sha"):
                stdout = MODULE.sha256(apk) + "  remote.apk\n"
            return subprocess.CompletedProcess(["fake", name], rc, stdout, "")

        def run(self, name: str, *args: str):
            self.calls.append(name)
            if name.endswith("snapshot-recv"):
                Path(args[-1]).write_bytes(b"png")
            return subprocess.CompletedProcess(["fake", name], 0, "", "")

    evidence = root / "evidence"; evidence.mkdir()
    fake = FakeD600(evidence)
    outcome = MODULE.app_lifecycle(
        fake,
        MODULE.App("x", apk, src, "com.example.x", "com.example.x.MainActivity", "entry"),
        1,
    )
    assert outcome["verdict"] == "FAIL_LAUNCH_SCREENSHOT_OR_UNINSTALL"
    # Failure after installation still owns a normal uninstallation attempt.
    assert "01-x-uninstall" in fake.calls
    assert outcome["steps"]["uninstalled_bms_absent"] is True
    assert outcome["requires_bionic_runtime_bridge"] is True
    assert outcome["steps"]["bms_identity"]["selected_activity"] == "com.example.x.MainActivity"
    assert outcome["steps"]["yaml_activity_is_bms_launcher"] is True

    package_fake = FakeD600(evidence)
    package_outcome = MODULE.app_lifecycle(
        package_fake,
        MODULE.App("x", apk, src, "com.example.x", "com.example.x.MainActivity", "entry"),
        2,
        require_launch=False,
    )
    assert package_outcome["verdict"] == "PASS_PACKAGE_LIFECYCLE"
    assert package_outcome["steps"]["launch_skipped"] is True
    assert "02-x-launch" not in package_fake.calls

    queue_apps = [
        MODULE.App("a", apk, src, "com.example.a", None, "entry"),
        MODULE.App("b", apk, src, "com.example.b", None, "entry"),
        MODULE.App("c", apk, src, "com.example.c", None, "entry"),
    ]
    queue_calls = []

    def fake_member(member, index):
        queue_calls.append((member.package, index))
        verdict = "PASS_PACKAGE_LIFECYCLE" if member.package == "com.example.a" else "FAIL_INSTALL_OR_QUERY"
        return {"app": {"package": member.package}, "verdict": verdict}

    queue_outcomes, stopped_at, unattempted = MODULE.run_fail_fast_queue(
        queue_apps, fake_member, "PASS_PACKAGE_LIFECYCLE"
    )
    assert [item[0] for item in queue_calls] == ["com.example.a", "com.example.b"]
    assert [item["verdict"] for item in queue_outcomes] == [
        "PASS_PACKAGE_LIFECYCLE", "FAIL_INSTALL_OR_QUERY"
    ]
    assert stopped_at == "com.example.b"
    assert unattempted == ["com.example.c"]

print("generic D600 APK lifecycle harness tests PASS")
