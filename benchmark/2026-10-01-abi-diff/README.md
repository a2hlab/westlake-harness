# ABI signature diff for rebuilt native libraries (2026-10-01)

**What was wrong.** The strict rebuild of the 846 bridge (`7cf8ebcc`) was accepted on an export-table diff:
"14 missing exports, no consumers". On the board (#96, 5ea) every app, controls included, died in
`ViewRootImpl.setView` with `InvalidDisplayException`. A missing symbol fails loudly at load; a changed signature
fails silently — the old caller keeps the old calling convention and the callee reads the wrong argument slots.

**Tool.** `scripts/lab/abi_diff.py --old <deployed.so> --new <rebuilt.so> [--consumer <lib.so> ...]` lists removed /
added exports, **signature drift** (a removed C++ export whose qualified name reappears with a different mangled
name) and **consumer breaks** (a consumer's undefined symbol the new build no longer defines). Exit 1 on any drift or
break. Tests: `scripts/lab/tests/test_abi_diff.py`.

**Result on the bridge** (`bridge-846-vs-7cf8ebcc.{txt,json}`; deployed `84695d62…` vs rebuilt `7cf8ebcc…`, consumer
`liboh_android_runtime.so` of U8): 14 removed, 318 added, **8 signature drifts** (5 distinct functions), 0 consumer
breaks. Among them `OHWindowManagerClient::createSession(..., int, int, int, int, unsigned long)` gained an `int`
— cc-wiki's suspect for #96 — and `OHInputBridge::injectKeyEvent / injectTouchEvent` gained three parameters.
The "no consumers" finding was true for imports and still missed all of this.

**Rule.** A rebuilt native library is accepted only with `abi_diff.py` exit 0 against the deployed one (or each drift
explained: the caller is rebuilt in the same package with the new convention).
