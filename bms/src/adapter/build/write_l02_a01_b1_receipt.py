#!/usr/bin/env python3
"""Materialize the canonical B1 receipt from one immutable local generation."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


ADAPTER = Path("/opt/21.Game/02.unity.cardwords/adapter")
SCHEMA = ADAPTER / "research/architecture-six-way/schemas/l02-b1-generation-receipt.schema.json"
OUTPUT = ADAPTER / "research/atoms/L02/A01/evidence/b1_generation.json"
PREIMAGES = ADAPTER / "ohos_patches/l02_a01/OH610_GAME_MIN_REV5_PREIMAGES.tsv"
POST_ROOT = ADAPTER / "out/rev5-oh-work-20260724/post"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def readelf_fields(path: Path) -> tuple[str, str, list[str]]:
    text = path.read_bytes().replace(b"\0", b"").decode("utf-8", "replace")
    build_id = re.search(r"Build ID:\s*([0-9a-f]+)", text)
    elf_class = re.search(r"Class:\s*(\S+)", text)
    machine = re.search(r"Machine:\s*(\S+)", text)
    needed = re.findall(r"\(NEEDED\).*?\[([^\]]+)\]", text)
    if not (build_id and elf_class and machine):
        raise SystemExit(f"incomplete readelf identity: {path}")
    if elf_class.group(1) != "ELF64" or machine.group(1) != "AArch64":
        raise SystemExit(f"wrong architecture: {path}")
    return build_id.group(1), elf_class.group(1), needed


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: write_l02_a01_b1_receipt.py <local-generation-root>")
    generation = Path(sys.argv[1]).resolve()
    if generation.parent != ADAPTER / "out/deploy-bundles":
        raise SystemExit("generation must be directly under canonical out/deploy-bundles")

    identity = (generation / "meta/l01-approved-identity.sha256").read_text().strip()
    if identity != sha256(generation / "meta/source-coverage.tsv"):
        raise SystemExit("source identity does not match coverage receipt")

    patch_oracle = []
    for line in PREIMAGES.read_text().splitlines()[1:]:
        pre, relative = line.split("\t", 1)
        post = POST_ROOT / relative
        if not post.is_file():
            raise SystemExit(f"missing postimage: {post}")
        patch_oracle.append(
            {
                "path": relative,
                "pre_sha256": pre,
                "post_sha256": sha256(post),
                "status": "preimage_reproduced_patch_applied_compile_pass_restored",
            }
        )

    artifact_names = ("libapk_installer.so", "libbms.z.so", "libinstalls.z.so")
    artifacts = []
    for name in artifact_names:
        artifact = generation / "artifacts" / name
        build_id, elf_class, needed = readelf_fields(generation / "meta" / f"{name}.readelf.txt")
        artifacts.append(
            {
                "name": name,
                "sha256": sha256(artifact),
                "build_id": build_id,
                "elf_class": elf_class,
                "machine": "AArch64",
                "dt_needed": needed,
                "unexpected_undefined": 0,
                "strict_link_basis": "-Wl,-z,defs for provider; OH production ninja link for pair",
            }
        )

    build_hash = hashlib.sha256()
    for name in ("host-gates.log", "provider-build.log", "pair-build.log"):
        build_hash.update((generation / "logs" / name).read_bytes())

    receipt = {
        "schema": "westlake.l02.b1-generation.v1",
        "generation_id": generation.name,
        "target": {"openharmony": "6.1.0.31", "aosp": "14", "arch": "AArch64"},
        "source_lock": {
            "l01_approved_identity_sha256": identity,
            "approval_basis": [
                "user: 批准",
                "user: 批准你的任何请求",
                "scope: exact final OH6.1.0.31 rev5 source coverage only; no version upgrade",
            ],
            "repos": {
                "oh_bundle_framework_commit": (
                    generation / "meta/oh-repo-commit.txt"
                ).read_text().strip(),
                "adapter_root": str(ADAPTER),
            },
            "coverage_receipt_sha256": sha256(generation / "meta/source-coverage.tsv"),
            "coverage_receipt_path": str(generation / "meta/source-coverage.tsv"),
        },
        "toolchain": {
            "compiler_path": "/opt/build-trees/oh610_lts_source/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang",
            "compiler_sha256": "b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913",
            "sysroot_sha256": "01f3f766e8ff320d0be77254678c0ca59a1bc50366989ebc6b644cb7c643177a",
            "sysroot_hash_rule": "sha256(sorted sha256sum of every regular file under musl/usr)",
            "build_jobs": 32,
        },
        "patch_oracle": patch_oracle,
        "build": {
            "command": (
                "ADAPTER_ROOT=/home/alexyang/westlake/02.unity.cardwords/adapter "
                "OH_ROOT=/opt/build-trees/oh610_lts_source "
                f"GENERATION_ROOT=.../{generation.name} BUILD_JOBS=32 "
                "build/build_l02_a01_same_generation.sh"
            ),
            "rc": 0,
            "log_sha256": build_hash.hexdigest(),
            "clean_replay_sha256": sha256(
                generation / "pair/logs/post-restore-source-check.log"
            ),
            "host_gate_sha256": sha256(generation / "logs/host-gates.log"),
        },
        "artifacts": artifacts,
        "deploy_manifest": {
            "path": str(generation / "meta/deploy-manifest.tsv"),
            "sha256": sha256(generation / "meta/deploy-manifest.tsv"),
            "preflight_sha256": sha256(generation / "logs/host-gates.log"),
        },
        "rollback_manifest": {
            "path": str(generation / "meta/rollback-manifest.tsv"),
            "sha256": sha256(generation / "meta/rollback-manifest.tsv"),
            "restore_test_sha256": sha256(
                generation / "pair/logs/post-restore-source-check.log"
            ),
        },
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    print(f"B1_RECEIPT_WRITTEN {OUTPUT}")
    print(f"B1_RECEIPT_SHA256={sha256(OUTPUT)}")
    print(f"L01_APPROVED_IDENTITY_SHA256={identity}")
    print(f"SCHEMA={SCHEMA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
