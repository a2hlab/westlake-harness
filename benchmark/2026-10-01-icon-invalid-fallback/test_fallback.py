import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import unittest
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE_SHA = '1ffed6bcd4941767d048988ee230577d8134fcd256055705ce104ca6a51b2730'
TARGET = Path('bms/src/adapter/framework/package-manager/jni/apk_installer.cpp')


def function(source, declaration):
    start = source.index(declaration)
    body = source.index('{', start)
    depth = 0
    for position in range(body, len(source)):
        if source[position] == '{':
            depth += 1
        elif source[position] == '}':
            depth -= 1
            if depth == 0:
                return source[start:position + 1]
    raise ValueError('Unclosed production function')


HOST = r'''
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cerrno>
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include <vector>
#include <unistd.h>
std::vector<std::string> logs;
template<typename... Args> void Log(std::string format, Args... args) {
    size_t position;
    while ((position = format.find("%{public}")) != std::string::npos) format.replace(position, 9, "%");
    char buffer[2048];
    if constexpr (sizeof...(Args) == 0) {
        std::snprintf(buffer, sizeof(buffer), "%s", format.c_str());
    } else {
        std::snprintf(buffer, sizeof(buffer), format.c_str(), args...);
    }
    logs.emplace_back(buffer);
}
#define LOGI(...) Log(__VA_ARGS__)
#define LOGW(...) Log(__VA_ARGS__)
#define LOGE(...) Log(__VA_ARGS__)
bool parseOk = true, resolveOk = true, selectedReadable = true, legacyOk = false, placeholderOk = true, hasPhysical = false;
uint32_t declaredIcon = 0x7f090000;
int legacyCalls = 0, placeholderCalls = 0;
std::string selectedName = "res/selected.webp";
std::vector<uint8_t> selectedBytes, outputBytes;
const unsigned char ohos_adapter_template_resources_hap[] = {0};
const unsigned int ohos_adapter_template_resources_hap_len = 1;
namespace oh_adapter {
struct ApkManifestParser {
    struct ManifestData { uint32_t appIcon = 0; };
    static bool Parse(const std::string&, ManifestData& data) { data.appIcon = declaredIcon; return parseOk; }
};
bool ResolveResourceIdToFile(const std::string&, uint32_t, std::string& result) { result = selectedName; return resolveOk; }
class ApkInstaller { public: static bool ExtractAndPackResourceHap(const std::string&, const std::string&); };
}
bool ReadZipEntry(const std::string& archive, const std::string&, std::vector<uint8_t>& result) {
    if (archive.find(".iconprobe.tmp") != std::string::npos) {
        ++placeholderCalls;
        result = {0x89,'P','N','G',13,10,26,10,1};
        return placeholderOk;
    }
    result = selectedBytes;
    return selectedReadable;
}
bool ComposeAdaptiveIcon(const std::string&, const std::string&, const std::vector<uint8_t>&, std::vector<uint8_t>&) { return false; }
bool ZipHasAnyIconEntry(const std::string&) { return hasPhysical; }
bool ReadApkLauncherIcon(const std::string&, std::vector<uint8_t>& result) {
    ++legacyCalls;
    result = {0x89,'P','N','G',13,10,26,10,2};
    return legacyOk;
}
using oh_adapter::ApkInstaller;
'''


MAIN = r'''
int main(int argc, char** argv) {
    if (argc < 3) return 2;
    std::ifstream input(argv[2], std::ios::binary);
    selectedBytes.assign(std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>());
    if (std::string(argv[1]) == "header") {
        const char* failure = SelectedRasterHeaderFailure(selectedBytes);
        std::cout << (failure ? failure : "OK") << '\n';
        return 0;
    }
    if (argc != 4) return 2;
    std::string scenario = argv[1];
    if (scenario == "invalid") legacyOk = true;
    if (scenario == "unreadable") { selectedReadable = false; legacyOk = true; }
    if (scenario == "manifest-fail") parseOk = false;
    if (scenario == "no-icon") declaredIcon = 0;
    if (scenario == "xml") { selectedName = "res/icon.xml"; legacyOk = true; }
    if (scenario == "xml-only") selectedName = "res/icon.xml";
    if (scenario == "unreadable-no-legacy") selectedReadable = false;
    if (scenario == "placeholder-fail") placeholderOk = false;
    if (scenario == "unresolved-present") { resolveOk = false; hasPhysical = true; }
    bool success = ApkInstaller::ExtractAndPackResourceHap("app.apk", argv[3]);
    std::cout << "success=" << success << "\nlegacy=" << legacyCalls << "\nplaceholder=" << placeholderCalls
              << "\nsame=" << (outputBytes == selectedBytes) << '\n';
    for (const auto& line : logs) std::cout << "log=" << line << '\n';
    return 0;
}
'''


