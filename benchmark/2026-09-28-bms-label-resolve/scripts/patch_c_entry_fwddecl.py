#!/usr/bin/env python3
"""Forward-declare oh_adapter_close_game_install_plan before its first use in
oh_adapter_install_apk_c_entry.cpp (the wire-generation definition sits later in
the same TU at the close/validate helpers; the header only declares the _v1
variant, so uses above the definition don't resolve). Idempotent.

Run ON hw248 against /opt/build-runs/2026-09-28-oh6.1.0.31-bms-label-resolve.
"""
from pathlib import Path

P = Path("/opt/build-runs/2026-09-28-oh6.1.0.31-bms-label-resolve/full-src/src/adapter"
         "/framework/package-manager/jni/oh_adapter_install_apk_c_entry.cpp")
src = P.read_text()

DECL = 'extern "C" void oh_adapter_close_game_install_plan(GameInstallPlanWire* plan);\n'
if "forward decl" in src.split("oh_adapter_verify_and_parse_apk")[0]:
    print("already patched")
    raise SystemExit(0)

# Insert the declaration right before the first function that uses it.
ANCHOR = "extern \"C\" int oh_adapter_prepare_install"
if ANCHOR not in src:
    # fall back: before the wire-plan validate/close users' enclosing function
    ANCHOR = "extern \"C\" int oh_adapter_verify_and_parse_apk"
if ANCHOR not in src:
    raise SystemExit("no anchor found — refusing blind patch")

src = src.replace(ANCHOR, "// forward decl: definition is later in this TU; header declares only _v1\n" + DECL + ANCHOR, 1)
P.write_text(src)
print("forward declaration added")
