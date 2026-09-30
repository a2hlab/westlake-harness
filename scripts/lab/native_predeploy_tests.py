"""Offline filesystem/ELF fixtures, plus the retained real-package reader replay."""

import copy
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

from native_gate_common import Package, apply_exceptions, digest_bytes, read_json, sha256
from native_needed_gate import ElfReader, parse_dynamic, scan_domains
from native_predeploy import ROOT, check_package


EMPTY = {"schema_version": 1, "exceptions": []}
REPLAY = ROOT / "benchmark/2026-10-01-native-predeploy-gates"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def elf_bytes(needed=(), soname="libtest.so"):
    strings = bytearray(b"\0")
    names = []
    for name in [soname, *needed]:
        names.append(len(strings))
        strings.extend(name.encode() + b"\0")
    dynamic_size = 16 * (4 + len(needed))
    dynamic_offset = 64 + 2 * 56
    string_offset = dynamic_offset + dynamic_size
    address = 0x10000
    dynamic = [(5, address + string_offset), (10, len(strings)), (14, names[0])]
    dynamic.extend((1, offset) for offset in names[1:])
    dynamic.append((0, 0))
    total = string_offset + len(strings)
    identity = b"\x7fELF" + bytes([2, 1, 1]) + bytes(9)
    header = struct.pack("<16sHHIQQQIHHHHHH", identity, 3, 183, 1, 0, 64, 0, 0, 64, 56, 2, 0, 0, 0)
    load = struct.pack("<IIQQQQQQ", 1, 4, 0, address, address, total, total, 0x1000)
    section = struct.pack("<IIQQQQQQ", 2, 4, dynamic_offset, address + dynamic_offset,
                          address + dynamic_offset, dynamic_size, dynamic_size, 8)
    return header + load + section + b"".join(struct.pack("<QQ", tag, value) for tag, value in dynamic) + strings


class Fixture:
    def __init__(self, root, bad_namespace=False, bad_jni=False, unknown=False):
        self.root = root
        self.package = root / "package"
        self.inputs_dir = root / "inputs"
        self.inputs_dir.mkdir(parents=True)
        files = {"payload/runtime/appspawn-x": elf_bytes(soname="host"),
                 "payload/android/lib64/libruntime.so": elf_bytes(soname="libruntime.so"),
                 "payload/android/lib64/westlake_flutter/libandroid.so": elf_bytes(soname="libandroid.so"),
                 "payload/android/framework/framework.jar": b"synthetic-jar-identity"}
        for name, data in files.items():
            target = self.package / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        self.manifest = dict(schema=1, files={name: digest_bytes(data) for name, data in files.items()},
                             mounts=[dict(source="payload/android", target="/system/android"),
                                     dict(source="payload/runtime/appspawn-x", target="/system/bin/appspawn-x")])
        write_json(self.package / "package.json", self.manifest)
        load = 'void* handle = dlopen_ns(app, "libexample.so", RTLD_NOW); if (!handle) { return 1; }'
        host = 'int create() { dlns_create2(app, paths, 0); ' + ("" if bad_namespace else load)
        host += 'dlopen_ns(app, "libexample.so", RTLD_NOW | RTLD_NOLOAD); }'
        if unknown:
            host += 'int other() { dlopen(dynamic_name, RTLD_NOLOAD); }'
        order = "cache(env); register_need(env);" if bad_jni else "register_need(env); cache(env);"
        runtime = '''
JNINativeMethod methods[] = {{"ping", "()V", (void*)native_ping}};
void cache(JNIEnv* env) {
    jclass klass = env->FindClass("Cache");
    auto field = env->GetFieldID(klass, "field", "I");
}
void register_need(JNIEnv* env) {
    jclass klass = env->FindClass("Need");
    env->RegisterNatives(klass, methods, 1);
}
void start(JNIEnv* env) { ''' + order + " }\n"
        (self.inputs_dir / "host.c").write_text(host)
        (self.inputs_dir / "runtime.cpp").write_text(runtime)
        classes = {"Cache": {"super": None, "methods": [
            {"name": "<clinit>", "descriptor": "()V", "native": False,
             "instructions": [{"offset": 0, "opcode": "invoke-static", "output": "LNeed;->ping()V"}]}]},
            "Need": {"super": None, "methods": [
                {"name": "ping", "descriptor": "()V", "native": True, "instructions": []}]}}
        write_json(self.inputs_dir / "dex.json", {"classes": classes, "jar_sha256": self.manifest["files"]["payload/android/framework/framework.jar"]})
        self.scan = dict(schema_version=1, sources={name: self.ref(name) for name in ("host.c", "runtime.cpp")},
                         dex=self.ref("dex.json"), profiles=[
            dict(name="host", rule="namespace", source="host.c", identity=self.identity("payload/runtime/appspawn-x")),
            dict(name="jni", rule="jni-order", source="runtime.cpp", sources=["runtime.cpp"],
                 entry_source="runtime.cpp", entry_function="start", identity=self.identity("payload/android/lib64/libruntime.so"))])
        write_json(self.inputs_dir / "scan.json", self.scan)
        write_json(self.inputs_dir / "domains.json", dict(schema_version=1, config_sources=[self.ref("host.c")], domains=[domain()]))
        self.inputs = dict(schema_version=1, package_manifest_sha256=sha256(self.package / "package.json"),
                           initialization=dict(manifest=self.ref("scan.json"), dex_artifact=self.artifact("payload/android/framework/framework.jar")),
                           namespaces=dict(manifest=self.ref("domains.json"), owner_artifact=self.artifact("payload/runtime/appspawn-x")))
        self.inputs_path = self.inputs_dir / "native-gates.json"
        self.exceptions = root / "exceptions.json"
        self.save()
        write_json(self.exceptions, EMPTY)

    def ref(self, name):
        return dict(path=name, sha256=sha256(self.inputs_dir / name))

    def artifact(self, name):
        return dict(path=name, sha256=self.manifest["files"][name])

    def identity(self, name):
        return dict(manifest_sha256=sha256(self.package / "package.json"), artifact=name,
                    artifact_sha256=self.manifest["files"][name])

    def save(self):
        write_json(self.inputs_path, self.inputs)

    def run(self, gate="N1", readelf="llvm-readelf"):
        return check_package(self.package, self.inputs_path, gate, self.exceptions, readelf)


