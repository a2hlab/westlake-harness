#!/usr/bin/env python3
"""Generate or verify the project-local frozen OH appspawn source closure."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib


def digest(path: pathlib.Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def build_manifest(root: pathlib.Path, project: pathlib.Path) -> dict:
    files = []
    tree_lines = []
    total_bytes = 0
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        sha256 = digest(path)
        size = path.stat().st_size
        files.append({"path": relative, "sha256": sha256, "size": size})
        tree_lines.append(f"{sha256}  {relative}\n")
        total_bytes += size
    tree_sha = hashlib.sha256("".join(tree_lines).encode("utf-8")).hexdigest()

    logical_generation = project / ".work/product-tls-generation"
    generation = pathlib.Path(os.environ.get(
        "WESTLAKE_GENERATION_ROOT", logical_generation)).resolve()
    lock = generation / "tool_runtime.lock"
    compiler = generation / "frozen/toolchain/bin/clang-15"
    frozen = project / "adapter/frozen/references/oh-appspawn-security-v7"
    auxiliary_paths = [
        "base/startup/init/interfaces/innerkits/include/hookmgr.h",
        "base/startup/init/interfaces/innerkits/include/beget_ext.h",
        "base/startup/init/interfaces/innerkits/include/init_error.h",
        "base/startup/init/interfaces/innerkits/include/init_socket.h",
        "base/startup/init/interfaces/innerkits/include/init_utils.h",
        "base/startup/init/interfaces/innerkits/include/list.h",
        "base/startup/init/interfaces/innerkits/include/loop_event.h",
        "base/startup/init/interfaces/innerkits/include/modulemgr.h",
        "base/startup/init/interfaces/innerkits/include/syspara/parameter.h",
        "base/startup/init/interfaces/innerkits/hookmgr/hookmgr.c",
        "base/startup/init/interfaces/innerkits/modulemgr/modulemgr.c",
        "base/startup/init/services/utils/list.c",
        "interface/sdk_c/hiviewdfx/hilog/include/hilog/log.h",
        "interface/sdk_c/hiviewdfx/hilog/include/hilog/log_c.h",
        "interface/sdk_c/hiviewdfx/hilog/include/hilog/log_cpp.h",
        "interface/sdk_c/hiviewdfx/hilog/include/hilog_base/log_base.h",
        "third_party/bounds_checking_function/include/securec.h",
        "third_party/bounds_checking_function/include/securectype.h",
        "third_party/cJSON/cJSON.h",
    ]
    auxiliary = []
    for relative in auxiliary_paths:
        path = frozen / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        auxiliary.append({
            "path": str(path.relative_to(project)),
            "sha256": digest(path),
            "size": path.stat().st_size,
        })
    return {
        "schema": "westlake-oh-v7-stock-appspawn-source-closure-v1",
        "origin_read_only":
            "/opt/10.Project/19.Document/19.1H.HarmonyOS-V7.0.0.18-GZ05-Build/base/startup/appspawn",
        "frozen_root": str(root.relative_to(project)),
        "file_count": len(files),
        "total_bytes": total_bytes,
        "tree_sha256": tree_sha,
        "files": files,
        "auxiliary_frozen_inputs": auxiliary,
        "target_tool_inputs": {
            "runtime_lock": {
                "path": str((logical_generation / "tool_runtime.lock").relative_to(project)),
                "sha256": digest(lock),
            },
            "clang_15": {
                "path": str((logical_generation / "frozen/toolchain/bin/clang-15").relative_to(project)),
                "sha256": digest(compiler),
            },
            "sysroot":
                ".work/product-tls-generation/frozen/sysroot",
        },
        "stock_host_gn_target":
            "base/startup/appspawn/standard/BUILD.gn:appspawn",
        "stock_security_gn_targets": [
            "base/startup/appspawn/modules/common/BUILD.gn:appspawn_common",
            "base/startup/appspawn/modules/sandbox/BUILD.gn:appspawn_sandbox",
        ],
        "adapter_route": "A_stock_appspawn_child_processor",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    plugin = pathlib.Path(__file__).resolve().parent
    project = plugin.parents[4]
    root = (project /
            "adapter/frozen/references/oh-appspawn-security-v7/base/startup/appspawn")
    output = plugin / "SOURCE_CLOSURE.json"
    manifest = build_manifest(root, project)
    encoded = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if args.verify:
        if not output.is_file() or output.read_text(encoding="utf-8") != encoded:
            raise SystemExit("SOURCE_CLOSURE.json drift")
        print(f"PASS source closure files={manifest['file_count']} "
              f"tree={manifest['tree_sha256']}")
        return 0
    output.write_text(encoded, encoding="utf-8")
    print(f"WROTE source closure files={manifest['file_count']} "
          f"tree={manifest['tree_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
