#!/usr/bin/env python3
"""Build a minimal immutable D600 ELF base from ordered provider pools.

Payload providers always win. Each remaining DT_NEEDED name is resolved by
the first exact filename in the ordered device namespace roots. The selected
file must advertise that exact SONAME. The output mirrors device absolute
paths and contains only regular AArch64 ELF files; reports live outside it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


SONAME = re.compile(r"Library soname:\s*\[([^]]+)\]")
NEEDED = re.compile(r"Shared library:\s*\[([^]]+)\]")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_readelf(readelf: Path, path: Path, *arguments: str) -> str:
    result = subprocess.run(
        [os.fspath(readelf), *arguments, os.fspath(path)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        raise ValueError(f"readelf failed for {path}: {result.stdout.strip()}")
    return result.stdout


@dataclass(frozen=True)
class Elf:
    source: Path
    deploy_path: str
    soname: str | None
    needed: tuple[str, ...]
    sha256: str


def inspect(readelf: Path, source: Path, deploy_path: str) -> Elf:
    header = run_readelf(readelf, source, "-h", "--wide")
    if re.search(r"Class:\s+ELF64", header) is None:
        raise ValueError(f"provider is not ELF64: {source}")
    if re.search(r"Machine:\s+AArch64", header) is None:
        raise ValueError(f"provider is not AArch64: {source}")
    dynamic = run_readelf(readelf, source, "-d", "--wide")
    sonames = SONAME.findall(dynamic)
    if len(sonames) > 1:
        raise ValueError(f"provider has multiple SONAMEs: {source}: {sonames}")
    return Elf(
        source=source,
        deploy_path=deploy_path,
        soname=sonames[0] if sonames else None,
        needed=tuple(NEEDED.findall(dynamic)),
        sha256=sha256(source),
    )


def regular_payload_files(root: Path) -> list[Path]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"payload root must be a non-symlink directory: {root}")
    files: list[Path] = []
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        for name in dirnames:
            path = directory_path / name
            if path.is_symlink():
                raise ValueError(f"payload contains directory symlink: {path}")
        for name in filenames:
            path = directory_path / name
            mode = path.lstat().st_mode
            if not stat.S_ISREG(mode):
                raise ValueError(f"payload contains non-regular file: {path}")
            files.append(path)
    if not files:
        raise ValueError("payload root is empty")
    return sorted(files, key=os.fspath)


@dataclass(frozen=True)
class ProviderRoot:
    device: str
    host: Path


def parse_provider_root(raw: str, pool_root: Path) -> ProviderRoot:
    if "=" not in raw:
        raise ValueError(f"provider root must be DEVICE=HOST: {raw}")
    device, host_raw = raw.split("=", 1)
    device_path = PurePosixPath(device)
    if (
        not device_path.is_absolute()
        or ".." in device_path.parts
        or str(device_path) == "/"
    ):
        raise ValueError(f"unsafe device provider root: {device}")
    host = Path(host_raw).absolute()
    if host.is_symlink() or not host.is_dir():
        raise ValueError(f"host provider root must be a non-symlink directory: {host}")
    if os.path.commonpath((os.fspath(pool_root), os.fspath(host.resolve()))) != os.fspath(
        pool_root
    ):
        raise ValueError(f"provider root escapes pool root: {host}")
    return ProviderRoot(str(device_path), host)


def candidate_for(
    readelf: Path,
    pool_root: Path,
    provider_root: ProviderRoot,
    needed: str,
) -> Elf | None:
    if "/" in needed or needed in ("", ".", ".."):
        raise ValueError(f"unsafe DT_NEEDED name: {needed!r}")
    lookup = provider_root.host / needed
    if not lookup.exists():
        if lookup.is_symlink():
            raise ValueError(f"provider pool contains broken symlink: {lookup}")
        return None
    resolved = lookup.resolve(strict=True)
    mode = resolved.lstat().st_mode
    if not stat.S_ISREG(mode):
        raise ValueError(f"provider lookup is not a regular file: {lookup}")
    if os.path.commonpath((os.fspath(pool_root), os.fspath(resolved))) != os.fspath(
        pool_root
    ):
        raise ValueError(f"provider symlink escapes pool: {lookup} -> {resolved}")

    if lookup.is_symlink():
        raw_target = os.readlink(lookup)
        target_device = PurePosixPath(raw_target)
        if not target_device.is_absolute():
            target_device = PurePosixPath(provider_root.device) / target_device
        target_device = PurePosixPath(os.path.normpath(str(target_device)))
        deploy_path = str(target_device)
    else:
        deploy_path = str(PurePosixPath(provider_root.device) / needed)
    elf = inspect(readelf, resolved, deploy_path)
    if elf.soname not in (None, needed):
        raise ValueError(
            f"first provider has wrong SONAME: needed={needed} "
            f"lookup={lookup} soname={elf.soname}"
        )
    return elf


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload-root", required=True)
    parser.add_argument("--pool-root", required=True)
    parser.add_argument("--provider-root", action="append", default=[], required=True)
    parser.add_argument("--loader", required=True)
    parser.add_argument("--expected-interpreter", required=True)
    parser.add_argument("--readelf", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    payload_root = Path(args.payload_root).absolute()
    raw_pool_root = Path(args.pool_root).absolute()
    if raw_pool_root.is_symlink() or not raw_pool_root.is_dir():
        raise ValueError(
            f"pool root must be a non-symlink directory: {raw_pool_root}"
        )
    pool_root = raw_pool_root.resolve(strict=True)
    readelf = Path(args.readelf).absolute()
    loader_source = Path(args.loader).absolute()
    output = Path(args.output).absolute()
    report = Path(args.report).absolute()
    if not readelf.is_file() or not os.access(readelf, os.X_OK):
        raise ValueError(f"readelf is not executable: {readelf}")
    if loader_source.is_symlink() or not loader_source.is_file():
        raise ValueError(f"loader must be a regular non-symlink file: {loader_source}")
    loader_physical = loader_source.resolve(strict=True)
    if os.path.commonpath((os.fspath(pool_root), os.fspath(loader_physical))) != os.fspath(
        pool_root
    ):
        raise ValueError(f"loader escapes pool root: {loader_source}")
    interpreter = PurePosixPath(args.expected_interpreter)
    if not interpreter.is_absolute() or ".." in interpreter.parts:
        raise ValueError("expected interpreter must be a safe absolute path")
    if output.exists() or output.is_symlink():
        raise ValueError(f"output already exists: {output}")
    if report.exists() or report.is_symlink():
        raise ValueError(f"report already exists: {report}")
    if output == report or output in report.parents or report in output.parents:
        raise ValueError("report and output must be separate paths")

    roots = [parse_provider_root(raw, pool_root) for raw in args.provider_root]
    if len({root.device for root in roots}) != len(roots):
        raise ValueError("device provider roots are duplicated")

    payload_elfs = [
        inspect(readelf, path, path.relative_to(payload_root).as_posix())
        for path in regular_payload_files(payload_root)
    ]
    payload_providers: dict[str, Elf] = {}
    for elf in payload_elfs:
        if elf.soname is None:
            continue
        if elf.soname in payload_providers:
            raise ValueError(
                f"payload has duplicate SONAME: {elf.soname}: "
                f"{payload_providers[elf.soname].source}, {elf.source}"
            )
        payload_providers[elf.soname] = elf

    loader = inspect(readelf, loader_source, str(interpreter))
    if loader.soname is None:
        raise ValueError("loader lacks SONAME")
    if loader.soname in payload_providers:
        raise ValueError(f"payload illegally provides loader SONAME: {loader.soname}")
    base_providers: dict[str, Elf] = {loader.soname: loader}
    queue = list(payload_elfs) + [loader]
    resolutions: list[dict[str, str]] = []
    index = 0
    while index < len(queue):
        consumer = queue[index]
        index += 1
        for needed in consumer.needed:
            if needed in payload_providers:
                resolutions.append(
                    {
                        "consumer": consumer.deploy_path,
                        "needed": needed,
                        "scope": "payload",
                        "provider": payload_providers[needed].deploy_path,
                    }
                )
                continue
            if needed in base_providers:
                resolutions.append(
                    {
                        "consumer": consumer.deploy_path,
                        "needed": needed,
                        "scope": "base",
                        "provider": base_providers[needed].deploy_path,
                    }
                )
                continue
            selected = None
            for root in roots:
                selected = candidate_for(readelf, pool_root, root, needed)
                if selected is not None:
                    break
            if selected is None:
                raise ValueError(
                    f"no immutable-base provider: consumer={consumer.deploy_path} "
                    f"needed={needed}"
                )
            provider_name = selected.soname or needed
            if provider_name in payload_providers or provider_name in base_providers:
                raise ValueError(f"provider became ambiguous: {provider_name}")
            base_providers[provider_name] = selected
            queue.append(selected)
            resolutions.append(
                {
                    "consumer": consumer.deploy_path,
                    "needed": needed,
                    "scope": "base",
                    "provider": selected.deploy_path,
                }
            )

    output.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        copied_paths: set[str] = set()
        for soname, elf in sorted(base_providers.items()):
            relative = elf.deploy_path.lstrip("/")
            if not relative or ".." in PurePosixPath(relative).parts:
                raise ValueError(f"unsafe selected deploy path: {elf.deploy_path}")
            if relative in copied_paths:
                raise ValueError(f"two providers share deploy path: {elf.deploy_path}")
            copied_paths.add(relative)
            destination = temporary.joinpath(*PurePosixPath(relative).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(elf.source, destination)
            os.chmod(destination, 0o755)
            if sha256(destination) != elf.sha256:
                raise ValueError(f"provider copy drift: {elf.source}")
        temporary.rename(output)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    report_data = {
        "schema": "westlake.l03_a12.immutable_base_resolution.v1",
        "expected_interpreter": str(interpreter),
        "payload_root": os.fspath(payload_root),
        "provider_roots": [
            {"device": root.device, "host": os.fspath(root.host)} for root in roots
        ],
        "payload": [
            {
                "path": elf.deploy_path,
                "soname": elf.soname,
                "sha256": elf.sha256,
                "needed": list(elf.needed),
            }
            for elf in payload_elfs
        ],
        "immutable_base": [
            {
                "soname": soname,
                "elf_soname": elf.soname,
                "source": os.fspath(elf.source),
                "deploy_path": elf.deploy_path,
                "sha256": elf.sha256,
                "needed": list(elf.needed),
            }
            for soname, elf in sorted(base_providers.items())
        ],
        "resolutions": resolutions,
    }
    with report.open("x", encoding="utf-8") as stream:
        json.dump(report_data, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(
        "IMMUTABLE_BASE_PASS "
        f"payload={len(payload_elfs)} base={len(base_providers)} "
        f"edges={len(resolutions)}"
    )


if __name__ == "__main__":
    main()