def domain(**changes):
    result = dict(name="flutter", library_dirs=["/system/android/lib64/westlake_flutter"],
                  search_paths=["/system/android/lib64/westlake_flutter"],
                  permitted_paths=["/system/android/lib64/westlake_flutter"], unresolved_paths=[])
    result.update(changes)
    return result


class FixtureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)


class InitializationTests(FixtureTests):
    def test_real_rules_reject_both_known_wall_families(self):
        fixture = Fixture(self.root, bad_namespace=True, bad_jni=True)
        report = fixture.run()
        self.assertEqual(report["exit_code"], 1, report)
        findings = report["gates"]["N1"]["findings"]
        self.assertEqual({row["detail"]["family"] for row in findings},
                         {"noload-before-namespace-mapping", "jni-cache-before-native-registration"})
        completed = subprocess.run([sys.executable, str(ROOT / "scripts/lab/native_predeploy.py"),
                                    "--package", str(fixture.package), "--inputs", str(fixture.inputs_path),
                                    "--gate", "N1", "--exceptions", str(fixture.exceptions)], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(json.loads(completed.stdout)["status"], "REJECT")

    def test_corrected_order_passes_and_cli_is_json(self):
        fixture = Fixture(self.root)
        report = fixture.run()
        self.assertEqual(report["exit_code"], 0, report)
        self.assertEqual(report["gates"]["N1"]["findings"], [])
        completed = subprocess.run([sys.executable, str(ROOT / "scripts/lab/native_predeploy.py"),
                                    "--package", str(fixture.package), "--inputs", str(fixture.inputs_path),
                                    "--gate", "N1", "--exceptions", str(fixture.exceptions)], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["status"], "PASS")

    def test_unknown_is_not_a_pass(self):
        report = Fixture(self.root, unknown=True).run()
        self.assertEqual(report["exit_code"], 1)
        self.assertEqual(report["gates"]["N1"]["findings"][0]["kind"], "unknown")


class IdentityTests(FixtureTests):
    def test_empty_namespace_and_mismatched_dex_provenance_reject(self):
        for kind in ("empty-source", "dex-provenance"):
            with self.subTest(kind=kind):
                fixture = Fixture(self.root / kind)
                if kind == "empty-source":
                    (fixture.inputs_dir / "host.c").write_text(" ")
                    fixture.scan["sources"]["host.c"] = fixture.ref("host.c")
                else:
                    dex = read_json(fixture.inputs_dir / "dex.json")
                    dex["jar_sha256"] = "0" * 64
                    write_json(fixture.inputs_dir / "dex.json", dex)
                    fixture.scan["dex"] = fixture.ref("dex.json")
                write_json(fixture.inputs_dir / "scan.json", fixture.scan)
                fixture.inputs["initialization"]["manifest"] = fixture.ref("scan.json")
                fixture.save()
                self.assertEqual(fixture.run()["exit_code"], 3)

    def test_artifact_source_dex_and_package_drift_reject(self):
        mutations = ("artifact", "source", "dex", "manifest", "profile-identity", "dex-identity", "coverage")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                fixture = Fixture(self.root / mutation)
                if mutation == "artifact":
                    (fixture.package / "payload/runtime/appspawn-x").write_bytes(b"changed")
                elif mutation in {"source", "dex"}:
                    path = fixture.inputs_dir / ("host.c" if mutation == "source" else "dex.json")
                    path.write_text(path.read_text() + " ")
                elif mutation == "manifest":
                    (fixture.package / "package.json").write_text((fixture.package / "package.json").read_text() + " ")
                elif mutation == "dex-identity":
                    fixture.inputs["initialization"]["dex_artifact"]["sha256"] = "0" * 64
                    fixture.save()
                else:
                    if mutation == "coverage":
                        fixture.scan["profiles"].pop()
                    else:
                        fixture.scan["profiles"][0]["identity"]["manifest_sha256"] = "0" * 64
                    write_json(fixture.inputs_dir / "scan.json", fixture.scan)
                    fixture.inputs["initialization"]["manifest"] = fixture.ref("scan.json")
                    fixture.save()
                self.assertEqual(fixture.run()["exit_code"], 3)

    def test_path_escape_and_symlink_are_not_inputs(self):
        fixture = Fixture(self.root)
        fixture.inputs["initialization"]["manifest"]["path"] = "../inputs/scan.json"
        fixture.save()
        self.assertEqual(fixture.run()["exit_code"], 3)
        member = fixture.package / "payload/runtime/appspawn-x"
        original = member.read_bytes()
        member.unlink()
        outside = self.root / "outside"
        outside.write_bytes(original)
        member.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "symlink|escapes"):
            Package(fixture.package)


