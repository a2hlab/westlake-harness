#!/usr/bin/env python3
"""Add OH_ADAPTER_APK_VERIFY_PREPASS_FAILED to the verified-session status enum
(full-src wire generation). The c_entry source returns it on prepass failure but
the enum never grew the value, which is why that TU never compiled on this tree.

Idempotent. Run ON hw248 against /opt/build-runs/2026-09-28-oh6.1.0.31-bms-label-resolve.
"""
from pathlib import Path

P = Path("/opt/build-runs/2026-09-28-oh6.1.0.31-bms-label-resolve/full-src/src/adapter"
         "/framework/package-manager/jni/apk_verified_session_c_api.h")
src = P.read_text()

if "OH_ADAPTER_APK_VERIFY_PREPASS_FAILED" in src:
    print("already present")
    raise SystemExit(0)

ANCHOR = "    OH_ADAPTER_APK_VERIFY_OUTPUT_TOO_SMALL = -2006,"
NEW = ANCHOR + "\n    OH_ADAPTER_APK_VERIFY_PREPASS_FAILED = -2007,"
if ANCHOR not in src:
    raise SystemExit("anchor not found — refusing blind patch")
P.write_text(src.replace(ANCHOR, NEW, 1))
print("enum added: OH_ADAPTER_APK_VERIFY_PREPASS_FAILED = -2007")