def build_probe(directory):
    base = (HERE / 'base-apk_installer.cpp').read_bytes()
    if hashlib.sha256(base).hexdigest() != BASE_SHA:
        raise ValueError('Installer base SHA drift')
    target = directory / TARGET
    target.parent.mkdir(parents=True)
    target.write_bytes(base)
    subprocess.run(['/usr/bin/patch', '-p1', '--batch', '--fuzz=0', '-i', str(HERE / 'apk_installer.cpp.patch')], cwd=directory, check=True, capture_output=True)
    proposed = target.read_text()
    if proposed != (HERE / 'proposed-apk_installer.cpp').read_text():
        raise ValueError('Patch/proposed source mismatch')
    pieces = [function(proposed, 'uint32_t ReadLe32('), function(proposed, 'const char* SelectedRasterHeaderFailure('),
              function(proposed, 'bool ReadIconByManifest(')]
    pieces.append(proposed[proposed.index('enum class IconlessApkClass'):proposed.index('// Physical presence probe')])
    pieces.extend([function(proposed, 'IconlessApkClass ClassifyIconlessApk('), function(proposed, 'bool ReadTemplatePlaceholderIcon(')])
    start = proposed.index('bool ApkInstaller::ExtractAndPackResourceHap(')
    stop = proposed.index('    NormalizeLauncherIconPng(apkIconBytes);', start)
    pieces.append(proposed[start:stop] + '    outputBytes = apkIconBytes;\n    return true;\n}\n')
    translation = directory / 'probe.cpp'
    translation.write_text(HOST + '\n'.join(pieces) + MAIN)
    executable = directory / 'probe'
    subprocess.run(['/usr/bin/clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror', str(translation), '-o', str(executable)], check=True, capture_output=True)
    return executable


def webp(kind=b'VP8X', payload=b'\0' * 10):
    body = b'WEBP' + kind + struct.pack('<I', len(payload)) + payload + (b'\0' if len(payload) % 2 else b'')
    return b'RIFF' + struct.pack('<I', len(body)) + body


class ProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='icon-fallback-host-')
        cls.directory = Path(cls.temporary.name)
        cls.probe = build_probe(cls.directory)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def execute(self, data, scenario='header'):
        source = self.directory / 'image.bin'
        source.write_bytes(data)
        arguments = [str(self.probe), scenario, str(source)]
        if scenario != 'header':
            arguments.append(str(self.directory / 'resources.hap'))
        return subprocess.check_output(arguments, text=True)


class HeaderTests(ProbeTests):
    def test_healthy_PNG_header_is_unchanged(self):
        self.assertEqual(self.execute(b'\x89PNG\r\n\x1a\n'), 'OK\n')

    def test_three_WebP_header_variants_are_accepted(self):
        for data in [webp(), webp(b'VP8L', b'\x2f\0\0\0\0'), webp(b'VP8 ', b'\0\0\0\x9d\x01\x2a\0\0\0\0')]:
            with self.subTest(data=data):
                self.assertEqual(self.execute(data), 'OK\n')

    def test_JPEG_initial_segment_and_end_marker(self):
        self.assertEqual(self.execute(b'\xff\xd8\xff\xe0\0\4ok\xff\xd9'), 'OK\n')
        self.assertEqual(self.execute(b'\xff\xd8\xff\xe0\0\4ok\xff\xd9trailer'), 'OK\n')
        self.assertEqual(self.execute(b'\xff\xd8\xff\xff\xe0\0\4ok\xff\xd9'), 'OK\n')
        self.assertIn('truncated-jpeg', self.execute(b'\xff\xd8\xff\xe0\0\4ok'))
        self.assertIn('invalid-jpeg-first-segment', self.execute(b'\xff\xd8\xff\xe0\xff\xffok\xff\xd9'))

    def test_UTF8_expanded_header_and_RIFF_size_are_rejected(self):
        data = webp(payload=b'\xff' * 10).decode('latin1').encode('utf8')
        self.assertIn('invalid-webp', self.execute(data))
        changed = bytearray(webp()); changed[4:8] = struct.pack('<I', 0xffffffff)
        self.assertIn('invalid-webp-riff-size', self.execute(changed))

    def test_truncated_and_unknown_chunks_are_rejected(self):
        for data in [webp(b'NOPE', b'1234'), webp(b'VP8L', b'\x00' * 5), webp(b'VP8 ', b'\0' * 10), webp(b'VP8X', b'\0' * 9)]:
            self.assertNotEqual(self.execute(data), 'OK\n')
        changed = bytearray(webp()); changed[16:20] = struct.pack('<I', 0xffffffff)
        self.assertIn('truncated-webp', self.execute(changed))

    def test_every_truncation_is_bounded(self):
        data = webp()
        for length in range(len(data)):
            self.assertNotEqual(self.execute(data[:length]), 'OK\n')
        self.assertIn('unsupported-or-invalid', self.execute(b'not an image'))