class ExceptionTests(unittest.TestCase):
    def approve(self, finding):
        initial = apply_exceptions("N1", [finding], "a" * 64, "b" * 64, EMPTY)
        return dict(gate="N1", issue_id=initial["findings"][0]["issue_id"],
                    package_manifest_sha256="a" * 64, inputs_sha256="b" * 64,
                    reason="fixture-only waiver", evidence=["evidence/fixture.json"],
                    removal_condition="review a complete source closure", approved_by="unit-test-only", approved_at="2026-10-01")

    def test_exact_exception_preserves_failure_and_new_wall_rejects(self):
        finding = dict(kind="unknown", detail="indirect call")
        entry = self.approve(finding)
        registry = dict(schema_version=1, exceptions=[entry])
        result = apply_exceptions("N1", [finding, dict(kind="new-wall")], "a" * 64, "b" * 64, registry)
        self.assertEqual((result["excepted"], result["rejected"]), (1, 1))
        changed = apply_exceptions("N1", [finding], "c" * 64, "b" * 64, registry)
        self.assertEqual(changed["rejected"], 1)

    def test_stale_and_incomplete_approval(self):
        entry = self.approve(dict(kind="unknown"))
        registry = dict(schema_version=1, exceptions=[entry])
        self.assertEqual(apply_exceptions("N1", [], "a" * 64, "b" * 64, registry)["stale"], [entry["issue_id"]])
        for field in ("reason", "approved_by", "evidence", "removal_condition"):
            invalid = copy.deepcopy(registry)
            del invalid["exceptions"][0][field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                apply_exceptions("N1", [], "a" * 64, "b" * 64, invalid)


class NeededTests(FixtureTests):
    def graph(self, graph, domains=None):
        virtual = {name: dict(sha256=digest_bytes(name.encode()), package_path=name,
                              metadata=dict(needed=needed, soname=name.rsplit("/", 1)[-1], rpath=[], runpath=[]))
                   for name, needed in graph.items()}
        selected = list(domains or [domain()])
        owned = {directory for item in selected for directory in item["library_dirs"]}
        for directory in sorted({name.rsplit("/", 1)[0] for name in graph} - owned):
            selected.append(domain(name="owner:" + directory, library_dirs=[directory],
                                   search_paths=[directory], permitted_paths=[directory]))
        return scan_domains(virtual, selected, lambda record: record["metadata"])

    def test_transitive_dependency_never_uses_global_or_inherit(self):
        prefix = "/system/android/lib64/westlake_flutter/"
        graph = {prefix + "libandroid.so": ["libmiddle.so"], prefix + "libmiddle.so": ["libruntime.so"],
                 "/system/android/lib64/libruntime.so": []}
        findings, report = self.graph(graph, [domain(inherit=["default"])])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["needed"], "libruntime.so")
        self.assertFalse(report["inherit_used"])
        self.assertEqual(findings[0]["outside_domain_candidates"], ["/system/android/lib64/libruntime.so"])
        graph[prefix + "libruntime.so"] = ["libandroid.so"]
        findings, report = self.graph(graph)
        self.assertEqual(findings, [])
        self.assertEqual(len(report["libraries"]), 4)

    def test_search_order_and_permitted_boundaries(self):
        prefix = "/system/android/lib64/westlake_flutter/"
        graph = {prefix + "libandroid.so": ["libruntime.so"], "/extra/libruntime.so": [],
                 "/extra-neighbor/libruntime.so": []}
        config = domain(search_paths=[prefix.rstrip("/"), "/extra-neighbor", "/extra"],
                        permitted_paths=[prefix.rstrip("/"), "/extra"])
        findings, report = self.graph(graph, [config])
        self.assertEqual(findings, [])
        self.assertEqual(report["edges"][0]["resolved"], "/extra/libruntime.so")
        config["search_paths"] = [prefix.rstrip("/")]
        self.assertEqual(self.graph(graph, [config])[0][0]["kind"], "missing-dt-needed")

    def test_real_readelf_and_cli_on_constructed_elf(self):
        executable = shutil.which("llvm-readelf") or shutil.which("readelf")
        self.assertIsNotNone(executable, "ELF reader is a required gate-test tool")
        fixture = Fixture(self.root)
        report = fixture.run("all", executable)
        self.assertEqual(report["exit_code"], 1, report)
        self.assertEqual({row["kind"] for row in report["gates"]["N2"]["findings"]}, {"uncovered-library-directory"})
        namespaces = read_json(fixture.inputs_dir / "domains.json")
        namespaces["domains"].append(domain(name="default", library_dirs=["/system/android/lib64"],
                                            search_paths=["/system/android/lib64"], permitted_paths=["/system/android/lib64"]))
        write_json(fixture.inputs_dir / "domains.json", namespaces)
        fixture.inputs["namespaces"]["manifest"] = fixture.ref("domains.json")
        fixture.save()
        self.assertEqual(fixture.run("all", executable)["exit_code"], 0)
        self.assertEqual(report["gates"]["N2"]["details"]["libraries"][0]["soname"], "libandroid.so")
        completed = subprocess.run([sys.executable, str(ROOT / "scripts/lab/native_predeploy.py"),
                                    "--package", str(fixture.package), "--inputs", str(fixture.inputs_path),
                                    "--readelf", executable, "--exceptions", str(fixture.exceptions)], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)

    def test_mount_override_uses_final_payload_not_old_hash(self):
        fixture = Fixture(self.root)
        replacement = fixture.package / "payload/override.so"
        replacement.write_bytes(elf_bytes(["missing.so"]))
        fixture.manifest["files"]["payload/override.so"] = sha256(replacement)
        fixture.manifest["mounts"].append(dict(source="payload/override.so", target="/system/android/lib64/westlake_flutter/libandroid.so"))
        write_json(fixture.package / "package.json", fixture.manifest)
        view = Package(fixture.package).virtual_files()
        self.assertEqual(view["/system/android/lib64/westlake_flutter/libandroid.so"]["sha256"], sha256(replacement))


