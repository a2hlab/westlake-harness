#!/usr/bin/env python3
"""P/N/F host contract for the strict adapter-bridge source closure."""

from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "inner" / "compile_oh_adapter_bridge_arm64.sh"

REQUIRED_TOKENS = (
    'PM_SOURCE_ROOT="${PACKAGE_MANAGER_SOURCE_ROOT:-$ADAPTER_ROOT/framework/package-manager}"',
    'OH_APPKIT_APP_ROOT="$OH/foundation/ability/ability_runtime/interfaces/kits/native/appkit/app"',
    'OH_ABILITY_STAGE_ROOT="$OH/foundation/ability/ability_runtime/interfaces/kits/native/appkit/ability_runtime/app"',
    'OH_RUNTIME_ROOT="$OH/foundation/ability/ability_runtime/interfaces/inner_api/runtime/include"',
    '"$OH_APPKIT_APP_ROOT/ohos_application.h"',
    '"$OH_ABILITY_STAGE_ROOT/ability_stage.h"',
    '"$OH_RUNTIME_ROOT/runtime.h"',
    '-I$PM_SOURCE_ROOT/application_info/include',
    '-I$PM_SOURCE_ROOT/component_resolver/include',
    '-I$OH_APPKIT_APP_ROOT',
    '-I$OH_ABILITY_STAGE_ROOT',
    '-I$OH_RUNTIME_ROOT',
    '"$PM_SOURCE_ROOT/jni/axml_parser.cpp"',
    '"$PM_SOURCE_ROOT/application_info/src/application_info_runtime_owner_v1.cpp"',
    '"$PM_SOURCE_ROOT/component_resolver/src/component_resolver_runtime_v1.cpp"',
    '"$PM_SOURCE_ROOT/install_plan/src/sha256.c"',
    '-lappkit_native.z',
    'required real adapter bridge input is missing or symlinked',
    'required package-manager source is missing or symlinked',
)


def validate(source: str) -> list[str]:
    errors = [token for token in REQUIRED_TOKENS if token not in source]
    package_block_start = source.find("# Package-manager is selected explicitly.")
    package_block_end = source.find(
        'SOURCES="$SOURCES $ADAPTER_ROOT/framework/native-compat/',
        package_block_start,
    )
    package_block = source[package_block_start:package_block_end]
    if package_block_start < 0 or package_block_end < 0:
        errors.append("explicit package-manager source block")
    elif '|| continue' in package_block:
        errors.append("package-manager source block silently skips missing inputs")
    elif package_block.count('"$PM_SOURCE_ROOT/jni/axml_parser.cpp"') != 1:
        errors.append("AxmlParser producer must appear exactly once")
    elif package_block.find('"$PM_SOURCE_ROOT/jni/axml_parser.cpp"') > package_block.find(
        '"$PM_SOURCE_ROOT/manifest_facts/src/manifest_facts_v1.cpp"'
    ):
        errors.append("AxmlParser producer must precede its manifest-facts consumer")
    link_block_start = source.find('LIBS="\\\n')
    link_block_end = source.find("\n\n# A.11:", link_block_start)
    link_block = source[link_block_start:link_block_end]
    if link_block_start < 0 or link_block_end < 0:
        errors.append("explicit strict link-input block")
    else:
        link_inputs = link_block.split()
        if link_inputs.count("-lappkit_native.z") != 1:
            errors.append("target appkit producer input must appear exactly once")
        platform_order = (
            "-lability_manager.z",
            "-lapp_manager.z",
            "-lappkit_native.z",
            "-lability_connect_callback_stub.z",
        )
        if all(token in link_inputs for token in platform_order):
            positions = tuple(link_inputs.index(token) for token in platform_order)
            if positions != tuple(sorted(positions)):
                errors.append("target appkit producer input must stay in the OH platform group")
    if "strict generation link failed; relaxed fallback is forbidden" not in source:
        errors.append("strict generation link guard")
    return errors


source = BUILD.read_text()
assert not validate(source), f"P1 canonical closure invalid: {validate(source)}"
print("PASS P1 canonical real-owner and target-OH closure")

fake_header = source.replace(
    'OH_ABILITY_STAGE_ROOT="$OH/foundation/ability/ability_runtime/interfaces/kits/native/appkit/ability_runtime/app"',
    'OH_ABILITY_STAGE_ROOT="$ADAPTER_ROOT/build/fake_headers"',
    1,
)
assert validate(fake_header), "N1 copied/fake ability-stage root was accepted"
print("PASS N1 fake ability-stage root rejected")

