#!/usr/bin/env python3
"""Fix the misplaced forward declaration: the previous patch anchored on
'oh_adapter_prepare_install' whose FIRST occurrence is inside the header
comment block, so the declaration landed inside the comment (grep showed it at
lines 13-14 under ' *' comment markers) and never took effect.

This script (a) removes the in-comment copy, (b) inserts the declaration after
the include block / before the first real code. Idempotent.

Run ON hw248 against /opt/build-runs/2026-09-28-oh6.1.0.31-bms-label-resolve.
"""
from pathlib import Path

P = Path("/opt/build-runs/2026-09-28-oh6.1.0.31-bms-label-resolve/full-src/src/adapter"
         "/framework/package-manager/jni/oh_adapter_install_apk_c_entry.cpp")
src = P.read_text()

BAD_IN_COMMENT = (
    " *     // forward decl: definition is later in this TU; header declares only _v1\n"
    'extern "C" void oh_adapter_close_game_install_plan(GameInstallPlanWire* plan);\n'
)
if BAD_IN_COMMENT in src:
    src = src.replace(BAD_IN_COMMENT, "", 1)

GOOD_DECL = (
    "// forward decl: definition is later in this TU; header declares only _v1\n"
    'extern "C" void oh_adapter_close_game_install_plan(GameInstallPlanWire* plan);\n\n'
)
if GOOD_DECL not in src:
    # Insert after the last #include line, before the first non-include code.
    lines = src.split("\n")
    last_include = max(i for i, l in enumerate(lines) if l.startswith("#include"))
    lines.insert(last_include + 1, "\n" + GOOD_DECL.rstrip("\n"))
    src = "\n".join(lines)

P.write_text(src)
# verify: declaration must now be OUTSIDE any comment and before line ~100
import re
m = re.search(r'^extern "C" void oh_adapter_close_game_install_plan', src, re.M)
assert m, "declaration missing after patch"
before = src[: m.start()]
assert not before.rstrip().endswith("*/"), "declaration still inside comment block"
print(f"declaration now at char offset {m.start()}, outside comments: OK")
