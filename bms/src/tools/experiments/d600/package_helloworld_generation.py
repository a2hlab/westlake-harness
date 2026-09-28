#!/usr/bin/env python3
"""Assemble one fail-closed HelloWorld P0 deploy generation.

The large Android runtime/framework baseline is copied from a previously
qualified candidate.  Every Route-A artifact that is allowed to vary between
generations is then replaced from one build output, and both deployment
manifests are regenerated from the resulting bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Any


APK_SHA256 = "2d122a7973ffd68c799700aaaaaa0593e5deec30bac83e22a9dc1bf9f64319fd"
RUNTIME_PROVIDER = "libwestlake_android_runtime_provider.so"
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def require_file(path: Path, label: str) -> Path:
    if not path.is_file():
        raise FileNotFoundError(f"missing {label}: {path}")
    return path


def require_sha256(value: str, label: str) -> str:
    if not SHA256.fullmatch(value):
        raise ValueError(f"invalid {label} SHA-256: {value!r}")
    return value


def require_proven_appspawn_config(path: Path) -> Path:
    config = read_json(require_file(path, "appspawn-x config"))
    services = [
        item
        for item in config.get("services", [])
        if isinstance(item, dict) and item.get("name") == "appspawn-x"
    ]
    if len(services) != 1:
        raise ValueError("appspawn-x config must contain exactly one service")
    env_names = {
        item.get("name")
        for item in services[0].get("env", [])
        if isinstance(item, dict)
    }
    preload = [
        item.get("value")
        for item in services[0].get("env", [])
        if isinstance(item, dict) and item.get("name") == "LD_PRELOAD"
    ]
    if preload not in (["/system/android/lib64/liblzma.so"], []):
        raise ValueError("unsupported appspawn-x LD_PRELOAD route")
    return path


def require_cold_appspawn_config(path: Path) -> Path:
    """Compatibility entry point for older host tests."""
    try:
        return require_proven_appspawn_config(path)
    except ValueError as error:
        if "unsupported appspawn-x LD_PRELOAD route" in str(error):
            raise ValueError("cold child route forbids appspawn-x LD_PRELOAD") from error
        raise


def copy_file(source: Path, destination: Path) -> None:
    require_file(source, "source artifact")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def relative_files(root: Path) -> list[Path]:
    return sorted(
        (path.relative_to(root) for path in root.rglob("*") if path.is_file()),
        key=lambda path: path.as_posix(),
    )


def prune_unselected_system_android(
    candidate: Path, selected_paths: set[str]
) -> None:
    system_android = candidate / "system/android"
    if not system_android.is_dir():
        raise FileNotFoundError(f"base candidate has no system/android: {candidate}")
    for path in system_android.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"base candidate system/android contains symlink: {path}")
    for path in sorted(system_android.rglob("*"), reverse=True):
        if path.is_file():
            relative = path.relative_to(candidate).as_posix()
            if relative not in selected_paths:
                path.unlink()
        elif path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass


def replace_generation(value: Any, old: str, new: str) -> Any:
    if isinstance(value, str):
        return value.replace(old, new)
    if isinstance(value, list):
        return [replace_generation(item, old, new) for item in value]
    if isinstance(value, dict):
        return {key: replace_generation(item, old, new) for key, item in value.items()}
    return value


def disable_top_sandbox_switch(path: Path) -> None:
    data = read_json(require_file(path, "sandbox config"))
    common = data.get("common")
    if not isinstance(common, list) or len(common) == 0 or not isinstance(common[0], dict):
        raise ValueError("sandbox config has no common profile")
    if common[0].get("top-sandbox-switch") != "ON":
        raise ValueError("sandbox config must declare top-sandbox-switch=ON")
    common[0]["top-sandbox-switch"] = "OFF"
    write_json(path, data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-candidate", type=Path, required=True)
    parser.add_argument("--route-generation", type=Path, required=True)
    parser.add_argument("--target-output", type=Path, required=True)
    parser.add_argument("--dynamic-roots", type=Path, required=True)
    parser.add_argument("--apk", type=Path, required=True)
    parser.add_argument("--appspawn-config", type=Path, required=True)
    parser.add_argument("--template-deploy-manifest", type=Path, required=True)
    parser.add_argument("--template-expected-hashes", type=Path, required=True)
    parser.add_argument("--namespace-manifest-sha256", required=True)
    parser.add_argument("--skia-provider-sha256", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = args.output_root.resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise ValueError(f"output root must be absent or empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    base_candidate = args.base_candidate.resolve()
    route_generation = args.route_generation.resolve()
    target_output = args.target_output.resolve()
    dynamic_roots = args.dynamic_roots.resolve()
    apk = require_file(args.apk.resolve(), "HelloWorld APK")
    appspawn_config = require_proven_appspawn_config(args.appspawn_config.resolve())
    if not base_candidate.is_dir():
        raise FileNotFoundError(f"missing base candidate: {base_candidate}")
    if not (route_generation / "providers").is_dir():
        raise FileNotFoundError(f"missing Route-A provider directory: {route_generation}")
    if sha256(apk) != APK_SHA256:
        raise ValueError(f"unexpected HelloWorld APK SHA-256: {sha256(apk)}")

    verification = read_json(require_file(route_generation / "verification.json", "Route-A verification"))
    if verification.get("status") != "PASS":
        raise ValueError("Route-A verification status is not PASS")
    generation = verification.get("route_a_input_generation_sha256")
    if not isinstance(generation, str) or len(generation) != 64:
        raise ValueError("Route-A verification has no valid generation SHA-256")

    template_deploy = read_json(args.template_deploy_manifest.resolve())
    template_hashes = read_json(args.template_expected_hashes.resolve())
    namespace_manifest_sha256 = require_sha256(
        args.namespace_manifest_sha256, "namespace manifest"
    )
    skia_provider_sha256 = require_sha256(
        args.skia_provider_sha256, "Skia provider"
    )
    old_generation = template_deploy.get("generation_id")
    if not isinstance(old_generation, str) or len(old_generation) != 64:
        raise ValueError("template deploy manifest has no valid generation_id")
    if template_hashes.get("generation_id") != old_generation:
        raise ValueError("template manifests describe different generations")
    template_android_paths = {
        item.get("path")
        for item in template_deploy.get("artifacts", [])
        if isinstance(item, dict)
        and isinstance(item.get("path"), str)
        and item["path"].startswith("system/android/")
    }

    candidate = output_root / "candidate"
    shutil.copytree(base_candidate, candidate, copy_function=shutil.copy2)
    disable_top_sandbox_switch(candidate / "appdata-sandbox.json")
    prune_unselected_system_android(candidate, template_android_paths)

    old_route_root = candidate / "system/lib64/westlake/route-a"
    resolved_old_route_root = old_route_root.resolve()
    if candidate.resolve() not in resolved_old_route_root.parents:
        raise ValueError("refusing to replace Route-A directory outside candidate")
    if old_route_root.exists():
        shutil.rmtree(old_route_root)

    copy_file(route_generation / "appspawn-x-stock", candidate / "appspawn-x")
    copy_file(
        target_output / "libwestlake_android_child.z.so",
        candidate / "system/lib64/appspawn/libwestlake_android_child.z.so",
    )
    copy_file(
        route_generation / RUNTIME_PROVIDER,
        candidate / f"system/android/lib64/{RUNTIME_PROVIDER}",
    )
    copy_file(
        dynamic_roots / "liboh_adapter_bridge.so",
        candidate / "system/android/lib64/liboh_adapter_bridge.so",
    )
    copy_file(
        dynamic_roots / "liboh_android_runtime.so",
        candidate / "system/android/lib64/liboh_android_runtime.so",
    )
    copy_file(apk, candidate / "HelloWorld.apk")
    copy_file(appspawn_config, candidate / "appspawn_x.cfg")

    providers = sorted((route_generation / "providers").glob("*.so"), key=lambda path: path.name)
    if len(providers) != verification.get("final_provider_set_count"):
        raise ValueError(
            "provider count does not match Route-A verification: "
            f"{len(providers)} != {verification.get('final_provider_set_count')}"
        )
    for provider in providers:
        copy_file(provider, candidate / "system/android/lib64" / provider.name)

    sealed_root = old_route_root / generation
    sealed_root.mkdir(parents=True)
    sealed_sources = providers + [route_generation / RUNTIME_PROVIDER]
    for source in sealed_sources:
        copy_file(source, sealed_root / source.name)
    sealed_names = {path.name for path in sealed_sources}
    expected_old_names = {
        Path(item["path"]).name
        for item in template_deploy.get("artifacts", [])
        if f"system/lib64/westlake/route-a/{old_generation}/" in item.get("path", "")
    }
    if sealed_names != expected_old_names:
        raise ValueError(
            "fresh sealed provider names differ from the qualified template: "
            f"missing={sorted(expected_old_names - sealed_names)} "
            f"extra={sorted(sealed_names - expected_old_names)}"
        )

    sealed_manifest = candidate / "route-a-sealed.sha256"
    sealed_manifest.write_text(
        "".join(
            f"{sha256(sealed_root / name)}  "
            f"system/lib64/westlake/route-a/{generation}/{name}\n"
            for name in sorted(sealed_names)
        ),
        encoding="utf-8",
    )

    artifact_generation = candidate / "artifactGeneration.sha256"
    if artifact_generation.exists():
        artifact_generation.unlink()
    artifact_generation.write_text(
        "".join(
            f"{sha256(candidate / relative)}  {relative.as_posix()}\n"
            for relative in relative_files(candidate)
        ),
        encoding="utf-8",
    )

    deploy = replace_generation(template_deploy, old_generation, generation)
    deploy["generation_id"] = generation
    if not isinstance(deploy.get("namespace_manifest"), dict):
        raise ValueError("template deploy manifest has no namespace_manifest object")
    if not isinstance(deploy.get("skia_provider"), dict):
        raise ValueError("template deploy manifest has no skia_provider object")
    deploy["namespace_manifest"]["sha256"] = namespace_manifest_sha256
    deploy["skia_provider"]["sha256"] = skia_provider_sha256
    artifact_paths: set[str] = set()
    for artifact in deploy.get("artifacts", []):
        relative = artifact.get("path")
        if not isinstance(relative, str) or relative.startswith("/") or ".." in Path(relative).parts:
            raise ValueError(f"invalid artifact path in manifest: {relative!r}")
        path = require_file(candidate / relative, "manifest artifact")
        artifact["sha256"] = sha256(path)
        if relative in artifact_paths:
            raise ValueError(f"duplicate artifact path: {relative}")
        artifact_paths.add(relative)

    expected = replace_generation(template_hashes, old_generation, generation)
    expected["generation_id"] = generation
    expected["apk_sha256"] = APK_SHA256
    if not isinstance(expected.get("device_files"), dict):
        raise ValueError("template expected hashes has no device_files object")
    expected["device_files"][deploy["namespace_manifest"]["device_path"]] = (
        namespace_manifest_sha256
    )
    expected["device_files"][deploy["skia_provider"]["device_path"]] = (
        skia_provider_sha256
    )
    expected["candidate_files"] = {
        relative: sha256(candidate / relative) for relative in sorted(artifact_paths)
    }
    if set(expected["candidate_files"]) != artifact_paths:
        raise ValueError("candidate hash set differs from deploy manifest")

    deploy_path = output_root / "deploy-manifest.json"
    expected_path = output_root / "expected-hashes.json"
    write_json(deploy_path, deploy)
    write_json(expected_path, expected)

    receipt = {
        "schema_version": "bridge.helloworld-p0.package-receipt.v1",
        "status": "PASS",
        "generation_id": generation,
        "apk_sha256": APK_SHA256,
        "artifact_count": len(artifact_paths),
        "candidate_file_count": len(relative_files(candidate)),
        "sealed_provider_count": len(sealed_names),
        "route_a_verification_sha256": sha256(route_generation / "verification.json"),
        "deploy_manifest_sha256": sha256(deploy_path),
        "expected_hashes_sha256": sha256(expected_path),
        "artifact_generation_sha256": sha256(artifact_generation),
        "namespace_manifest_sha256": namespace_manifest_sha256,
        "skia_provider_sha256": skia_provider_sha256,
        "fresh_artifacts": {
            "appspawn-x": sha256(candidate / "appspawn-x"),
            "appspawn_x.cfg": sha256(candidate / "appspawn_x.cfg"),
            "libwestlake_android_child.z.so": sha256(
                candidate / "system/lib64/appspawn/libwestlake_android_child.z.so"
            ),
            RUNTIME_PROVIDER: sha256(
                candidate / f"system/android/lib64/{RUNTIME_PROVIDER}"
            ),
            "liboh_adapter_bridge.so": sha256(
                candidate / "system/android/lib64/liboh_adapter_bridge.so"
            ),
            "liboh_android_runtime.so": sha256(
                candidate / "system/android/lib64/liboh_android_runtime.so"
            ),
        },
    }
    write_json(output_root / "package-receipt.json", receipt)
    print(
        f"PASS package generation={generation} artifacts={len(artifact_paths)} "
        f"sealed_providers={len(sealed_names)} output={output_root}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError) as error:
        print(f"REJECT package: {error}", file=sys.stderr)
        raise SystemExit(2)
