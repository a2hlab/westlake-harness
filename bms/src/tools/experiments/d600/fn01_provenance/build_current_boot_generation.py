#!/usr/bin/env python3
"""Build one hash-bound ARM64 ART boot generation on the AlexPC builder.

This worker runs on AlexPC.  The controller must first create a fresh work
directory containing:

  incoming/mainline-stubs/java/**/*.java
  incoming/oh-adapter-framework.jar
  incoming/coverage-manifest.json

The worker never deploys.  It freezes every consumed byte into ``frozen/``,
rebuilds the two locally-owned dex jars, bakes all nine bootclasspath segments,
and writes a receipt even on failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


EXPECTED_ACTIONS = ("Fn01.A01", "Fn01.A02", "Fn01.A03", "Fn01.A04")
RUNTIME_ORDER = (
    "core-oj",
    "core-libart",
    "core-icu4j",
    "okhttp",
    "bouncycastle",
    "apache-xml",
    "adapter-mainline-stubs",
    "framework",
    "oh-adapter-framework",
)
EXPECTED_WARNINGS = (
    "Type android.database.ContentObserver was not found",
    "Type android.app.SystemServiceRegistry$ContextAwareServiceProducerWithoutBinder was not found",
)
EXPECTED_WARNING_CLASS_SUFFIXES = (
    "android/provider/DeviceConfig$1.class:",
    "android/net/ConnectivityFrameworkInitializer$1.class:",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(value: Any) -> str:
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def file_fact(path: Path, root: Path) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(root)),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def canonical_java_manifest(root: Path) -> tuple[list[dict[str, Any]], str]:
    entries = []
    lines = []
    for path in sorted(root.rglob("*.java")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        digest = sha256(path)
        entries.append({"path": relative, "sha256": digest, "bytes": path.stat().st_size})
        lines.append(f"{digest}  {relative}\n")
    aggregate = hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()
    return entries, aggregate


def validate_coverage_manifest(value: dict[str, Any]) -> tuple[str, ...]:
    actions = value.get("covered_actions")
    if not isinstance(actions, list) or not actions:
        raise ValueError("coverage manifest needs a non-empty covered_actions list")
    if len(set(actions)) != len(actions):
        raise ValueError("coverage manifest has duplicate covered_actions")
    if any(action not in EXPECTED_ACTIONS for action in actions):
        raise ValueError(f"coverage includes unsupported action: {actions!r}")
    canonical = tuple(action for action in EXPECTED_ACTIONS if action in actions)
    if tuple(actions) != canonical:
        raise ValueError("covered_actions must use canonical Action order")
    proofs = value.get("coverage_proofs")
    if not isinstance(proofs, dict) or set(proofs) != set(actions):
        raise ValueError("coverage_proofs must exactly match covered_actions")
    for action in actions:
        proof = proofs[action]
        if not isinstance(proof, dict):
            raise ValueError(f"{action} coverage proof must be an object")
        producer_field = (
            "producer_receipt_ids"
            if value.get("schema_version") == "bridge.fn01.final-coverage.v1"
            else "producer_evidence"
        )
        for field in ("source_evidence", producer_field):
            values = proof.get(field)
            if not isinstance(values, list) or not values:
                raise ValueError(f"{action} missing non-empty {field}")
        if value.get("schema_version") == "bridge.fn01.final-coverage.v1":
            probes = proof.get("target_probe_receipt_ids")
            if not isinstance(probes, list):
                raise ValueError(f"{action} target_probe_receipt_ids must be a list")
    semantics = value.get("semantics", {})
    if semantics.get("authorizes_artifact_oracle_only") is not True:
        raise ValueError("coverage semantics must authorize artifact oracle only")
    if semantics.get("does_not_imply_behavior_pass") is not True:
        raise ValueError("coverage semantics must deny implicit behavior PASS")
    return tuple(actions)


class BuildFailure(RuntimeError):
    pass


class Builder:
    def __init__(self, aosp: Path, work: Path, frozen_build_id: str):
        self.aosp = aosp.resolve()
        self.jdk = self.aosp / "prebuilts" / "jdk" / "jdk17" / "linux-x86"
        self.work = work.resolve()
        self.frozen_build_id = frozen_build_id
        self.incoming = self.work / "incoming"
        self.frozen = self.work / "frozen"
        self.build = self.work / "build"
        self.products = self.work / "products"
        self.logs = self.work / "logs"
        self.receipt_path = self.work / "boot-build-receipt.json"
        self.stages: list[dict[str, Any]] = []
        self.receipt: dict[str, Any] = {
            "schema_version": "bridge.fn01.current-boot-build-receipt.v1",
            "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "status": {
                "build_pass": False,
                "device_verified": False,
                "formal_verdict": "NOT_ISSUED",
            },
            "semantics": {
                "build_pass_is_not_device_verified": True,
                "covered_actions_authorize_artifact_oracle_only": True,
                "covered_actions_do_not_imply_behavior_pass": True,
            },
            "runtime_bootclasspath_order": list(RUNTIME_ORDER),
            "expected_output_count": 27,
            "frozen_build_id": frozen_build_id,
        }

    def source(self, relative: str) -> Path:
        path = (self.aosp / relative).resolve()
        if self.aosp not in path.parents:
            raise BuildFailure(f"AOSP source escapes root: {relative}")
        if not path.is_file():
            raise BuildFailure(f"missing AOSP input: {relative}")
        return path

    def run(
        self,
        name: str,
        argv: Sequence[str],
        *,
        cwd: Path,
        env: dict[str, str] | None = None,
        allowed_rc: tuple[int, ...] = (0,),
    ) -> subprocess.CompletedProcess[str]:
        log = self.logs / f"{len(self.stages):02d}-{name}.log"
        command_env = os.environ.copy()
        if env:
            command_env.update(env)
        started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        result = subprocess.run(
            list(argv),
            cwd=cwd,
            env=command_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        log.write_text(result.stdout, encoding="utf-8")
        stage = {
            "name": name,
            "argv": list(argv),
            "cwd": str(cwd),
            "environment": env or {},
            "started_at": started,
            "returncode": result.returncode,
            "log": file_fact(log, self.work),
        }
        self.stages.append(stage)
        if result.returncode not in allowed_rc:
            raise BuildFailure(f"{name} failed rc={result.returncode}; see {log}")
        return result

    def freeze(self, source: Path, relative: str) -> Path:
        target = self.frozen / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return target

    def prepare(self) -> None:
        if self.receipt_path.exists() or self.frozen.exists() or self.build.exists():
            raise BuildFailure("work directory is not fresh; refuse overwrite")
        incoming_java = self.incoming / "mainline-stubs" / "java"
        incoming_oh = self.incoming / "oh-adapter-framework.jar"
        incoming_coverage = self.incoming / "coverage-manifest.json"
        for path in (incoming_java, incoming_oh, incoming_coverage):
            if not path.exists():
                raise BuildFailure(f"missing controller input: {path}")
        self.frozen.mkdir(parents=True)
        self.build.mkdir()
        self.products.mkdir()
        self.logs.mkdir()

        coverage = json.loads(incoming_coverage.read_text(encoding="utf-8"))
        covered_actions = validate_coverage_manifest(coverage)
        if coverage.get("frozen_build_id") != self.frozen_build_id:
            raise BuildFailure("coverage manifest frozen_build_id mismatch")
        self.receipt["covered_actions"] = list(covered_actions)
        self.receipt["qualification_only"] = coverage.get("qualification_only") is True
        self.receipt["eligible_for_deploy"] = coverage.get("eligible_for_deploy") is True
        parent_generation = coverage.get("parent_generation", {})
        if (
            parent_generation.get("superseded_for_final_bundle") is True
            and self.receipt["eligible_for_deploy"]
        ):
            raise BuildFailure("superseded parent generation cannot be eligible for deploy")
        frozen_coverage = self.freeze(incoming_coverage, "controller/coverage-manifest.json")
        self.receipt["coverage_manifest"] = file_fact(frozen_coverage, self.work)
        frozen_worker = self.freeze(Path(__file__).resolve(), "controller/build-worker.py")
        self.receipt["build_worker"] = file_fact(frozen_worker, self.work)

        shutil.copytree(incoming_java, self.frozen / "sources" / "mainline-stubs-java")
        java_entries, java_aggregate = canonical_java_manifest(
            self.frozen / "sources" / "mainline-stubs-java"
        )
        if len(java_entries) != 111:
            raise BuildFailure(f"expected 111 mainline stub sources, got {len(java_entries)}")
        self.receipt["mainline_stubs_source"] = {
            "schema": "sha256-two-spaces-relative-path-lf.v1",
            "entries": java_entries,
            "aggregate_sha256": java_aggregate,
        }

        source_map = {
            "sources/core-icu4j-combined.jar":
                "out/soong/.intermediates/external/icu/android_icu4j/core-icu4j/"
                "android_common/combined/core-icu4j.jar",
            "libs/core-oj-javac.jar":
                "out/soong/.intermediates/libcore/core-oj/android_common/javac/core-oj.jar",
            "libs/core-libart-javac.jar":
                "out/soong/.intermediates/libcore/core-libart/android_common/javac/"
                "core-libart.jar",
            "libs/framework-minus-apex-turbine.jar":
                "out/soong/.intermediates/frameworks/base/framework-minus-apex/"
                "android_common/turbine-combined/framework-minus-apex.jar",
            "src/tools/d8": "out/host/linux-x86/bin/d8",
            "framework/d8.jar": "out/host/linux-x86/framework/d8.jar",
            "src/tools/dex2oat64": "out/host/linux-x86/bin/dex2oat64",
            "src/tools/libart.so": "out/host/linux-x86/lib64/libart.so",
            "src/tools/libsigchain.so": "out/host/linux-x86/lib64/libsigchain.so",
            "src/tools/libc++.so": "out/host/linux-x86/lib64/libc++.so",
            "jdk/java": "prebuilts/jdk/jdk17/linux-x86/bin/java",
            "jdk/javac": "prebuilts/jdk/jdk17/linux-x86/bin/javac",
            "jdk/jar": "prebuilts/jdk/jdk17/linux-x86/bin/jar",
            "jdk/release": "prebuilts/jdk/jdk17/linux-x86/release",
            "jars/core-oj.jar":
                "out/target/product/generic_arm64/system/framework/core-oj.jar",
            "jars/core-libart.jar":
                "out/target/product/generic_arm64/system/framework/core-libart.jar",
            "jars/okhttp.jar":
                "out/target/product/generic_arm64/system/framework/okhttp.jar",
            "jars/bouncycastle.jar":
                "out/target/product/generic_arm64/system/framework/bouncycastle.jar",
            "jars/apache-xml.jar":
                "out/target/product/generic_arm64/system/framework/apache-xml.jar",
            "jars/framework.jar":
                "out/target/product/generic_arm64/system/framework/framework.jar",
        }
        original_before = {}
        for relative, aosp_relative in source_map.items():
            original = self.source(aosp_relative)
            original_before[aosp_relative] = sha256(original)
            self.freeze(original, relative)
        self.freeze(incoming_oh, "jars/oh-adapter-framework.jar")
        self.receipt["frozen_inputs"] = [
            file_fact(path, self.work)
            for path in sorted(self.frozen.rglob("*"))
            if path.is_file()
        ]
        self.receipt["aosp_original_before"] = original_before
        self.receipt["_source_map"] = source_map

    def make_jar(self, name: str, dex_dir: Path, output: Path) -> None:
        dex_files = sorted(path.name for path in dex_dir.glob("classes*.dex"))
        if not dex_files:
            raise BuildFailure(f"{name} produced no classes*.dex")
        self.run(
            f"{name}-jar",
            [str(self.jdk / "bin" / "jar"), "cf", str(output), *dex_files],
            cwd=dex_dir,
        )

    def build_owned_dex_jars(self) -> None:
        d8 = self.frozen / "tools" / "d8"
        core_build = self.build / "core-icu4j"
        core_dex = core_build / "dex"
        core_dex.mkdir(parents=True)
        self.run(
            "core-icu4j-d8",
            [
                str(d8),
                "--release",
                "--output",
                str(core_dex),
                "--lib",
                str(self.frozen / "libs" / "core-oj-javac.jar"),
                "--lib",
                str(self.frozen / "libs" / "core-libart-javac.jar"),
                str(self.frozen / "sources" / "core-icu4j-combined.jar"),
            ],
            cwd=self.work,
            env={
                "JAVA_HOME": str(self.jdk),
                "PATH": f"{self.jdk / 'bin'}:{os.environ.get('PATH', '')}",
            },
        )
        core_output = self.frozen / "jars" / "core-icu4j.jar"
        self.make_jar("core-icu4j", core_dex, core_output)

        stubs_build = self.build / "adapter-mainline-stubs"
        classes = stubs_build / "classes"
        dex = stubs_build / "dex"
        classes.mkdir(parents=True)
        dex.mkdir()
        sources = sorted((self.frozen / "sources" / "mainline-stubs-java").rglob("*.java"))
        self.run(
            "adapter-mainline-stubs-javac",
            [
                str(self.jdk / "bin" / "javac"),
                "-source",
                "17",
                "-target",
                "17",
                "-classpath",
                str(self.frozen / "libs" / "framework-minus-apex-turbine.jar"),
                "-d",
                str(classes),
                "-encoding",
                "UTF-8",
                "-nowarn",
                "-Xmaxerrs",
                "100",
                *[str(path) for path in sources],
            ],
            cwd=self.work,
            env={
                "JAVA_HOME": str(self.jdk),
                "PATH": f"{self.jdk / 'bin'}:{os.environ.get('PATH', '')}",
            },
        )
        class_files = sorted(classes.rglob("*.class"))
        if len(class_files) != 189:
            raise BuildFailure(f"expected 189 stub classes, got {len(class_files)}")
        d8_result = self.run(
            "adapter-mainline-stubs-d8",
            [
                str(d8),
                "--release",
                "--output",
                str(dex),
                "--lib",
                str(self.frozen / "libs" / "core-oj-javac.jar"),
                "--lib",
                str(self.frozen / "libs" / "core-libart-javac.jar"),
                *[str(path) for path in class_files],
            ],
            cwd=self.work,
            env={
                "JAVA_HOME": str(self.jdk),
                "PATH": f"{self.jdk / 'bin'}:{os.environ.get('PATH', '')}",
            },
        )
        normalized_output = d8_result.stdout.replace("`", "")
        warnings_seen = [warning for warning in EXPECTED_WARNINGS if warning in normalized_output]
        warning_headers = [
            line for line in d8_result.stdout.splitlines() if line.startswith("Warning in ")
        ]
        header_suffixes_seen = [
            suffix
            for suffix in EXPECTED_WARNING_CLASS_SUFFIXES
            if any(header.endswith(suffix) for header in warning_headers)
        ]
        self.receipt["adapter_mainline_stubs_warnings"] = {
            "expected": list(EXPECTED_WARNINGS),
            "seen": warnings_seen,
            "expected_class_suffixes": list(EXPECTED_WARNING_CLASS_SUFFIXES),
            "class_suffixes_seen": header_suffixes_seen,
            "raw_log": self.stages[-1]["log"],
            "classification": "RECORDED_NON_FATAL_MISSING_TYPE_WARNINGS",
        }
        if (
            tuple(warnings_seen) != EXPECTED_WARNINGS
            or tuple(header_suffixes_seen) != EXPECTED_WARNING_CLASS_SUFFIXES
            or len(warning_headers) != len(EXPECTED_WARNING_CLASS_SUFFIXES)
        ):
            raise BuildFailure("adapter-mainline-stubs warning set drifted")
        stubs_output = self.frozen / "jars" / "adapter-mainline-stubs.jar"
        self.make_jar("adapter-mainline-stubs", dex, stubs_output)

    def bake(self) -> None:
        jars = {role: self.frozen / "jars" / f"{role}.jar" for role in RUNTIME_ORDER}
        for role, path in jars.items():
            if not path.is_file():
                raise BuildFailure(f"missing frozen runtime jar {role}: {path}")
        self.receipt["runtime_jars"] = [
            {"role": role, **file_fact(path, self.work)}
            for role, path in jars.items()
        ]
        arm64 = self.products / "arm64"
        arm64.mkdir(parents=True)
        argv = [
            str(self.frozen / "tools" / "dex2oat64"),
            "--android-root=/system",
            "--instruction-set=arm64",
            "--base=0x70000000",
            "--compiler-filter=speed",
            "--runtime-arg",
            "-Xms64m",
            "--runtime-arg",
            "-Xmx512m",
            "--runtime-arg",
            "-Xverify:none",
            f"--image={arm64 / 'boot.art'}",
            f"--oat-file={arm64 / 'boot.oat'}",
        ]
        for role, path in jars.items():
            argv.extend(
                [
                    f"--dex-file={path}",
                    f"--dex-location=/system/android/framework/{role}.jar",
                ]
            )
        self.run(
            "dex2oat-arm64-9-segment",
            argv,
            cwd=self.work,
            env={
                "LD_LIBRARY_PATH": str(self.frozen / "tools"),
                "LD_PRELOAD": str(self.frozen / "tools" / "libsigchain.so"),
            },
        )
        expected_stems = ("boot", *[f"boot-{role}" for role in RUNTIME_ORDER[1:]])
        expected_names = {
            f"{stem}.{extension}"
            for stem in expected_stems
            for extension in ("art", "oat", "vdex")
        }
        observed = {path.name for path in arm64.iterdir() if path.is_file()}
        if observed != expected_names:
            raise BuildFailure(
                f"boot output set mismatch missing={sorted(expected_names - observed)} "
                f"extra={sorted(observed - expected_names)}"
            )
        outputs = [
            {"role": f"boot:{name}", **file_fact(arm64 / name, self.work)}
            for name in sorted(expected_names)
        ]
        if any(item["bytes"] == 0 for item in outputs):
            raise BuildFailure("one or more boot outputs are empty")
        self.receipt["outputs"] = outputs

    def verify_no_drift(self) -> None:
        source_map = self.receipt.pop("_source_map")
        after = {
            aosp_relative: sha256(self.source(aosp_relative))
            for aosp_relative in source_map.values()
        }
        self.receipt["aosp_original_after"] = after
        self.receipt["aosp_original_unchanged"] = (
            after == self.receipt["aosp_original_before"]
        )
        if not self.receipt["aosp_original_unchanged"]:
            raise BuildFailure("AOSP source/tool inputs changed during build")
        _, after_stubs = canonical_java_manifest(
            self.frozen / "sources" / "mainline-stubs-java"
        )
        self.receipt["mainline_stubs_source"]["after_aggregate_sha256"] = after_stubs
        if after_stubs != self.receipt["mainline_stubs_source"]["aggregate_sha256"]:
            raise BuildFailure("frozen mainline stubs changed during build")

    def write_receipt(self, failure: str | None = None) -> None:
        self.receipt["stages"] = self.stages
        self.receipt["builder_identity"] = {
            "hostname": platform.node(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": sys.version,
            "aosp_root": str(self.aosp),
            "work": str(self.work),
        }
        if failure is not None:
            self.receipt["failure"] = failure
        closure_entries = []
        for closure_root in (self.frozen, self.logs, self.products):
            if not closure_root.exists():
                continue
            closure_entries.extend(
                file_fact(path, self.work)
                for path in sorted(closure_root.rglob("*"))
                if path.is_file()
            )
        closure_path = self.work / "closure-manifest.sha256"
        closure_path.write_text(
            "".join(f"{item['sha256']}  {item['path']}\n" for item in closure_entries),
            encoding="utf-8",
        )
        self.receipt["closure_manifest"] = {
            **file_fact(closure_path, self.work),
            "entry_count": len(closure_entries),
        }
        body = json.dumps(self.receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.receipt["receipt_body_sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
        self.receipt_path.write_text(
            json.dumps(self.receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        receipt_sha = sha256(self.receipt_path)
        generation_digest = hashlib.sha256(
            f"{receipt_sha}\n{sha256(closure_path)}\n".encode("ascii")
        ).hexdigest()
        identity = {
            "schema_version": "bridge.fn01.current-boot-generation-identity.v1",
            "generation_id": f"Fn01.boot-{generation_digest[:20]}",
            "generation_digest": generation_digest,
            "build_receipt": file_fact(self.receipt_path, self.work),
            "closure_manifest": file_fact(closure_path, self.work),
            "covered_actions": self.receipt.get("covered_actions", []),
            "qualification_only": self.receipt.get("qualification_only", False),
            "eligible_for_deploy": self.receipt.get("eligible_for_deploy", False),
            "status": self.receipt["status"],
            "semantics": self.receipt["semantics"],
        }
        identity_body = json.dumps(
            identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        identity["identity_body_sha256"] = hashlib.sha256(
            identity_body.encode("utf-8")
        ).hexdigest()
        identity_path = self.work / "generation-identity.json"
        identity_path.write_text(
            json.dumps(identity, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        (self.work / "generation-identity.sha256").write_text(
            f"{sha256(identity_path)}  generation-identity.json\n",
            encoding="ascii",
        )
        producer_receipt = {
            "schema_version": "bridge.fn01.producer-receipt.v1",
            "receipt_id": f"boot-{self.frozen_build_id}",
            "frozen_build_id": self.frozen_build_id,
            "producer_kind": "boot",
            "generation_id": identity["generation_id"],
            "qualification_only": self.receipt.get("qualification_only", False),
            "status": {
                "producer_pass": self.receipt["status"]["build_pass"],
                "device_verified": False,
                "formal_verdict": "NOT_ISSUED",
            },
            "build_receipt": file_fact(self.receipt_path, self.work),
            "closure_manifest": file_fact(closure_path, self.work),
            "outputs": self.receipt.get("outputs", []),
        }
        producer_receipt["receipt_body_sha256"] = canonical_json_sha256(
            producer_receipt
        )
        producer_path = self.work / "producer-receipt.json"
        producer_path.write_text(
            json.dumps(producer_receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        (self.work / "producer-receipt.sha256").write_text(
            f"{sha256(producer_path)}  producer-receipt.json\n",
            encoding="ascii",
        )

    def execute(self) -> int:
        failure = None
        try:
            self.prepare()
            self.build_owned_dex_jars()
            self.bake()
            self.verify_no_drift()
            self.receipt["status"]["build_pass"] = True
        except Exception as error:  # receipt is required for every failed attempt
            failure = f"{type(error).__name__}: {error}"
        self.write_receipt(failure)
        print(f"RECEIPT={self.receipt_path}")
        print(f"BUILD_PASS={str(self.receipt['status']['build_pass']).lower()}")
        print("DEVICE_VERIFIED=false")
        print("FORMAL_VERDICT=NOT_ISSUED")
        if failure:
            print(f"FAILURE={failure}")
            return 1
        return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aosp-root", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--frozen-build-id", required=True)
    args = parser.parse_args(argv)
    return Builder(args.aosp_root, args.work, args.frozen_build_id).execute()


if __name__ == "__main__":
    raise SystemExit(main())
