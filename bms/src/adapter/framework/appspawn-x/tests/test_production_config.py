#!/usr/bin/env python3
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
CONFIG = PROJECT / "adapter/framework/appspawn-x/config/appspawn_x.cfg"
RUNTIME = PROJECT / "adapter/framework/appspawn-x/src/appspawnx_runtime.cpp"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL production_config: {message}")


def main() -> None:
    require(CONFIG.is_file() and CONFIG.resolve().is_relative_to(PROJECT),
            "canonical config must be project-local")
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    services = [item for item in data.get("services", [])
                if item.get("name") == "appspawn-x"]
    require(len(services) == 1, "exactly one appspawn-x service is required")
    service = services[0]
    require(service.get("path") == ["/system/bin/appspawn-x", "--socket-name",
                                    "AppSpawnX"],
            "production service must be init-owned direct exec")
    require(service.get("secon") == "u:r:appspawn:s0",
            "production parent SELinux domain changed")
    require(service.get("setuid") is True,
            "production service must retain init setuid handling")
    sockets = [item for item in service.get("socket", [])
               if item.get("name") == "AppSpawnX"]
    require(len(sockets) == 1, "exactly one AppSpawnX socket is required")
    require(sockets[0].get("permissions") == "0660" and
            sockets[0].get("uid") == "root" and
            sockets[0].get("gid") == "appspawn",
            "AppSpawnX socket must remain restricted to root:appspawn")

    env_items = service.get("env", [])
    env = {item.get("name"): item.get("value") for item in env_items
           if isinstance(item, dict) and item.get("name")}
    require(env.get("APPSPAWNX_FAST_DEV") == "0",
            "FAST_DEV must be disabled")
    require(env.get("APPSPAWNX_CHECK_JNI") == "0",
            "CheckJNI must be disabled")
    require(env.get("APPSPAWNX_NO_JIT") == "1",
            "qualifying cold starts must disable ART JIT")
    library_path = env.get("LD_LIBRARY_PATH", "").split(":")
    expected_library_path = [
        "/system/lib64",
        "/system/android/lib64",
        "/system/lib64/chipset-sdk-sp",
        "/system/lib64/platformsdk",
        "/system/lib64/chipset-sdk",
        "/system/lib64/ndk",
    ]
    require(library_path == expected_library_path,
            f"LD_LIBRARY_PATH must exactly match canonical AArch64 order: {library_path}")
    require(not any(path.startswith("/system/android/lib") and path != "/system/android/lib64"
                    for path in library_path),
            "32-bit Android library paths must not remain in canonical config")
    require(not any(path.startswith("/system/lib/") or path == "/system/lib"
                    for path in library_path),
            "32-bit OH library paths must not remain in canonical config")
    require("LD_PRELOAD" not in env,
            "cold child route forbids parent runtime LD_PRELOAD")

    commands = [command for job in data.get("jobs", [])
                for command in job.get("cmds", [])]
    require(any("dalvik-cache/arm64" in command for command in commands),
            "ARM64 dalvik-cache directory is missing")
    require(not any(command.endswith("dalvik-cache/arm 0711 root root")
                    for command in commands),
            "ARM32-only dalvik-cache directory remains canonical")

    runtime = RUNTIME.read_text(encoding="utf-8")
    gate = runtime.find('getenv("APPSPAWNX_VERBOSE_STARTUP")')
    option = runtime.find('makeOption("-verbose:startup")')
    require(gate >= 0 and option > gate,
            "verbose startup must be explicitly gated and default-off")

    print("PASS production_config arm64=true diagnostics_default_off=true "
          "no_jit=true")


if __name__ == "__main__":
    main()
