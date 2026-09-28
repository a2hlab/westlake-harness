#!/usr/bin/env python3
"""Capture AlexPC builder identity and optionally warm an isolated AOSP graph.

The preflight never imports Bridge worktree bytes and never emits an admitted
generation artifact.  A later final generation must freeze source hashes and
rebuild from those bytes.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


SCHEMA = "bridge.fn01.alexpc-builder-preflight.v1"
REMOTE_WORK_RE = re.compile(
    r"^/opt/build-trees/\.work/fn01-a04-provenance-[a-z0-9._-]+$"
)


class PreflightError(RuntimeError):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def ssh_run(host: str, script: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["ssh", host, "bash", "-lc", shlex.quote(script)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PreflightError(f"ssh probe failed to execute: {exc}") from exc


def run_probe(
    host: str, name: str, script: str, raw_dir: Path, timeout: int = 120
) -> dict[str, Any]:
    result = ssh_run(host, script, timeout)
    output = result.stdout or ""
    log_path = raw_dir / f"{name}.log"
    log_path.write_text(output, encoding="utf-8")
    record = {
        "name": name,
        "command_sha256": sha256_bytes(script.encode("utf-8")),
        "rc": result.returncode,
        "stdout_sha256": sha256_bytes(output.encode("utf-8")),
        "stdout_bytes": len(output.encode("utf-8")),
        "raw_log": str(log_path),
        "raw_log_sha256": sha256_file(log_path),
    }
    if result.returncode != 0:
        raise PreflightError(f"AlexPC probe {name} failed rc={result.returncode}: {output}")
    return record


HOST_PROBE = r"""
set -eu
printf 'hostname='; hostname
printf 'kernel='; uname -srvm
printf 'machine='; uname -m
printf 'shell='; getent passwd "$(id -un)" | cut -d: -f7
printf 'user='; id -un
printf 'uid='; id -u
"""


TOOLCHAIN_PROBE = r"""
set -eu
OH=/opt/build-trees/oh610_lts_source
AOSP=/opt/build-trees/aosp-arm64-d600
for tool in \
  "$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++" \
  "$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/ld.lld" \
  "$AOSP/prebuilts/jdk/jdk17/linux-x86/bin/java" \
  "$AOSP/prebuilts/jdk/jdk17/linux-x86/bin/javac"
do
  test -f "$tool"
  sha256sum "$tool"
done
"$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++" --version | head -5
"$AOSP/prebuilts/jdk/jdk17/linux-x86/bin/javac" -version
printf 'ccache_path='; command -v ccache
ccache --version | head -2
"""


BASELINE_PROBE = r"""
set -eu
OH=/opt/build-trees/oh610_lts_source
AOSP=/opt/build-trees/aosp-arm64-d600
printf 'oh_manifest_inputs\n'
sha256sum "$OH/.repo/manifest.xml"
git -C "$OH/.repo/manifests" rev-parse HEAD
git -C "$OH/.repo/manifests" status --porcelain=v1 --untracked-files=no | sha256sum
printf 'aosp_manifest_inputs\n'
sha256sum "$AOSP/.repo/manifest.xml"
git -C "$AOSP/.repo/manifests" rev-parse HEAD
git -C "$AOSP/.repo/manifests" status --porcelain=v1 --untracked-files=no | sha256sum
repo_id()
{
  path=$1
  printf 'repo=%s\n' "$path"
  git -C "$path" rev-parse HEAD
  git -C "$path" status --porcelain=v1 --untracked-files=no | sha256sum
  git -C "$path" diff --binary | sha256sum
}
repo_id "$OH/foundation/bundlemanager/bundle_framework"
repo_id "$OH/foundation/systemabilitymgr/safwk"
repo_id "$AOSP/frameworks/base"
repo_id "$AOSP/art"
repo_id "$AOSP/libnativehelper"
printf 'adapter_java_inputs\n'
sha256sum \
  "$AOSP/device/adapter/oh_adapter_framework/Android.bp" \
  "$AOSP/device/adapter/oh_adapter_framework/java/adapter/packagemanager/PackageManagerAdapter.java" \
  "$AOSP/device/adapter/oh_adapter_framework/java/adapter/packagemanager/PackageInfoBuilder.java"
printf 'current_java_artifact\n'
J="$AOSP/out/target/product/generic_arm64/system/framework/oh-adapter-framework.jar"
if test -f "$J"; then
  stat -c '%s %y %n' "$J"
  sha256sum "$J"
else
  echo "ABSENT $J"
fi
"""


BUILD_RUNTIME_PROBE = r"""
set -eu
printf 'docker='
if command -v docker >/dev/null 2>&1; then
  command -v docker
  docker version --format '{{.Client.Version}}' 2>/dev/null || true
else
  echo ABSENT
fi
printf 'ccache_stats\n'
ccache -s
printf 'aosp_out\n'
du -sk /opt/build-trees/aosp-arm64-d600/out 2>/dev/null || true
printf 'oh_out\n'
du -sk /opt/build-trees/oh610_lts_source/out 2>/dev/null || true
"""


SOURCE_STATE_PROBE = r"""
set -eu
OH=/opt/build-trees/oh610_lts_source
AOSP=/opt/build-trees/aosp-arm64-d600
sha256sum \
  "$AOSP/device/adapter/oh_adapter_framework/Android.bp" \
  "$AOSP/device/adapter/oh_adapter_framework/java/adapter/packagemanager/PackageManagerAdapter.java" \
  "$AOSP/device/adapter/oh_adapter_framework/java/adapter/packagemanager/PackageInfoBuilder.java"
