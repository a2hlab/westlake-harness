#!/usr/bin/env python3
"""P/N/F contract for appspawn's project native-loader compile/link closure."""

from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "inner" / "compile_appspawnx.sh"
PRODUCER = (
    ROOT
    / "framework"
    / "native-loader-oh"
    / "include"
    / "nativeloader"
    / "native_loader.h"
)
INCLUDE_EDGE = "-I$ADAPTER/framework/native-loader-oh/include"
LINK_EDGE = "-lnativeloader"
NEEDED_EDGE = "libnativeloader.so"


def validate(source: str) -> list[str]:
    errors: list[str] = []
    block_start = source.find('INC="')
    block_end = source.find("\n\nBC=", block_start)
    if block_start < 0 or block_end < 0:
        errors.append("explicit appspawn include block")
        return errors

    include_block = source[block_start:block_end]
    include_inputs = include_block.split()
    if include_inputs.count(INCLUDE_EDGE) != 1:
        errors.append("project native-loader include edge must appear exactly once")
    if "art/libnativeloader/include" in include_block:
        errors.append("AOSP native-loader headers must not replace the project producer")

    libs_start = source.find('LIBS="')
    libs_end = source.find('\n\nif [ "$STRICT_BUILD"', libs_start)
    if libs_start < 0 or libs_end < 0:
        errors.append("explicit appspawn link block")
        return errors
    link_inputs = source[libs_start:libs_end].split()
    if link_inputs.count(LINK_EDGE) != 1:
        errors.append("direct native-loader link edge must appear exactly once")

    needed_start = source.find("    for needed in \\\n")
    needed_end = source.find("; do\n", needed_start)
    if needed_start < 0 or needed_end < 0:
        errors.append("strict postlink DT_NEEDED audit block")
        return errors
    needed_inputs = source[needed_start:needed_end].split()
    if needed_inputs.count(NEEDED_EDGE) != 1:
        errors.append("native-loader DT_NEEDED audit must appear exactly once")
    return errors


source = BUILD.read_text()
assert PRODUCER.is_file() and not PRODUCER.is_symlink(), "project producer is not regular"
assert not validate(source), f"P1 canonical include closure invalid: {validate(source)}"
print("PASS P1 project native-loader include edge present exactly once")

missing_edge = source.replace(f"{INCLUDE_EDGE} \\\n", "", 1)
assert validate(missing_edge), "N1 missing project native-loader include edge was accepted"
print("PASS N1 missing project native-loader include edge rejected")

duplicate_edge = source.replace(
    f"{INCLUDE_EDGE} \\\n",
    f"{INCLUDE_EDGE} \\\n{INCLUDE_EDGE} \\\n",
    1,
)
assert validate(duplicate_edge), "F1 duplicate project native-loader include edge was accepted"
print("PASS F1 duplicate project native-loader include edge rejected")

missing_link = source.replace(f" {LINK_EDGE} ", " ", 1)
assert validate(missing_link), "N2 missing direct native-loader link edge was accepted"
print("PASS N2 missing direct native-loader link edge rejected")

duplicate_link = source.replace(
    f" {LINK_EDGE} ",
    f" {LINK_EDGE} {LINK_EDGE} ",
    1,
)
assert validate(duplicate_link), "F2 duplicate direct native-loader link edge was accepted"
print("PASS F2 duplicate direct native-loader link edge rejected")

missing_needed = source.replace(f" {NEEDED_EDGE} ", " ", 1)
assert validate(missing_needed), "N3 missing native-loader DT_NEEDED audit was accepted"
print("PASS N3 missing native-loader DT_NEEDED audit rejected")

duplicate_needed = source.replace(
    f" {NEEDED_EDGE} ",
    f" {NEEDED_EDGE} {NEEDED_EDGE} ",
    1,
)
assert validate(duplicate_needed), "F3 duplicate native-loader DT_NEEDED audit was accepted"
print("PASS F3 duplicate native-loader DT_NEEDED audit rejected")

with tempfile.TemporaryDirectory() as temp:
    fixture = Path(temp) / "compile_appspawnx.sh"
    fixture.write_text(source)
    assert not validate(fixture.read_text())
print("PASS P2 deterministic non-mutating fixture replay")

print("appspawn native-loader compile/link contract: PASS 8/8")
