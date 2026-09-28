#!/usr/bin/env python3
"""Positive controls and one focused mutant for every runtime-generation gate."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SUITE = HERE.parent
FIXTURES = HERE / "fixtures"
SPEC = importlib.util.spec_from_file_location(
    "runtime_generation_verify_candidate", SUITE / "verify_candidate.py"
)
assert SPEC and SPEC.loader
VERIFY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VERIFY
SPEC.loader.exec_module(VERIFY)

TOKEN_A = "westlake-route-a-generation-20260713-a"
TOKEN_B = "westlake-route-a-generation-20260713-b"
RUNTIME_SOURCE = r'''// Synthetic source-only oracle. It is never product code.
int RegisterNativeMethods() {
    auto *libRuntime = dlopen("liboh_android_runtime.so", RTLD_NOW | RTLD_NOLOAD);
    if (!libRuntime) {
        return -10;
    }
    auto *runtimeAlias = libRuntime;
    if (!runtimeAlias) {
        return -11;
    }
    if (!VerifyLoadedAndroidRuntime(libRuntime)) {
        return -12;
    }
    auto startReg = dlsym(libRuntime, "AndroidRuntime::startReg");
    if (!startReg) {
        return -13;
    }
    return startReg(nullptr);
}

int Preload() {
    auto *bridgeHandle = dlopen("liboh_adapter_bridge.so", RTLD_NOW | RTLD_NOLOAD);
    if (!bridgeHandle) {
        return -20;
    }
    if (!VerifyLoadedAdapterBridge(bridgeHandle)) {
        return -21;
    }
    CallStaticVoidMethod();
    if (ExceptionCheck()) {
        ExceptionDescribe();
        return -22;
    }
    return 0;
}
'''


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def find_tool(env_name: str, basename: str) -> Path:
    if os.environ.get(env_name):
        path = Path(os.environ[env_name])
        if path.is_file():
            return path
    sdk = Path(
        "/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin"
    )
    path = sdk / basename
    if path.is_file():
        return path
    found = shutil.which(basename)
    if found:
        return Path(found)
    raise unittest.SkipTest(f"required tool not found: {basename}")


class CandidateBuilder:
    def __init__(self, project: Path, cc: Path, readelf: Path) -> None:
        self.project = project
        self.source = project / "source"
        self.build = project / "build"
        self.cc = cc
        self.readelf = readelf
        self.manifest_path = self.build / "meta/candidate.json"
        self.manifest: dict[str, object] = {}
        self.source.mkdir(parents=True)
        self.build.mkdir(parents=True)
        (self.build / "toolchain").mkdir()
        (self.build / "toolchain/clang.receipt").write_text(
            "synthetic validator-oracle tool receipt\n", encoding="utf-8"
        )
        (self.source / "control").mkdir()
        (self.source / "control/runtime_control.cpp").write_text(
            RUNTIME_SOURCE, encoding="utf-8"
        )
        (self.source / "fixtures").mkdir()
        for path in FIXTURES.glob("*.c"):
            shutil.copy2(path, self.source / "fixtures" / path.name)

    def command(self, argv: list[str]) -> None:
        result = subprocess.run(
            argv,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"compile failed: {' '.join(argv)}\n{result.stdout}")

    def compile(
        self,
        *,
        relative: str,
        source: str,
        soname: str,
        token: str = TOKEN_A,
        anchor: str | None = None,
        target: str = "aarch64-linux-ohos",
        build_id: str = "sha1",
        runpath: str | None = None,
        provider_dir: Path | None = None,
        allow_undefined: bool = False,
    ) -> Path:
        output = self.build / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        source_path = self.source / source
        argv = [
            str(self.cc),
            f"--target={target}",
            "-fuse-ld=lld",
            "-nostdlib",
            "-fPIC",
            "-fno-stack-protector",
            "-shared",
            f'-DWESTLAKE_GENERATION_TOKEN="{token}"',
        ]
        if anchor:
            argv.append(f"-DWESTLAKE_ANCHOR={anchor}")
        argv.extend(
            [
                str(source_path),
                f"-Wl,-soname,{soname}",
                f"-Wl,--build-id={build_id}",
                "-Wl,-z,now",
                "-Wl,-z,relro",
            ]
        )
        if runpath:
            argv.append(f"-Wl,-rpath,{runpath}")
        if provider_dir:
            argv.extend(
                [
                    f"-L{provider_dir}",
                    "-Wl,--no-as-needed",
                    "-Wl,-l:libshadow.so",
                ]
            )
        if allow_undefined:
            argv.append("-Wl,--allow-shlib-undefined")
        else:
            argv.extend(["-Wl,-z,defs", "-Wl,--no-allow-shlib-undefined"])
        argv.extend(["-o", str(output)])
        self.command(argv)
        return output

    def elf_info(self, path: Path):
        return VERIFY.inspect_elf(self.readelf, path)

    def artifact(
        self,
        *,
        role: str,
        relative: str,
        namespace: str,
        soname: str,
        source: str,
    ) -> dict[str, object]:
        path = self.build / relative
        info = self.elf_info(path)
        receipt_rel = f"receipts/{role}.json"
        receipt_path = self.build / receipt_rel
        receipt = {
            "schema": VERIFY.LINK_SCHEMA,
            "artifact_role": role,
            "artifact_sha256": sha(path),
            "generation_token": TOKEN_A,
            "output": relative,
            "argv": [
                "build/toolchain/clang.receipt",
                "--target=aarch64-linux-ohos",
                "-Wl,-z,defs",
                "-Wl,--no-allow-shlib-undefined",
                f"source/{source}",
                "-o",
                f"build/{relative}",
            ],
            "inputs": [
                {"root": "source", "path": source, "sha256": sha(self.source / source)},
                {
                    "root": "build",
                    "path": "toolchain/clang.receipt",
                    "sha256": sha(self.build / "toolchain/clang.receipt"),
                },
            ],
        }
        write_json(receipt_path, receipt)
        return {
            "role": role,
            "path": relative,
            "kind": "shared",
            "soname": soname,
            "sha256": sha(path),
            "build_id": info.build_id,
            "namespace": namespace,
            "provenance": "generated",
            "link_receipt": receipt_rel,
            "link_receipt_sha256": sha(receipt_path),
        }

    def build_positive(self) -> None:
        parent = self.build / "payload/parent"
        child = self.build / "payload/child"
        self.compile(
            relative="payload/parent/libappspawnx_host.so",
            source="fixtures/elf_root.c",
            soname="libappspawnx_host.so",
            anchor="appspawn_host_anchor",
        )
        self.compile(
            relative="payload/parent/liboh_android_runtime.so",
            source="fixtures/elf_root.c",
            soname="liboh_android_runtime.so",
            anchor="android_runtime_anchor",
        )
        self.compile(
            relative="payload/parent/liboh_adapter_bridge.so",
            source="fixtures/elf_root.c",
            soname="liboh_adapter_bridge.so",
            anchor="adapter_bridge_anchor",
        )
        self.compile(
            relative="payload/parent/libshadow.so",
            source="fixtures/elf_provider.c",
            soname="libshadow.so",
        )
        self.compile(
            relative="payload/child/libshadow.so",
            source="fixtures/elf_provider.c",
            soname="libshadow.so",
        )
        self.compile(
            relative="payload/parent/libparent_consumer.so",
            source="fixtures/elf_consumer.c",
            soname="libparent_consumer.so",
            provider_dir=parent,
        )
        self.compile(
            relative="payload/child/libchild_consumer.so",
            source="fixtures/elf_consumer.c",
            soname="libchild_consumer.so",
            provider_dir=child,
        )
        specs = [
            ("appspawn_host", "payload/parent/libappspawnx_host.so", "parent", "libappspawnx_host.so", "fixtures/elf_root.c"),
            ("android_runtime", "payload/parent/liboh_android_runtime.so", "parent", "liboh_android_runtime.so", "fixtures/elf_root.c"),
            ("adapter_bridge", "payload/parent/liboh_adapter_bridge.so", "parent", "liboh_adapter_bridge.so", "fixtures/elf_root.c"),
            ("parent_shadow", "payload/parent/libshadow.so", "parent", "libshadow.so", "fixtures/elf_provider.c"),
            ("child_shadow", "payload/child/libshadow.so", "child", "libshadow.so", "fixtures/elf_provider.c"),
            ("parent_consumer", "payload/parent/libparent_consumer.so", "parent", "libparent_consumer.so", "fixtures/elf_consumer.c"),
            ("child_consumer", "payload/child/libchild_consumer.so", "child", "libchild_consumer.so", "fixtures/elf_consumer.c"),
        ]
        artifacts = [
            self.artifact(
                role=role,
                relative=relative,
                namespace=namespace,
                soname=soname,
                source=source,
            )
            for role, relative, namespace, soname, source in specs
        ]
        source_files = sorted(
            path.relative_to(self.source).as_posix()
            for path in self.source.rglob("*")
            if path.is_file()
        )
        source_entries = [
            {"path": relative, "sha256": sha(self.source / relative)}
            for relative in source_files
        ]
        source_digest = VERIFY.tree_digest(
            (item["path"], item["sha256"]) for item in source_entries
        )
        control_sha = sha(self.source / "control/runtime_control.cpp")
        self.manifest = {
            "schema": VERIFY.SCHEMA,
            "status": "candidate",
            "device_verified": False,
            "generation_id": TOKEN_A,
            "generation_token": TOKEN_A,
            "source_snapshot": {"digest": source_digest, "files": source_entries},
            "namespaces": [
                {"id": "parent", "search_paths": ["payload/parent"], "imports": []},
                {"id": "child", "search_paths": ["payload/child"], "imports": []},
            ],
            "artifacts": artifacts,
            "dynamic_roots": [
                {
                    "id": "android_runtime",
                    "caller_role": "appspawn_host",
                    "artifact_role": "android_runtime",
                    "namespace": "parent",
                    "soname": "liboh_android_runtime.so",
                    "source": "control/runtime_control.cpp",
                    "source_sha256": control_sha,
                    "function_anchor": "int RegisterNativeMethods()",
                    "load_anchor_regex": r'dlopen\("liboh_android_runtime\.so"[^;]*;',
                    "identity_anchor_regex": r"VerifyLoadedAndroidRuntime\(libRuntime\)",
                    "first_side_effect_regex": r"return\s+startReg\(",
                    "handle_variable": "libRuntime",
                    "failure_contract": "return_nonzero",
                },
                {
                    "id": "adapter_bridge",
                    "caller_role": "appspawn_host",
                    "artifact_role": "adapter_bridge",
                    "namespace": "parent",
                    "soname": "liboh_adapter_bridge.so",
                    "source": "control/runtime_control.cpp",
                    "source_sha256": control_sha,
                    "function_anchor": "int Preload()",
                    "load_anchor_regex": r'dlopen\("liboh_adapter_bridge\.so"[^;]*;',
                    "identity_anchor_regex": r"VerifyLoadedAdapterBridge\(bridgeHandle\)",
                    "first_side_effect_regex": r"CallStaticVoidMethod\(",
                    "handle_variable": "bridgeHandle",
                    "failure_contract": "return_nonzero",
                },
            ],
            "source_contracts": [
                {
                    "id": "runtime_root_failure",
                    "source": "control/runtime_control.cpp",
                    "source_sha256": control_sha,
                    "function_anchor": "int RegisterNativeMethods()",
                    "handle_variable": "runtimeAlias",
                },
                {
                    "id": "startreg_failure",
                    "source": "control/runtime_control.cpp",
                    "source_sha256": control_sha,
                    "function_anchor": "int RegisterNativeMethods()",
                    "symbol_variable": "startReg",
                },
                {
                    "id": "preload_throwable_failure",
                    "source": "control/runtime_control.cpp",
                    "source_sha256": control_sha,
                    "function_anchor": "int Preload()",
                },
            ],
            "fd_admissions": [],
        }
        self.refresh_fd_admissions()
        self.save_manifest()

    def refresh_fd_admissions(self) -> None:
        roots = {item["id"]: item for item in self.manifest["dynamic_roots"]}
        artifacts = {item["role"]: item for item in self.manifest["artifacts"]}
        values = []
        for root_id in sorted(roots):
            role = roots[root_id]["artifact_role"]
            artifact = artifacts[role]
            identity = VERIFY.canonical_stat(self.build / artifact["path"])
            mapping = dict(identity)
            mapping["namespace"] = artifact["namespace"]
            values.append(
                {
                    "artifact_role": role,
                    "mode": "sealed_fd",
                    "mapping_policy": "single_identity",
                    "open_flags": ["O_CLOEXEC", "O_NOFOLLOW"],
                    "path": artifact["path"],
                    "path_before": dict(identity),
                    "fd_before": dict(identity),
                    "fd_after": dict(identity),
                    "path_after": dict(identity),
                    "mappings": [mapping],
                }
            )
        self.manifest["fd_admissions"] = values

    def save_manifest(self) -> None:
        write_json(self.manifest_path, self.manifest)

    def refresh_sources(self) -> None:
        snapshot = self.manifest["source_snapshot"]
        for item in snapshot["files"]:
            item["sha256"] = sha(self.source / item["path"])
        snapshot["digest"] = VERIFY.tree_digest(
            (item["path"], item["sha256"]) for item in snapshot["files"]
        )
        source_by_path = {item["path"]: item["sha256"] for item in snapshot["files"]}
        for value in self.manifest["dynamic_roots"] + self.manifest["source_contracts"]:
            value["source_sha256"] = source_by_path[value["source"]]
        for artifact in self.manifest["artifacts"]:
            receipt = self.build / artifact["link_receipt"]
            data = json.loads(receipt.read_text(encoding="utf-8"))
            for item in data["inputs"]:
                if item["root"] == "source":
                    item["sha256"] = source_by_path[item["path"]]
            write_json(receipt, data)
            artifact["link_receipt_sha256"] = sha(receipt)
        self.save_manifest()

    def replace_artifact(
        self,
        *,
        role: str,
        replacement: Path,
        expected_soname: str | None = None,
        receipt_token: str = TOKEN_A,
    ) -> None:
        artifact = next(item for item in self.manifest["artifacts"] if item["role"] == role)
        destination = self.build / artifact["path"]
        shutil.copy2(replacement, destination)
        info = self.elf_info(destination)
        artifact["sha256"] = sha(destination)
        artifact["build_id"] = info.build_id
        if expected_soname is not None:
            artifact["soname"] = expected_soname
        receipt_path = self.build / artifact["link_receipt"]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["artifact_sha256"] = artifact["sha256"]
        receipt["generation_token"] = receipt_token
        write_json(receipt_path, receipt)
        artifact["link_receipt_sha256"] = sha(receipt_path)
        self.refresh_fd_admissions()
        self.save_manifest()

    def add_generated_artifact(
        self, *, role: str, relative: str, namespace: str, soname: str, source: str
    ) -> None:
        self.manifest["artifacts"].append(
            self.artifact(
                role=role,
                relative=relative,
                namespace=namespace,
                soname=soname,
                source=source,
            )
        )
        self.save_manifest()


class RuntimeGenerationVerifierTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cc = find_tool("OH_CC", "clang")
        cls.readelf = find_tool("OH_READELF", "llvm-readelf")
        cls.class_tmp = tempfile.TemporaryDirectory(prefix="westlake-runtime-redteam-")
        cls.seed = Path(cls.class_tmp.name) / "seed-project"
        builder = CandidateBuilder(cls.seed, cls.cc, cls.readelf)
        builder.build_positive()
        mutant = cls.seed / "mutants"
        mutant.mkdir()
        builder.compile(
            relative="mutants/libbridge.wrong_soname.so",
            source="fixtures/elf_root.c",
            soname="libwrong_bridge.so",
            anchor="wrong_bridge_anchor",
        )
        builder.compile(
            relative="mutants/libbridge.runpath.so",
            source="fixtures/elf_root.c",
            soname="liboh_adapter_bridge.so",
            anchor="runpath_bridge_anchor",
            runpath="/unreviewed/provider/path",
        )
        builder.compile(
            relative="mutants/libbridge.md5.so",
            source="fixtures/elf_root.c",
            soname="liboh_adapter_bridge.so",
            anchor="md5_bridge_anchor",
            build_id="md5",
        )
        builder.compile(
            relative="mutants/libbridge.generation_b.so",
            source="fixtures/elf_root.c",
            soname="liboh_adapter_bridge.so",
            anchor="generation_b_bridge_anchor",
            token=TOKEN_B,
        )
        builder.compile(
            relative="mutants/libshadow.arm32.so",
            source="fixtures/elf_provider.c",
            soname="libshadow.so",
            target="arm-linux-ohos",
        )
        builder.compile(
            relative="payload/parent/libunresolved_consumer.so",
            source="fixtures/elf_unresolved.c",
            soname="libunresolved_consumer.so",
            allow_undefined=True,
        )
        cls.seed_manifest = json.loads(builder.manifest_path.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.class_tmp.cleanup()

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="westlake-runtime-case-")
        self.project = Path(self.tmp.name) / "project"
        shutil.copytree(self.seed, self.project)
        self.builder = CandidateBuilder.__new__(CandidateBuilder)
        self.builder.project = self.project
        self.builder.source = self.project / "source"
        self.builder.build = self.project / "build"
        self.builder.cc = self.cc
        self.builder.readelf = self.readelf
        self.builder.manifest_path = self.builder.build / "meta/candidate.json"
        self.builder.manifest = json.loads(
            self.builder.manifest_path.read_text(encoding="utf-8")
        )
        self.builder.refresh_fd_admissions()
        self.builder.save_manifest()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def verify(self) -> dict[str, object]:
        verifier = VERIFY.Verifier(
            project_root=self.project,
            source_root=self.builder.source,
            build_root=self.builder.build,
            manifest_path=self.builder.manifest_path,
            readelf=self.readelf,
        )
        return verifier.verify()

    def assert_mutant(self, code: str) -> None:
        with self.assertRaises(VERIFY.GateError) as caught:
            self.verify()
        self.assertEqual(code, caught.exception.code, caught.exception)

    def edit_control(self, old: str, new: str, *, refresh: bool = True) -> None:
        path = self.builder.source / "control/runtime_control.cpp"
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")
        if refresh:
            self.builder.refresh_sources()

    def test_00_positive_control_covers_every_gate(self) -> None:
        report = self.verify()
        self.assertTrue(report["eligible_for_route_a_device_admission"])
        self.assertFalse(report["device_verified"])
        self.assertFalse(report["first_frame_proven"])
        gates = {item["gate"] for item in report["checks"]}
        self.assertEqual({f"G{value:02d}_" for value in range(1, 21)}, {gate[:4] for gate in gates})

    def test_01_stale_source_json_mutant(self) -> None:
        self.edit_control("return -10;", "return -1010;", refresh=False)
        self.assert_mutant("hash_drift")

    def test_02_symlink_input_mutant(self) -> None:
        path = self.builder.source / "control/runtime_control.cpp"
        external = Path(self.tmp.name) / "external.cpp"
        external.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        path.unlink()
        path.symlink_to(external)
        self.assert_mutant("symlink_input")

    def test_03_elf32_mutant(self) -> None:
        self.builder.replace_artifact(
            role="parent_shadow",
            replacement=self.builder.build / "mutants/libshadow.arm32.so",
        )
        self.assert_mutant("elf64_aarch64")

    def test_04_soname_mutant(self) -> None:
        self.builder.replace_artifact(
            role="adapter_bridge",
            replacement=self.builder.build / "mutants/libbridge.wrong_soname.so",
        )
        self.assert_mutant("soname")

    def test_05_short_build_id_mutant(self) -> None:
        self.builder.replace_artifact(
            role="adapter_bridge",
            replacement=self.builder.build / "mutants/libbridge.md5.so",
        )
        self.assert_mutant("build_id")

    def test_06_runpath_mutant(self) -> None:
        self.builder.replace_artifact(
            role="adapter_bridge",
            replacement=self.builder.build / "mutants/libbridge.runpath.so",
        )
        self.assert_mutant("unsafe_dynamic_tag")

    def test_07_missing_dynamic_root_mutant(self) -> None:
        self.builder.manifest["dynamic_roots"] = [
            item
            for item in self.builder.manifest["dynamic_roots"]
            if item["id"] != "adapter_bridge"
        ]
        self.builder.refresh_fd_admissions()
        self.builder.save_manifest()
        self.assert_mutant("dynamic_root_missing")

    def test_08_dynamic_root_callsite_mutant(self) -> None:
        self.edit_control("liboh_android_runtime.so", "libwrong_runtime.so")
        self.assert_mutant("source_callsite")

    def test_09_dynamic_root_fake_success_mutant(self) -> None:
        self.edit_control("return -10;", "return 0;")
        self.assert_mutant("dynamic_root_fake_success")

    def test_10_runtime_contract_fake_success_mutant(self) -> None:
        self.edit_control("return -11;", "return 0;")
        self.assert_mutant("runtime_fake_success")

    def test_11_startreg_fake_success_mutant(self) -> None:
        self.edit_control("return -13;", "return 0;")
        self.assert_mutant("startreg_fake_success")

    def test_12_preload_fake_success_mutant(self) -> None:
        self.edit_control("return -22;", "return 0;")
        self.assert_mutant("preload_fake_success")

    def test_13_namespace_unreachable_mutant(self) -> None:
        artifact = next(
            item for item in self.builder.manifest["artifacts"] if item["role"] == "adapter_bridge"
        )
        old = self.builder.build / artifact["path"]
        new_rel = "payload/child/liboh_adapter_bridge.so"
        new = self.builder.build / new_rel
        shutil.move(old, new)
        artifact["path"] = new_rel
        artifact["namespace"] = "child"
        receipt_path = self.builder.build / artifact["link_receipt"]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["output"] = new_rel
        write_json(receipt_path, receipt)
        artifact["link_receipt_sha256"] = sha(receipt_path)
        self.builder.refresh_fd_admissions()
        self.builder.save_manifest()
        self.assert_mutant("namespace_reachability")

    def test_14_same_soname_reachable_twice_mutant(self) -> None:
        parent = next(
            item for item in self.builder.manifest["namespaces"] if item["id"] == "parent"
        )
        parent["imports"] = ["child"]
        self.builder.save_manifest()
        self.assert_mutant("soname_ambiguous")

    def test_15_relaxed_link_argv_mutant(self) -> None:
        artifact = self.builder.manifest["artifacts"][0]
        receipt_path = self.builder.build / artifact["link_receipt"]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["argv"] = [
            token
            for token in receipt["argv"]
            if token not in ("-Wl,-z,defs", "-Wl,--no-allow-shlib-undefined")
        ] + ["-Wl,--allow-shlib-undefined"]
        write_json(receipt_path, receipt)
        artifact["link_receipt_sha256"] = sha(receipt_path)
        self.builder.save_manifest()
        self.assert_mutant("strict_link_argv")

    def test_16_project_local_argv_escape_mutant(self) -> None:
        artifact = self.builder.manifest["artifacts"][0]
        receipt_path = self.builder.build / artifact["link_receipt"]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["argv"].append("/opt/outside-westlake/leak.c")
        write_json(receipt_path, receipt)
        artifact["link_receipt_sha256"] = sha(receipt_path)
        self.builder.save_manifest()
        self.assert_mutant("argv_path_escape")

    def test_17_strong_undefined_mutant(self) -> None:
        source = "fixtures/elf_unresolved.c"
        relative = "payload/parent/libunresolved_consumer.so"
        self.builder.add_generated_artifact(
            role="unresolved_consumer",
            relative=relative,
            namespace="parent",
            soname="libunresolved_consumer.so",
            source=source,
        )
        self.assert_mutant("strong_undefined")

    def test_18_mixed_generation_token_mutant(self) -> None:
        self.builder.replace_artifact(
            role="adapter_bridge",
            replacement=self.builder.build / "mutants/libbridge.generation_b.so",
        )
        self.assert_mutant("generation_token_mismatch")

    def test_19_fd_path_swap_mutant(self) -> None:
        admission = self.builder.manifest["fd_admissions"][0]
        admission["path_after"]["ino"] += 1
        self.builder.save_manifest()
        self.assert_mutant("fd_path_swap")

    def test_20_duplicate_mapping_mutant(self) -> None:
        admission = self.builder.manifest["fd_admissions"][0]
        duplicate = copy.deepcopy(admission["mappings"][0])
        duplicate["ino"] += 1
        admission["mappings"].append(duplicate)
        self.builder.save_manifest()
        self.assert_mutant("fd_duplicate_mapping")

    def test_21_parameterized_cli_emits_current_byte_verdict(self) -> None:
        report = self.builder.build / "meta/verdict.json"
        result = subprocess.run(
            [
                sys.executable,
                str(SUITE / "verify_candidate.py"),
                "--project-root",
                str(self.project),
                "--source-root",
                str(self.builder.source),
                "--build-root",
                str(self.builder.build),
                "--manifest",
                str(self.builder.manifest_path),
                "--readelf",
                str(self.readelf),
                "--report",
                str(report),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self.assertEqual(0, result.returncode, result.stdout)
        value = json.loads(report.read_text(encoding="utf-8"))
        self.assertTrue(value["eligible_for_route_a_device_admission"])
        self.assertEqual(sha(self.builder.manifest_path), value["manifest_sha256"])
        self.assertEqual("exact source/artifact/receipt bytes only", value["decision_scope"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
