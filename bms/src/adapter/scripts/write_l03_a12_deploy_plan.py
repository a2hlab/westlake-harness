#!/usr/bin/env python3
"""Write a deterministic deploy plan for one generation-private payload."""

import argparse
import json
import os
from pathlib import Path


SCHEMA = "westlake.l03_a12.deploy_plan.v1"


def regular_files(root: Path) -> list[Path]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"payload root must be a real directory: {root}")
    files: list[Path] = []
    for directory, dirnames, filenames in os.walk(root):
        dirnames.sort()
        filenames.sort()
        current = Path(directory)
        for name in filenames:
            path = current / name
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"payload entry must be a regular non-symlink: {path}")
            files.append(path)
    return files


OH_SERVICE_PLATFORMSDK = {
    "libabilityms.z.so",
    "libmission_list.z.so",
    "libscene_session.z.so",
    "libscene_session_manager.z.so",
    "librender_service_base.z.so",
    "libappexecfwk_common.z.so",
}


def destination(relative: str) -> str:
    parts = Path(relative).parts
    if parts == ("bin", "appspawn-x"):
        return "/system/bin/appspawn-x"
    if len(parts) == 2 and parts[0] in {"adapter", "aosp"} and parts[1].endswith(".so"):
        return f"/system/android/lib64/{parts[1]}"
    if len(parts) == 2 and parts[0] == "oh-service" and parts[1].endswith(".z.so"):
        if parts[1] in OH_SERVICE_PLATFORMSDK:
            return f"/system/lib64/platformsdk/{parts[1]}"
        return f"/system/lib64/{parts[1]}"
    raise ValueError(f"unsupported payload path: {relative}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation-id", required=True)
    parser.add_argument("--payload-root", required=True)
    parser.add_argument("--image-fingerprint", required=True)
    parser.add_argument("--expected-interpreter", required=True)
    parser.add_argument("--filesystem-type", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload_root = Path(args.payload_root).absolute()
    output = Path(args.output).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError(f"refusing to replace deploy plan: {output}")

    entries = []
    destinations: set[str] = set()
    for path in regular_files(payload_root):
        relative = path.relative_to(payload_root).as_posix()
        deploy_path = destination(relative)
        if deploy_path in destinations:
            raise ValueError(f"duplicate deploy destination: {deploy_path}")
        destinations.add(deploy_path)
        entries.append(
            {
                "source": relative,
                "destination": deploy_path,
                "owner": "root",
                "group": "root",
                "mode": "0755",
                "selinux_label": "u:object_r:system_file:s0",
                "namespace_owner": "appspawn-x",
            }
        )
    if not entries:
        raise ValueError("payload is empty")

    document = {
        "entries": entries,
        "expected_interpreter": args.expected_interpreter,
        "filesystem_type": args.filesystem_type,
        "generation_id": args.generation_id,
        "image_fingerprint": args.image_fingerprint,
        "schema": SCHEMA,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