fake_runtime = source.replace(
    'OH_RUNTIME_ROOT="$OH/foundation/ability/ability_runtime/interfaces/inner_api/runtime/include"',
    'OH_RUNTIME_ROOT="$ADAPTER_ROOT/build/fake_headers"',
    1,
)
assert validate(fake_runtime), "N2 copied/fake runtime root was accepted"
print("PASS N2 fake runtime root rejected")

missing_owner = source.replace(
    '    "$PM_SOURCE_ROOT/application_info/src/application_info_runtime_owner_v1.cpp" \\\n',
    "",
)
assert validate(missing_owner), "N3 missing runtime-owner source was accepted"
print("PASS N3 missing runtime-owner source rejected")

missing_axml_producer = source.replace(
    '    "$PM_SOURCE_ROOT/jni/axml_parser.cpp" \\\n',
    "",
    1,
)
assert validate(missing_axml_producer), "N4 missing AxmlParser producer was accepted"
print("PASS N4 missing AxmlParser producer rejected")

duplicate_axml_producer = source.replace(
    '    "$PM_SOURCE_ROOT/jni/axml_parser.cpp" \\\n',
    '    "$PM_SOURCE_ROOT/jni/axml_parser.cpp" \\\n'
    '    "$PM_SOURCE_ROOT/jni/axml_parser.cpp" \\\n',
    1,
)
assert validate(duplicate_axml_producer), "N5 duplicate AxmlParser producer was accepted"
print("PASS N5 duplicate AxmlParser producer rejected")

misordered_axml_producer = source.replace(
    '    "$PM_SOURCE_ROOT/jni/axml_parser.cpp" \\\n',
    "",
    1,
).replace(
    '    "$PM_SOURCE_ROOT/manifest_facts/src/manifest_facts_v1.cpp" \\\n',
    '    "$PM_SOURCE_ROOT/manifest_facts/src/manifest_facts_v1.cpp" \\\n'
    '    "$PM_SOURCE_ROOT/jni/axml_parser.cpp" \\\n',
    1,
)
assert validate(misordered_axml_producer), "F1 misordered AxmlParser producer was accepted"
print("PASS F1 AxmlParser producer-after-consumer ordering rejected")

missing_appkit_input = source.replace(" -lappkit_native.z", "", 1)
assert validate(missing_appkit_input), "N6 missing target appkit link input was accepted"
print("PASS N6 missing target appkit link input rejected")

duplicate_appkit_input = source.replace(
    " -lappkit_native.z",
    " -lappkit_native.z -lappkit_native.z",
    1,
)
assert validate(duplicate_appkit_input), "F5 duplicate target appkit link input was accepted"
print("PASS F5 duplicate target appkit link input rejected")

skip_missing = source.replace(
    '    if [ ! -f "$src" ] || [ -L "$src" ]; then\n'
    '        echo "ERROR: required package-manager source is missing or symlinked: $src" >&2\n'
    '        exit 2\n'
    '    fi\n',
    '    [ -f "$src" ] || continue\n',
    1,
)
assert validate(skip_missing), "F2 silent missing-source skip was accepted"
print("PASS F2 silent missing-source skip rejected")

without_preflight = source.replace(
    '    "$OH_ABILITY_STAGE_ROOT/ability_stage.h" \\\n',
    '',
    1,
)
assert validate(without_preflight), "F3 missing target ability-stage preflight was accepted"
print("PASS F3 missing target ability-stage preflight rejected")

without_runtime_preflight = source.replace(
    '    "$OH_RUNTIME_ROOT/runtime.h"; do',
    '    "$OH_ABILITY_STAGE_ROOT/ability_stage.h"; do',
    1,
)
assert validate(without_runtime_preflight), "F4 missing target runtime-header preflight was accepted"
print("PASS F4 missing target runtime-header preflight rejected")

with tempfile.TemporaryDirectory() as temp:
    target = Path(temp) / "bridge.sh"
    target.write_text(source)
    assert not validate(target.read_text())
print("PASS P2 deterministic non-mutating fixture replay")

print("adapter bridge include/source/link closure contract: PASS 13/13")
