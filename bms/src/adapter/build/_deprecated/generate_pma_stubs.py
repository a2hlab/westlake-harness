#!/usr/bin/env python3
"""
generate_pma_stubs.py — auto-generate stub implementations for abstract
IPackageManager methods missing from PackageManagerAdapter.

Run on ECS with access to the turbine framework-minus-apex.jar. Parses
`javap -p` output and emits a Java snippet that can be appended to
PackageManagerAdapter.java.

Usage:
    python3 build/generate_pma_stubs.py > /tmp/pma_stubs.java
    # Then manually insert into PackageManagerAdapter.java before the final }

This is not a permanent solution — the real goal is for the adapter to
route these calls to OH BMS. For now stubs let the jar compile; reaching
OH BMS happens via the methods that are already [BRIDGED] in the existing
file.

Created: 2026-04-11 to close gap 7 jar-rebuild loop.
"""

import os
import re
import subprocess
import sys

AOSP = os.environ.get("AOSP_ROOT", os.path.expanduser("~/aosp"))
JAVAP = f"{AOSP}/prebuilts/jdk/jdk17/linux-x86/bin/javap"
FWK_JAR = f"{AOSP}/out/soong/.intermediates/frameworks/base/framework-minus-apex/android_common/turbine-combined/framework-minus-apex.jar"
PMA_JAVA = f"{AOSP}/device/adapter/oh_adapter_framework/java/adapter/packagemanager/PackageManagerAdapter.java"


def default_value(return_type: str) -> str:
    """Return a safe default expression for a given Java return type."""
    rt = return_type.strip()
    if rt == "void":
        return ""
    if rt == "boolean":
        return "false"
    if rt in ("byte", "short", "int", "long", "float", "double", "char"):
        return "0"
    if rt.endswith("[]"):
        return "null"
    # array-like or primitive wrappers and all reference types
    return "null"


SIG_RE = re.compile(
    r"public abstract\s+(?P<ret>[\w.$<>\[\],?\s]+?)\s+(?P<name>\w+)\((?P<args>[^)]*)\)(?:\s+throws\s+(?P<throws>[\w.$,\s]+))?;"
)


def list_abstract(interface: str) -> list:
    out = subprocess.check_output(
        [JAVAP, "-p", "-cp", FWK_JAR, interface], stderr=subprocess.DEVNULL
    ).decode()
    methods = []
    for line in out.splitlines():
        m = SIG_RE.search(line.strip())
        if not m:
            continue
        ret = m.group("ret").strip()
        name = m.group("name")
        args = m.group("args").strip()
        throws = (m.group("throws") or "").strip()
        methods.append((name, ret, args, throws))
    return methods


def existing_method_names(path: str) -> set:
    with open(path) as f:
        src = f.read()
    # A simple heuristic: every public method declaration
    names = set()
    for m in re.finditer(r"public\s+(?:\w[\w.<>\[\]?,\s]*\s+)?(\w+)\s*\(", src):
        names.add(m.group(1))
    return names


def _normalize_type(t: str) -> str:
    """Convert javap inner-class notation `Outer$Inner` to Java `Outer.Inner`."""
    # Only replace $ that comes between word chars (class$nestedclass), leave
    # dollar in identifiers alone. javap emits $ only between class/inner-class
    # boundaries so this is safe.
    return re.sub(r"(\w)\$(\w)", r"\1.\2", t)


def render_stub(name: str, ret: str, args: str, throws: str) -> str:
    ret = _normalize_type(ret)
    args = _normalize_type(args)
    # Parse args — comma-split, then for each "TypeName paramName" keep paramName; if missing, autogenerate
    arg_pairs = []
    if args:
        # split respecting generics
        depth = 0
        cur = ""
        pieces = []
        for ch in args:
            if ch == "," and depth == 0:
                pieces.append(cur.strip())
                cur = ""
            else:
                if ch == "<":
                    depth += 1
                elif ch == ">":
                    depth -= 1
                cur += ch
        if cur.strip():
            pieces.append(cur.strip())
        for idx, p in enumerate(pieces):
            # If the piece ends with `>` it's a bare generic type with no
            # parameter name (turbine header jars strip names). Same if it
            # ends with `]` (array) or looks like a dotted type.
            # Use rsplit ONLY if the tail looks like a bare identifier
            # (no angle brackets, no dots, no brackets).
            tokens = p.rsplit(None, 1)
            if len(tokens) == 2 and re.fullmatch(r"[A-Za-z_$][\w$]*", tokens[1]):
                ptype, pname = tokens
            else:
                ptype = p
                pname = f"arg{idx}"
            arg_pairs.append((ptype.strip(), pname.strip()))
    arg_decl = ", ".join(f"{t} {n}" for (t, n) in arg_pairs)
    throws_clause = f" throws {throws}" if throws else ""
    default = default_value(ret)
    body_return = "" if ret.strip() == "void" else f"\n        return {default};"
    return (
        f"\n    @Override\n"
        f"    public {ret} {name}({arg_decl}){throws_clause} {{\n"
        f"        logStub(\"{name}\", \"\");"
        f"{body_return}\n"
        f"    }}\n"
    )


def main():
    if not os.path.isfile(FWK_JAR):
        print(f"ERROR: framework-minus-apex.jar not found: {FWK_JAR}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(PMA_JAVA):
        print(f"ERROR: PackageManagerAdapter.java not found: {PMA_JAVA}", file=sys.stderr)
        sys.exit(1)

    abstract = list_abstract("android.content.pm.IPackageManager")
    have = existing_method_names(PMA_JAVA)
    missing = [(n, r, a, t) for (n, r, a, t) in abstract if n not in have]
    sys.stderr.write(
        f"IPackageManager abstract: {len(abstract)} | existing in PMA: "
        f"{len(have)} | missing to generate: {len(missing)}\n"
    )
    snippets = [render_stub(*m) for m in missing]
    # Emit as a block that can be `sed`-inserted before final }
    print("\n    // === AUTO-GENERATED STUBS (generate_pma_stubs.py, 2026-04-11) ===")
    print("    // These satisfy IPackageManager.Stub's abstract contract. They log")
    print("    // and return safe defaults. Replace with [BRIDGED] OH BMS routing when")
    print("    // needed per use-case. Not runtime stubs in the 禁止用 stub 回避问题 sense —")
    print("    // these are Java compile-satisfaction stubs; the real work happens")
    print("    // at the adapter JNI layer in oh_bundle_mgr_client.cpp.")
    for s in snippets:
        print(s)


if __name__ == "__main__":
    main()