class RoutingTests(ProbeTests):
    def test_invalid_selected_member_bypasses_legacy_and_logs_reason(self):
        result = self.execute(b'RIFFbad image', 'invalid')
        for expected in ['success=1', 'legacy=0', 'placeholder=1', 'same=0', 'file=res/selected.webp reason=invalid-webp-header', 'ICONLESS_APK_TEMPLATE_PLACEHOLDER', 'class=DECLARED_INVALID_RASTER']:
            self.assertIn(expected, result)
        self.assertFalse((self.directory / 'resources.hap.iconprobe.tmp').exists())

    def test_healthy_selected_bytes_are_not_replaced(self):
        for data in [b'\x89PNG\r\n\x1a\n', webp(), b'\xff\xd8\xff\xe0\0\4ok\xff\xd9']:
            result = self.execute(data, 'healthy')
            for expected in ['success=1', 'legacy=0', 'placeholder=0', 'same=1']:
                self.assertIn(expected, result)

    def test_unreadable_member_and_XML_keep_legacy_fallback(self):
        for scenario in ['unreadable', 'xml']:
            result = self.execute(b'not a readable raster', scenario)
            self.assertIn('success=1', result)
            self.assertIn('legacy=1', result)
            self.assertIn('placeholder=0', result)
            self.assertNotIn('invalid selected raster', result)

    def test_manifest_failure_and_unresolved_physical_entry_fail_closed(self):
        for scenario in ['manifest-fail', 'unresolved-present', 'unreadable-no-legacy']:
            result = self.execute(b'not an image', scenario)
            self.assertIn('success=0', result)
            self.assertIn('placeholder=0', result)

    def test_existing_iconless_template_branch_is_preserved(self):
        result = self.execute(b'', 'no-icon')
        self.assertIn('success=1', result)
        self.assertIn('class=NOT_DECLARED', result)
        self.assertIn('placeholder=1', result)

    def test_existing_B7_XML_only_template_branch_is_preserved(self):
        result = self.execute(b'compiled XML', 'xml-only')
        self.assertIn('success=1', result)
        self.assertIn('class=DECLARED_XML_ONLY', result)
        self.assertIn('placeholder=1', result)

    def test_unreadable_placeholder_remains_fatal_and_cleans_temp(self):
        result = self.execute(b'RIFFbad image', 'placeholder-fail')
        self.assertIn('success=0', result)
        self.assertIn('placeholder=1', result)
        self.assertFalse((self.directory / 'resources.hap.iconprobe.tmp').exists())


class ReplayTests(ProbeTests):
    def test_patch_changed_only_the_requested_source_and_applies_exactly(self):
        patch = (HERE / 'apk_installer.cpp.patch').read_text()
        self.assertEqual(re.findall(r'^\+\+\+ (.+)$', patch, re.M), ['b/' + str(TARGET)])
        self.assertEqual(hashlib.sha256((HERE / 'base-apk_installer.cpp').read_bytes()).hexdigest(), BASE_SHA)

    def test_real_25_WebP_family_members_preserve_24_valid_headers(self):
        import os
        workspaces = Path(os.environ.get('WORKSPACES', ROOT.parent))
        result = json.loads((ROOT / 'benchmark/2026-10-01-icon-format-scan/results.json').read_text())
        import importlib.util
        spec = importlib.util.spec_from_file_location('fallback_icon_scan', ROOT / 'benchmark/2026-10-01-icon-format-scan/scan.py')
        scanner = importlib.util.module_from_spec(spec); spec.loader.exec_module(scanner)
        paths = {row['key']: row['path'] for row in scanner.cohort.inputs(workspaces)}
        accepted = []
        rejected = []
        for row in result['rows']:
            if row['selected_format'] != 'WebP':
                continue
            apk = Path(paths[row['key']])
            self.assertEqual(hashlib.sha256(apk.read_bytes()).hexdigest(), row['apk_sha256'])
            with zipfile.ZipFile(apk) as archive:
                data = archive.read(row['selected_file'])
            self.assertEqual(hashlib.sha256(data).hexdigest(), row['selected_sha256'])
            answer = self.execute(data)
            (accepted if answer == 'OK\n' else rejected).append(row['key'])
        self.assertEqual(len(accepted), 24)
        self.assertEqual(rejected, ['cv2-com-frequent-habits'])


if __name__ == '__main__':
    unittest.main()
