#!/usr/bin/env python3
"""
apply_BUILD_gn.py — idempotent semantic patcher for libbms BUILD.gn.

Adds the Android APK adapter source files and their OpenSSL dependency to the
ohos_shared_library("libbms") target in:
    foundation/bundlemanager/bundle_framework/services/bundlemgr/BUILD.gn

Modifications are applied only if not already present, so the script is safe
to run repeatedly after `repo sync`.
"""

import argparse
import re
import sys
from pathlib import Path


def find_target_block(text: str, target_name: str = "libbms") -> tuple[int, int]:
    """Return (start, end) indices of the ohos_shared_library("libbms") { ... } block."""
    pattern = re.compile(r'ohos_shared_library\s*\(\s*"' + re.escape(target_name) + r'"\s*\)\s*\{')
    match = pattern.search(text)
    if not match:
        raise ValueError(f'ohos_shared_library("{target_name}") block not found')
    start = match.end() - 1  # position of the opening '{'
    depth = 0
    i = start
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1
        i += 1
    raise ValueError(f'unterminated ohos_shared_library("{target_name}") block')


def has_string_in_block(block: str, value: str) -> bool:
    """Check whether a double-quoted string literal exists in the block."""
    return f'"{value}"' in block


def patch_defines(block: str, define: str = "OH_ADAPTER_ANDROID") -> str:
    """Add a define to the first defines = [ ... ] list in the block if absent."""
    if has_string_in_block(block, define):
        return block
    # Insert after the first opening bracket of defines = [
    match = re.search(r'defines\s*=\s*\[', block)
    if not match:
        raise ValueError('defines = [ ... ] list not found in libbms block')
    insert_pos = match.end()
    return block[:insert_pos] + f'\n    "{define}",' + block[insert_pos:]


def remove_deprecated_sources(block: str, deprecated: list[str]) -> tuple[str, list[str]]:
    """Remove deprecated source entries that may have been added by earlier
    versions of this patcher. Returns (new_block, removed_list)."""
    removed: list[str] = []
    new_block = block
    for src in deprecated:
        # Match a line that contains exactly this quoted source string and a
        # trailing comma (with optional whitespace/comment). Keep the search
        # scoped to sources += [ ... ] blocks by only removing lines inside
        # bracketed list context.
        pattern = re.compile(r'^\s+"' + re.escape(src) + r'",\s*$', re.MULTILINE)
        if pattern.search(new_block):
            new_block = pattern.sub('', new_block)
            removed.append(src)
    # Collapse any double blank line introduced inside a sources += [ ... ] list.
    new_block = re.sub(r'(sources \+= \[)\n\n', r'\1\n', new_block)
    return new_block, removed


def patch_sources(block: str, sources: list[str]) -> str:
    """Add adapter sources via a new sources += [ ... ] entry if absent."""
    missing = [s for s in sources if not has_string_in_block(block, s)]
    if not missing:
        return block

    # Prefer inserting after the unconditional sources += bundle_install_sources line.
    anchor = "sources += bundle_install_sources"
    anchor_match = re.search(re.escape(anchor), block)
    if anchor_match:
        insert_pos = anchor_match.end()
        new_block = (
            block[:insert_pos]
            + "\n\n  # Android APK install adapter sources (gap 6)"
            + "\n  sources += ["
        )
        for src in sources:
            new_block += f'\n    "{src}",'
        new_block += "\n  ]"
        new_block += block[insert_pos:]
        return new_block

    # Fallback: insert just after the sources = bundle_mgr_source line.
    fallback = re.search(r'sources\s*=\s*bundle_mgr_source', block)
    if fallback:
        insert_pos = fallback.end()
        new_block = block[:insert_pos] + "\n\n  sources += ["
        for src in sources:
            new_block += f'\n    "{src}",'
        new_block += "\n  ]" + block[insert_pos:]
        return new_block

    raise ValueError('could not find a stable sources anchor in libbms block')


def patch_external_deps(block: str, dep: str = "openssl:libcrypto_shared") -> str:
    """Add an external dependency to the first external_deps = [ ... ] list if absent."""
    if has_string_in_block(block, dep):
        return block
    match = re.search(r'external_deps\s*=\s*\[', block)
    if not match:
        raise ValueError('external_deps = [ ... ] list not found in libbms block')
    insert_pos = match.end()
    return block[:insert_pos] + f'\n    "{dep}",' + block[insert_pos:]


def patch_build_gn(path: Path) -> tuple[bool, list[str]]:
    text = path.read_text(encoding="utf-8")
    start, end = find_target_block(text)
    original_block = text[start:end]
    block = original_block

    changes: list[str] = []

    if not has_string_in_block(block, "OH_ADAPTER_ANDROID"):
        block = patch_defines(block)
        changes.append('added define "OH_ADAPTER_ANDROID"')
    else:
        changes.append('define "OH_ADAPTER_ANDROID" already present')

    # adapter_apk_install_minimal.cpp is dead code: the real install path routes
    # through libapk_installer.so (oh_adapter_install_apk / oh_adapter_install_apk_with_manifest)
    # and ProcessApkInstall has no caller. Keep only the parser/verifier/mapper helpers
    # that are still used by the BMS install chain.
    deprecated_sources = [
        "src/adapter_apk_install_minimal.cpp",
    ]
    block, removed_sources = remove_deprecated_sources(block, deprecated_sources)
    if removed_sources:
        changes.append(f'removed deprecated sources: {", ".join(removed_sources)}')

    adapter_sources = [
        "src/apk_manifest_parser.cpp",
        "src/apk_signature_verifier.cpp",
        "src/permission_mapper.cpp",
    ]
    missing_sources = [s for s in adapter_sources if not has_string_in_block(block, s)]
    if missing_sources:
        block = patch_sources(block, adapter_sources)
        changes.append(f'added adapter sources: {", ".join(missing_sources)}')
    else:
        changes.append('adapter sources already present')

    if not has_string_in_block(block, "openssl:libcrypto_shared"):
        block = patch_external_deps(block)
        changes.append('added external dep "openssl:libcrypto_shared"')
    else:
        changes.append('external dep "openssl:libcrypto_shared" already present')

    if block == original_block:
        return False, changes

    new_text = text[:start] + block + text[end:]
    path.write_text(new_text, encoding="utf-8")
    return True, changes


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Patch libbms BUILD.gn to build the Android APK adapter sources."
    )
    parser.add_argument(
        "--bms-build-gn",
        required=True,
        help="Path to foundation/bundlemanager/bundle_framework/services/bundlemgr/BUILD.gn",
    )
    parser.add_argument(
        "--aosp-root",
        default=None,
        help="Kept for interface compatibility; no longer used.",
    )
    args = parser.parse_args()

    path = Path(args.bms_build_gn)
    if not path.is_file():
        print(f"ERROR: BUILD.gn not found: {path}", file=sys.stderr)
        return 1

    try:
        modified, changes = patch_build_gn(path)
    except Exception as e:
        print(f"ERROR: failed to patch {path}: {e}", file=sys.stderr)
        return 1

    status = "MODIFIED" if modified else "UNCHANGED"
    print(f"{status}: {path}")
    for line in changes:
        print(f"  - {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
