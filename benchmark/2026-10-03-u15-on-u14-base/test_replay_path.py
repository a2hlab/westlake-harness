import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = {
    "u14": ("benchmark/2026-10-03-u14-on-u13-base/replay-production.sh", "U14_U13_PRODUCTION_REPLAY"),
    "u15": ("benchmark/2026-10-03-u15-final-assembly/replay-production.sh", "U15_PRODUCTION_REPLAY"),
}


def executable(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o755)


class ReplayPathTests(unittest.TestCase):
    def test_default_disabled_before_any_probe(self):
        for relative, marker in SCRIPTS.values():
            environment = dict(os.environ)
            environment.pop(marker, None)
            result = subprocess.run(["bash", str(REPO / relative)], env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 78)
            self.assertIn("DISABLED", result.stdout)

    def test_vm_tools_shared_tmp_and_mac_home(self):
        for relative, marker in SCRIPTS.values():
            for surface, inherited_home in [("vm", False), ("vm", True), ("mac", True)]:
                with tempfile.TemporaryDirectory(prefix="replay-path-model-") as temporary:
                    root = Path(temporary)
                    ws = root / "workspaces"
                    wrapper = ws / "lane" / relative
                    wrapper.parent.mkdir(parents=True)
                    shutil.copyfile(REPO / relative, wrapper)
                    base, package = root / "base", root / "package"
                    base.mkdir()
                    package.mkdir()
                    (base / "bundle.json").write_text("{}\n")
                    digest = hashlib.sha256((base / "bundle.json").read_bytes()).hexdigest()
                    (package / "bundle.json").write_text(json.dumps(dict(rollout_ready=False, execution_enabled=False,
                        static_checks=dict(baseline_bundle_sha256=digest), transaction_binding=dict(base_sha256=digest, promotion_confirmed=False))))
                    ambient = root / "ambient"
                    vmtools = ws / "westlake-harness/benchmark/2026-10-01-u7-executor/.vm-tools"
                    for directory in [ambient, vmtools]:
                        for name in ["dexdump", "ssh", "scp"]:
                            executable(directory / name, "#!/bin/sh\nexit 0\n")
                    executable(ambient / "uname", "#!/bin/sh\nif [ \"$1\" = -m ]; then echo x86_64; else echo " + ("Linux" if surface == "vm" else "Darwin") + "; fi\n")
                    mac_home = root / ("inherited-mac-home" if inherited_home else "discovered-mac-home")
                    executable(ambient / "mac", "#!/bin/sh\nprintf '%s' '" + str(mac_home) + "'\n")
                    executable(ambient / "python3", "#!/bin/sh\nif [ \"$1\" = - ]; then exec " + str(Path(sys.executable)) + " \"$@\"; fi\ncommand -v dexdump\ncommand -v ssh\ncommand -v scp\nprintf 'TMPDIR=%s\\nMAC_HOME=%s\\n' \"$TMPDIR\" \"$MAC_HOME\"\n" + str(Path(sys.executable)) + " -c 'import tempfile; print(\"DEX_TMP=\" + tempfile.gettempdir())'\n")
                    environment = dict(os.environ, WORKSPACES=str(ws), PATH=str(ambient) + ":" + os.environ["PATH"])
                    ambient_tmp = root / "ambient-tmp"
                    ambient_tmp.mkdir()
                    environment["TMPDIR"] = str(ambient_tmp)
                    environment.pop("MAC_HOME", None)
                    if inherited_home:
                        environment["MAC_HOME"] = str(mac_home)
                    environment[marker] = "outer-approved"
                    result = subprocess.run(["bash", str(wrapper), surface, str(base), digest, str(package), "not-executed-oatdump"],
                        env=environment, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    expected = vmtools if surface == "vm" else ambient
                    for name in ["dexdump", "ssh", "scp"]:
                        self.assertIn(str(expected / name), result.stdout)
                    expected_tmp = wrapper.parent / ".artifacts/vm-tmp" if surface == "vm" else ambient_tmp
                    self.assertIn("TMPDIR=" + str(expected_tmp), result.stdout)
                    self.assertIn("MAC_HOME=" + str(mac_home), result.stdout)
                    actual_tmp = next(line.removeprefix("DEX_TMP=") for line in result.stdout.splitlines() if line.startswith("DEX_TMP="))
                    self.assertEqual(Path(actual_tmp).resolve(), expected_tmp.resolve())


if __name__ == "__main__":
    unittest.main(verbosity=2)