class FailClosedTests(FixtureTests):
    def test_missing_domain_unresolved_path_and_rpath_reject(self):
        prefix = "/system/android/lib64/westlake_flutter/"
        metadata = dict(needed=[], soname="libandroid.so", rpath=[], runpath=["$ORIGIN"])
        virtual = {prefix + "libandroid.so": dict(sha256="a" * 64),
                   "/system/android/lib64/westlake_new/libnew.so": dict(sha256="b" * 64)}
        findings, _ = scan_domains(virtual, [domain(unresolved_paths=["domain->app_paths"])], lambda record: metadata)
        self.assertEqual({row["kind"] for row in findings},
                         {"unknown-effective-path", "unsupported-elf-search-path", "uncovered-library-directory"})
        for invalid in ([], [domain(search_paths=[])], [domain(permitted_paths=["/safe/../escape"])]):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                scan_domains(virtual, invalid, lambda record: metadata)

    def test_reader_error_wrong_architecture_and_malformed_output(self):
        fixture = Fixture(self.root)
        self.assertEqual(fixture.run("N2", "/missing/readelf")["exit_code"], 3)
        record = dict(path=fixture.package / "payload/android/lib64/westlake_flutter/libandroid.so",
                      sha256="a" * 64, package_path="fixture.so")
        raw = bytearray(record["path"].read_bytes())
        raw[18:20] = (62).to_bytes(2, "little")
        record["path"].write_bytes(raw)
        record["sha256"] = sha256(record["path"])
        with self.assertRaisesRegex(ValueError, "AArch64"):
            ElfReader("llvm-readelf")(record)
        for text in ("", "No dynamic section", "Dynamic section at offset 0 contains 1 entries:\n (NEEDED) invalid"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_dynamic(text)

    def test_duplicate_json_and_missing_approval_fail_closed(self):
        fixture = Fixture(self.root)
        fixture.inputs_path.write_text('{"schema_version":1,"schema_version":1}')
        self.assertEqual(fixture.run()["exit_code"], 3)

    def test_directory_mount_cannot_hide_unsealed_library(self):
        fixture = Fixture(self.root)
        (fixture.package / "payload/android/lib64/surprise.so").write_bytes(elf_bytes())
        self.assertEqual(fixture.run("N2")["exit_code"], 3)

    def test_invalid_schema_type_and_non_native_binding_reject(self):
        fixture = Fixture(self.root)
        fixture.inputs["initialization"] = []
        fixture.save()
        self.assertEqual(fixture.run()["exit_code"], 3)
        package = Package(fixture.package)
        with self.assertRaisesRegex(ValueError, "AArch64"):
            package.native_artifact(fixture.artifact("payload/android/framework/framework.jar"))


class ReplayTests(unittest.TestCase):
    def test_n4_bad_order_has_a_real_blocker_and_order_fix_keeps_unknowns(self):
        bad = read_json(REPLAY / "n4-gate.json")
        current = read_json(REPLAY / "current-gate.json")
        self.assertEqual(bad["exit_code"], 1)
        self.assertEqual(current["exit_code"], 1)
        bad_findings = bad["gates"]["N1"]["findings"]
        walls = [row for row in bad_findings if row["kind"] == "findings"]
        self.assertEqual(len(walls), 1)
        self.assertEqual(walls[0]["detail"]["family"], "jni-cache-before-native-registration")
        self.assertFalse(any(row["kind"] == "findings" for row in current["gates"]["N1"]["findings"]))
        self.assertGreater(current["gates"]["N1"]["rejected"], 0)

    def test_current_package_flutter_edge(self):
        replay = read_json(REPLAY / "needed-replay.json")
        package_path = REPLAY / "candidate-package.json"
        self.assertEqual(sha256(package_path), replay["package_manifest_sha256"])
        package = read_json(package_path)
        for record in replay["virtual_files"].values():
            self.assertEqual(package["files"][record["package_path"]], record["sha256"])
        metadata = {}
        for entry in replay["readelf_evidence"]:
            path = REPLAY / entry["path"]
            self.assertEqual(sha256(path), entry["sha256"])
            metadata[entry["artifact_sha256"]] = parse_dynamic(path.read_text())
        findings, report = scan_domains(replay["virtual_files"], replay["domains"], lambda record: metadata[record["sha256"]])
        selected = [row for row in findings if row.get("library", "").endswith("/westlake_flutter/libandroid.so")
                    and row.get("needed") == "liboh_android_runtime.so"]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["kind"], "missing-dt-needed")
        self.assertIn("/system/android/lib64/liboh_android_runtime.so", selected[0]["outside_domain_candidates"])
        self.assertFalse(report["inherit_used"])
        self.assertEqual(findings, replay["findings"])
        for entry in replay["config_sources"]:
            self.assertEqual(sha256(REPLAY / entry["path"]), entry["sha256"])


if __name__ == "__main__":
    unittest.main()
