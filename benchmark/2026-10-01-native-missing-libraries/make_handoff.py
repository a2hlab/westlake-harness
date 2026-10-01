"""Create source-bound patches in memory; do not build or deploy a generation."""

import difflib
import hashlib
import json
from pathlib import Path
import os

HERE = Path(__file__).resolve().parent
POLICY = 'bms/src/adapter/framework/native-loader-oh/'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('Source anchor is absent or ambiguous: ' + before[:70])
    return text.replace(before, after)


def proposal(policy_json, policy_header, system_loader, host, policy_checker=None):
    manifest = json.loads(policy_json)
    if any(item['soname'] == 'libmedia_jni.so' for item in manifest['system_libraries']):
        raise ValueError('media_jni already mapped; rebase rather than duplicate')
    manifest['system_libraries'].append(dict(soname='libmedia_jni.so', path='/system/android/lib64/liboh_android_runtime.so'))
    header = replace_once(policy_header, 'std::array<SystemLibrary, 4>', 'std::array<SystemLibrary, 5>')
    header = replace_once(header, '    {"liboh_adapter_bridge.so", "/system/android/lib64/liboh_adapter_bridge.so"},',
        '    {"liboh_adapter_bridge.so", "/system/android/lib64/liboh_adapter_bridge.so"},\n'
        '    {"libmedia_jni.so", "/system/android/lib64/liboh_android_runtime.so"},')
    loader = replace_once(system_loader, '#include <stdlib.h>', '#include <stdlib.h>\n#include <stdio.h>')
    loader = replace_once(loader, '  void* handle = ops_->OpenExact(resolved.c_str(), RTLD_NOW | RTLD_LOCAL);',
        '  const bool media_owner = library->soname == "libmedia_jni.so";\n'
        '  const int flags = RTLD_NOW | RTLD_LOCAL | (media_owner ? RTLD_NOLOAD : 0);\n'
        '  void* handle = ops_->OpenExact(resolved.c_str(), flags);')
    loader = replace_once(loader, '  return handle;\n}\n\nbool SystemLoader::Owns',
        '  if (media_owner) {\n'
        '    fprintf(stderr, "[U9-MEDIA-OWNER] request=libmedia_jni.so owner=%s handle=%p resident-only=1\\n",\n'
        '            resolved.c_str(), handle);\n'
        '  }\n'
        '  return handle;\n}\n\nbool SystemLoader::Owns')
    host_after = replace_once(host, '#include "westlake_stock_host_services.h"',
        '#include "westlake_stock_host_services.h"\n#include "missing-library-route.h"')
    host_after = replace_once(host_after, '    dlns_init(app_namespace, app_name);',
        '    const char *missing_original_search = app_search_paths;\n'
        '    char missing_search[4 * PATH_MAX], missing_permitted[5 * PATH_MAX];\n'
        '    const char *missing_root = MissingLibraryRoot(app_search_paths, app_permitted_paths);\n'
        '    if (missing_root != NULL) {\n'
        '        int search_length = snprintf(missing_search, sizeof(missing_search), "%s:%s", missing_root, app_search_paths);\n'
        '        int permitted_length = snprintf(missing_permitted, sizeof(missing_permitted), "%s:%s", missing_root, app_permitted_paths);\n'
        '        if (search_length < 0 || permitted_length < 0 ||\n'
        '            search_length >= (int)sizeof(missing_search) || permitted_length >= (int)sizeof(missing_permitted))\n'
        '            return NamespaceResultFence(ENAMETOOLONG);\n'
        '        app_search_paths = missing_search;\n'
        '        app_permitted_paths = missing_permitted;\n'
        '    }\n'
        '    dlns_init(app_namespace, app_name);')
    host_after = replace_once(host_after,
        '    const bool native_private = wants_bridge &&\n'
        '        strncmp(app_search_paths, "/system/android/lib64/westlake_native:",',
        '    const bool native_private = wants_bridge &&\n'
        '        strncmp(missing_original_search, "/system/android/lib64/westlake_native:",')
    host_after = replace_once(host_after, '    return NamespaceResultFence(0);\n}\n\nstatic WLASC_NOINLINE void *StockOpenNamespace',
        '    result = MissingLibraryAudioOwner(app_namespace, app_search_paths, app_permitted_paths);\n'
        '    if (result != 0) return NamespaceResultFence(result);\n'
        '    if (missing_root != NULL) APPSPAWN_LOGI("[U9-LIB-ROUTE] ns=%{public}s root=%{public}s", app_name, missing_root);\n'
        '    return NamespaceResultFence(0);\n}\n\nstatic WLASC_NOINLINE void *StockOpenNamespace')
    sources = {
        POLICY + 'policy/native_bridge_policy.v1.json': (policy_json, json.dumps(manifest, indent=2) + '\n'),
        POLICY + 'include/nativeloader/native_bridge_policy.h': (policy_header, header),
        POLICY + 'src/system_loader.cpp': (system_loader, loader),
        'bms/src/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/src/westlake_stock_host_main.c': (host, host_after),
    }
    if policy_checker is not None:
        checker = replace_once(policy_checker,
            '    if item["path"] != f"/system/android/lib64/{item[\'soname\']}":',
            '    media_owner_alias = (item["soname"], item["path"]) == (\n'
            '        "libmedia_jni.so", "/system/android/lib64/liboh_android_runtime.so")\n'
            '    if not media_owner_alias and item["path"] != f"/system/android/lib64/{item[\'soname\']}":')
        sources[POLICY + 'tests/verify_bridge_policy.py'] = (policy_checker, checker)
    return sources


def patches(sources):
    return [dict(target=target, base_sha256=digest(before.encode()), proposed_sha256=digest(after.encode()),
        patch=''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                        fromfile='a/' + target, tofile='b/' + target)))
        for target, (before, after) in sources.items()]


def main():
    workspaces = Path(os.environ.get('WORKSPACES', HERE.parents[2]))
    master = workspaces / 'westlake-harness'
    loader_root = master / POLICY
    host_path = workspaces / 'westlake-generation-u8-j9-t7e/native/native-checks/n4-host.c'
    sources = proposal((loader_root / 'policy/native_bridge_policy.v1.json').read_text(),
        (loader_root / 'include/nativeloader/native_bridge_policy.h').read_text(),
        (loader_root / 'src/system_loader.cpp').read_text(), host_path.read_text(),
        (loader_root / 'tests/verify_bridge_policy.py').read_text())
    print(json.dumps(dict(schema_version=1, status='offline-proposal-not-built', patches=patches(sources)), indent=2))


if __name__ == '__main__':
    main()
