import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from rules_native_initialization import Source, jni_order_walls, namespace_walls
from scan_native_initialization import scan


HERE = Path(__file__).resolve().parent
REPLAY = HERE / "native-initialization"


class NamespaceTests(unittest.TestCase):
    def test_generation_replay(self):
        profiles = {row["profile"]: row for row in scan(REPLAY / "manifest.json")["profiles"]}
        self.assertEqual(profiles["N2"]["findings"], [])
        findings = profiles["N3b"]["findings"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["library"], "/system/android/lib64/liboh_android_runtime.so")
        self.assertEqual(findings[0]["namespace"], "app_namespace")
        self.assertEqual(findings[0]["evidence"]["line"], 281)
        self.assertTrue(profiles["N2"]["unknown"])

    def detect(self, before="", after=""):
        return namespace_walls(Source("host.c", '''
int create() {
    dlns_create2(app, paths, LOCAL_NS_PREFERED);
''' + before + '''
    dlopen_ns(app, "libexample.so", RTLD_NOW | RTLD_NOLOAD);
''' + after + "\n}"))

    def test_prior_mapping_requires_matching_scope_and_guard(self):
        load = 'void* handle = dlopen_ns(app, "libexample.so", RTLD_NOW); if (!handle) { return 1; }'
        result = self.detect(load)
        self.assertFalse(result["findings"])
        self.assertEqual(len(result["checked"]), 1)
        for before in (load.replace("(app,", "(other,"), load.replace("libexample.so", "libother.so"),
                       "if (condition) { " + load + " }", load.split("if")[0],
                       load.replace("RTLD_NOW", "SOME_FLAGS"),
                       load + " dlclose(handle);", load + " dlns_create2(app, paths, 0);",
                       'dlns_inherit(app, owner, "libexample.so");',
                       "/* " + load + " */", 'const char* message = "RTLD_NOLOAD";'):
            with self.subTest(before=before):
                self.assertEqual(len(self.detect(before)["findings"]), 1)
        self.assertEqual(len(self.detect(after=load)["findings"]), 1)

    def test_unknown_or_no_noload_is_not_a_proven_wall(self):
        source = Source("host.c", '''
int create() {
  dlns_create2(app, paths, 0);
  dlopen_ns(app, "ok.so", RTLD_NOW);
  dlopen_ns(app, target, RTLD_NOW | RTLD_NOLOAD);
  dlopen("plugin.so", RTLD_NOLOAD);
  dlopen_ns(app, "log.so", trace("RTLD_NOLOAD"));
}
''')
        result = namespace_walls(source)
        self.assertFalse(result["findings"])
        self.assertEqual(len(result["unknown"]), 2)