for path in \
  "$OH/foundation/bundlemanager/bundle_framework" \
  "$OH/foundation/systemabilitymgr/safwk" \
  "$AOSP/frameworks/base" \
  "$AOSP/art" \
  "$AOSP/libnativehelper"
do
  printf 'repo=%s\n' "$path"
  git -C "$path" rev-parse HEAD
  git -C "$path" status --porcelain=v1 --untracked-files=no | sha256sum
  git -C "$path" diff --binary | sha256sum
done
"""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="AlexPC")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--remote-workspace",
        default="/opt/build-trees/.work/fn01-a04-provenance-preflight-r1",
    )
    parser.add_argument("--prewarm-aosp-graph", action="store_true")
    args = parser.parse_args(argv)

    if not REMOTE_WORK_RE.fullmatch(args.remote_workspace):
        raise SystemExit(
            "remote workspace must be a narrow "
            "/opt/build-trees/.work/fn01-a04-provenance-* path"
        )
    output_dir = args.output_dir.resolve()
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    probes = [
        run_probe(args.host, "host", HOST_PROBE, raw_dir),
        run_probe(args.host, "toolchain", TOOLCHAIN_PROBE, raw_dir),
        run_probe(args.host, "source-baseline", BASELINE_PROBE, raw_dir),
        run_probe(args.host, "build-runtime", BUILD_RUNTIME_PROBE, raw_dir),
    ]

    layout_script = f"""
set -eu
W={shlex.quote(args.remote_workspace)}
mkdir -p "$W/staging" "$W/out" "$W/cache" "$W/logs"
for path in "$W/staging" "$W/out" "$W/cache" "$W/logs"; do
  test -d "$path"
  stat -c '%U:%G %a %n' "$path"
done
"""
    layout = run_probe(args.host, "isolation-layout", layout_script, raw_dir)
    probes.append(layout)

    before = run_probe(
        args.host, "source-state-before-prewarm", SOURCE_STATE_PROBE, raw_dir
    )
    probes.append(before)
    prewarm: dict[str, Any] = {
        "requested": bool(args.prewarm_aosp_graph),
        "status": "NOT_RUN",
        "cache_warm_only": True,
        "artifacts_admitted": False,
        "final_generation_rebuild_required": True,
    }
    if args.prewarm_aosp_graph:
        prewarm_script = f"""
set -e
AOSP=/opt/build-trees/aosp-arm64-d600
W={shlex.quote(args.remote_workspace)}
export OUT_DIR="$W/out/aosp-graph"
export CCACHE_DIR="$W/cache/ccache"
export USE_CCACHE=1
export BUILD_BROKEN_DISABLE_BAZEL=true
mkdir -p "$OUT_DIR" "$CCACHE_DIR" "$W/logs"
cd "$AOSP"
. build/envsetup.sh >/dev/null
lunch oh_adapter-eng >/dev/null
m nothing -j8
"""
        prewarm_record = run_probe(
            args.host, "prewarm-aosp-graph", prewarm_script, raw_dir, timeout=1800
        )
        probes.append(prewarm_record)
        prewarm.update(
            {
                "status": "CACHE_WARM_ONLY",
                "probe": prewarm_record,
                "remote_out": f"{args.remote_workspace}/out/aosp-graph",
                "remote_cache": f"{args.remote_workspace}/cache/ccache",
            }
        )

    after = run_probe(
        args.host, "source-state-after-prewarm", SOURCE_STATE_PROBE, raw_dir
    )
    probes.append(after)
    source_unchanged = before["stdout_sha256"] == after["stdout_sha256"]
    if not source_unchanged:
        raise PreflightError("targeted AlexPC source state changed during preflight")

    receipt = {
        "schema_version": SCHEMA,
        "captured_at": utc_now(),
        "host_alias": args.host,
        "scope": "Fn01.A04 builder preflight only",
        "remote_layout": {
            "workspace": args.remote_workspace,
            "staging": f"{args.remote_workspace}/staging",
            "output": f"{args.remote_workspace}/out",
            "cache": f"{args.remote_workspace}/cache",
            "logs": f"{args.remote_workspace}/logs",
            "whole_dirty_worktree_sync_allowed": False,
            "final_import_policy": "exact hash-frozen source pack only",
        },
        "probes": probes,
        "source_state_unchanged": source_unchanged,
        "prewarm": prewarm,
        "claims": {
            "builder_preflight_complete": True,
            "build_pass": False,
            "target_deployment_generation_bound": False,
            "device_verified": False,
            "formal_verdict": "NOT_ISSUED",
        },
        "required_next_generation_rule": (
            "冻结最终 source manifest 后，在隔离 staging 中重新导入并重编；"
            "本预热 out/cache 中的任何产物都不得写入 generation receipt artifacts。"
        ),
    }
    receipt["receipt_body_sha256"] = sha256_bytes(
        json.dumps(
            receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    )
    write_json(output_dir / "alexpc-builder-preflight.json", receipt)
    print(f"RECEIPT={output_dir / 'alexpc-builder-preflight.json'}")
    print("BUILDER_PREFLIGHT_COMPLETE=true")
    print(f"PREWARM_STATUS={prewarm['status']}")
    print("BUILD_PASS=false")
    print("DEVICE_VERIFIED=false")
    print("FORMAL_VERDICT=NOT_ISSUED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PreflightError as exc:
        print(f"PREFLIGHT_REJECTED: {exc}", file=sys.stderr)
        print("BUILD_PASS=false", file=sys.stderr)
        print("DEVICE_VERIFIED=false", file=sys.stderr)
        print("FORMAL_VERDICT=NOT_ISSUED", file=sys.stderr)
        raise SystemExit(2)