class JniTests(unittest.TestCase):
    def test_generation_replay(self):
        profiles = {row["profile"]: row for row in scan(REPLAY / "manifest.json")["profiles"]}
        findings = profiles["N4"]["findings"]
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding["dependency"]["class_name"], "com/google/android/gles_jni/GLImpl")
        self.assertEqual(finding["dependency"]["method"], "_nativeClassInit")
        self.assertEqual(finding["cache"]["evidence"]["line"], 113)
        self.assertEqual(finding["cache"]["trace"][0]["line"], 666)
        self.assertEqual(finding["registration"]["trace"][0]["line"], 672)
        self.assertEqual(profiles["N4-order"]["findings"], [])
        self.assertTrue(any(row["dependency"]["class_name"].endswith("/GLImpl")
                            for row in profiles["N4-order"]["checked"]))

    def fixture(self, order="cache(env); register_need(env);", registered="Need", operation="GetFieldID"):
        classes = {
            "Cache": {"super": None, "methods": [
                {"name": "<clinit>", "descriptor": "()V", "native": False,
                 "instructions": [{"offset": 0, "opcode": "invoke-static", "output": "LNeed;->ping()V"}]}]},
            "Need": {"super": None, "methods": [
                {"name": "ping", "descriptor": "()V", "native": True, "instructions": []}]},
        }
        source = Source("runtime.cpp", '''
JNINativeMethod methods[] = {{"ping", "()V", (void*)native_ping}};
void cache(JNIEnv* env) {
  jclass klass = env->FindClass("Cache");
  auto cached = env->''' + operation + '''(klass, "field", "I");
}
void register_need(JNIEnv* env) {
  jclass klass = env->FindClass("''' + registered + '''");
  env->RegisterNatives(klass, methods, 1);
}
void start(JNIEnv* env) { ''' + order + " }")
        return {source.name: source}, classes

    def test_field_and_method_cache_calls(self):
        for operation in ("GetFieldID", "GetMethodID", "GetStaticFieldID", "GetStaticMethodID"):
            with self.subTest(operation=operation):
                sources, classes = self.fixture(operation=operation)
                result = jni_order_walls(sources, "runtime.cpp", "start", classes)
                self.assertEqual(len(result["findings"]), 1)
        sources, classes = self.fixture("register_need(env); cache(env);")
        self.assertFalse(jni_order_walls(sources, "runtime.cpp", "start", classes)["findings"])

    def test_unreachable_wrong_class_and_missing_dependency(self):
        sources, classes = self.fixture("register_need(env);")
        self.assertFalse(jni_order_walls(sources, "runtime.cpp", "start", classes)["findings"])
        sources, classes = self.fixture(registered="Other")
        result = jni_order_walls(sources, "runtime.cpp", "start", classes)
        self.assertFalse(result["findings"])
        self.assertTrue(result["unknown"])

    def test_wrong_native_method_table_is_not_registration(self):
        sources, classes = self.fixture("register_need(env); cache(env);")
        text = sources["runtime.cpp"].text.replace('"ping", "()V"', '"unrelated", "()V"')
        sources["runtime.cpp"] = Source("runtime.cpp", text)
        result = jni_order_walls(sources, "runtime.cpp", "start", classes)
        self.assertFalse(result["checked"])
        self.assertTrue(result["unknown"])
        sources, classes = self.fixture()
        del classes["Need"]
        result = jni_order_walls(sources, "runtime.cpp", "start", classes)
        self.assertFalse(result["findings"])
        self.assertTrue(result["unknown"])


class ProvenanceTests(unittest.TestCase):
    def test_frozen_replay_and_coordinates(self):
        result = scan(REPLAY / "manifest.json")
        self.assertEqual(result, json.loads((REPLAY / "results.json").read_text()))
        self.assertFalse(result["prospective"])
        self.assertFalse(result["device_access"])
        manifest = json.loads((REPLAY / "manifest.json").read_text())
        for entry in manifest["sources"].values():
            self.assertEqual(len(entry["source_sha256"]), 64)
            self.assertFalse(Path(entry["origin"]).is_absolute())
        self.assertEqual(manifest["sources"]["gl-register.cpp"]["first_line"], 9036)

    def test_tampered_or_missing_input_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "replay"
            shutil.copytree(REPLAY, target)
            source = target / "evidence/sources/n3b-host.c"
            source.write_text(source.read_text() + "\n")
            with self.assertRaisesRegex(ValueError, "SHA mismatch"):
                scan(target / "manifest.json")
            source.unlink()
            completed = subprocess.run([sys.executable, str(HERE / "scan_native_initialization.py"),
                                        "--manifest", str(target / "manifest.json")], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 3)
            self.assertEqual(json.loads(completed.stdout)["status"], "unknown-invalid-input")

    def test_missing_entry_and_malformed_source_refused(self):
        with self.assertRaisesRegex(ValueError, "entry function"):
            jni_order_walls({}, "absent.cpp", "start", {})
        with self.assertRaisesRegex(ValueError, "unbalanced"):
            Source("broken.cpp", "void start() {")


if __name__ == "__main__":
    unittest.main()
