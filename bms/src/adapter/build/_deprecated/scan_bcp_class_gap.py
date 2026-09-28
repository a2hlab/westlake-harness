#!/usr/bin/env python3
"""
scan_bcp_class_gap.py — B.16 (2026-04-28)

精确扫描 framework.jar 字节码引用的所有 class types，与 BCP 8 个 jar 已定义
class 集合做差集，得出 framework.jar transitive 依赖中缺失的 mainline 类清单。

用法:
    python3 build/scan_bcp_class_gap.py \\
        --aosp-fwk     /home/.../adapter/out/aosp_fwk \\
        --adapter-out  /home/.../adapter/out/adapter \\
        --report       doc/bcp_gap_report.txt \\
        [--gen-stubs   framework/mainline-stubs/java/]
        [--dexdump     /path/to/dexdump]   # default: aosp prebuilt

铁律对应:
  doc/overall_design.html §15  Framework 完整保留 + IPC 适配
  doc/interface_bridge_design.html §21  BCP 缺口扫描方法论

输出:
  - 每个 BCP jar 定义类计数
  - framework.jar 引用 type 计数
  - GAP 清单按 namespace 分组
  - 推荐 stub 生成路径
"""
import argparse
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

# BCP jar 顺序（与运行时 -Xbootclasspath 一致）
# 2026-04-30: B.41 抛弃 framework.jar 的决策已回退 — framework.jar 重新进 BCP。
# oh-adapter-framework.jar 在 adapter_out 路径下，由下方代码追加。
BCP_JARS = [
    "core-oj.jar",
    "core-libart.jar",
    "core-icu4j.jar",
    "okhttp.jar",
    "bouncycastle.jar",
    "apache-xml.jar",
    "framework.jar",
    "adapter-mainline-stubs.jar",
]

# 这些 namespace 的类被引用但不在 BCP 不构成缺口（libcore/JDK/特殊提供）
WHITELIST_PREFIXES = (
    "java/", "javax/", "kotlin/", "kotlinx/",
    "sun/", "jdk/", "com/sun/",
    "libcore/", "dalvik/system/", "org/json/",
    "org/xmlpull/", "org/w3c/", "org/xml/",
    "org/apache/harmony/dalvik/",
)


def run_dexdump(dexdump_bin: str, jar_path: str) -> str:
    """运行 dexdump -d 提取全 disasm（含 method 签名 + invoke + field type 等所有 type refs）"""
    try:
        result = subprocess.run(
            [dexdump_bin, "-d", jar_path],
            capture_output=True, text=True, encoding="latin-1", timeout=600,
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        sys.stderr.write(f"WARN: dexdump -d timeout on {jar_path}\n")
        return ""


def run_dexdump_l(dexdump_bin: str, jar_path: str) -> str:
    """运行 dexdump -l plain 提取 defined classes"""
    try:
        result = subprocess.run(
            [dexdump_bin, "-l", "plain", jar_path],
            capture_output=True, text=True, encoding="latin-1", timeout=300,
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        sys.stderr.write(f"WARN: dexdump -l timeout on {jar_path}\n")
        return ""


def extract_type_ids(dexdump_output: str) -> set:
    """从 dexdump -d 输出解析所有 L<class>; 形 type ref（含 method 签名 / 字段 / invoke / instance-of 等）"""
    refs = set()
    # Match L<path/to/Class>; in any context: quoted, in invoke, in field types, etc.
    # Excludes primitives (V, I, J, F, D, B, C, S, Z) and array prefix [
    # Allows nested arrays like [[Lfoo/Bar;
    pattern = re.compile(r"L([a-zA-Z][a-zA-Z0-9_/$]*);")
    for m in pattern.finditer(dexdump_output):
        cls = m.group(1)
        # Filter trivial false positives (rare regex matches in string literals are fine to include — dedupes)
        if "/" in cls or cls in ("Object", "String", "Class"):
            refs.add(cls)
    return refs


def extract_defined_classes(dexdump_output: str) -> set:
    """从 dexdump -l plain 输出解析 defined class headers (Class #N -- 'L...;')"""
    defined = set()
    pat = re.compile(r"^Class #\d+\s")
    name_pat = re.compile(r"Class descriptor\s*:\s*'L([a-zA-Z][\w/$]*);'")
    in_class_block = False
    for line in dexdump_output.splitlines():
        if pat.match(line):
            in_class_block = True
            continue
        if in_class_block:
            m = name_pat.search(line)
            if m:
                defined.add(m.group(1))
                in_class_block = False
    return defined


def all_dex_in_jar(jar_path: str):
    """yield each classesN.dex inside a multi-dex jar"""
    with zipfile.ZipFile(jar_path) as zf:
        for n in zf.namelist():
            if n.startswith("classes") and n.endswith(".dex"):
                yield n


def scan_jar(dexdump_bin: str, jar_path: str, mode: str) -> set:
    """
    scan one jar file. mode='refs' returns referenced types (via -h type_ids),
    mode='defined' returns defined classes (via -l plain).
    Handles multi-dex jars by extracting each .dex and dumping individually.
    """
    result = set()
    tmp_dir = Path("/tmp") / f"scan_bcp_{os.getpid()}"
    tmp_dir.mkdir(exist_ok=True)
    try:
        with zipfile.ZipFile(jar_path) as zf:
            for entry in zf.namelist():
                if not (entry.startswith("classes") and entry.endswith(".dex")):
                    continue
                tmp_path = tmp_dir / entry.replace("/", "_")
                with zf.open(entry) as src, open(tmp_path, "wb") as dst:
                    dst.write(src.read())
                if mode == "refs":
                    out = run_dexdump(dexdump_bin, str(tmp_path))
                    result |= extract_type_ids(out)
                else:
                    out = run_dexdump_l(dexdump_bin, str(tmp_path))
                    result |= extract_defined_classes(out)
                tmp_path.unlink()
    finally:
        try:
            tmp_dir.rmdir()
        except OSError:
            pass
    return result


def is_whitelisted(class_path: str) -> bool:
    """返回 True 表示该类即使 BCP 没定义也不算缺口（libcore/JDK 内置）"""
    return any(class_path.startswith(p) for p in WHITELIST_PREFIXES)


def main():
    ap = argparse.ArgumentParser(description="B.16 BCP class gap scanner")
    ap.add_argument("--aosp-fwk", required=True,
                    help="path to aosp_fwk dir containing core-oj.jar etc.")
    ap.add_argument("--adapter-out", required=True,
                    help="path to adapter out dir containing oh-adapter-framework.jar")
    ap.add_argument("--report", required=True, help="output report .txt")
    ap.add_argument("--target-jar", default=None,
                    help="path to jar whose refs are scanned (default: aosp_fwk/framework.jar)")
    ap.add_argument("--gen-stubs", default=None,
                    help="optional: directory to write empty .java stubs for each gap class")
    ap.add_argument("--dexdump",
                    default="/home/HanBingChen/aosp/prebuilts/sdk/tools/linux/bin/dexdump",
                    help="path to dexdump binary")
    args = ap.parse_args()

    aosp = Path(args.aosp_fwk)
    adapter = Path(args.adapter_out)
    # 2026-04-30: B.41 抛弃 framework.jar 的决策已回退 — 默认扫 aosp_fwk/framework.jar。
    if args.target_jar:
        framework_jar = Path(args.target_jar)
    else:
        framework_jar = aosp / "framework.jar"
    if not framework_jar.is_file():
        sys.exit(f"ERROR: target jar {framework_jar} not found")

    # 1. extract framework.jar all referenced type_ids (transitive deps)
    print(f"[1/3] scanning framework.jar refs ...", file=sys.stderr)
    fwk_refs = scan_jar(args.dexdump, str(framework_jar), "refs")
    print(f"      framework.jar references {len(fwk_refs)} unique types",
          file=sys.stderr)

    # 2. extract BCP jars defined classes
    print("[2/3] scanning BCP jars defined classes ...", file=sys.stderr)
    # framework.jar 与其它 AOSP-built core jars 都在 aosp_fwk/；
    # oh-adapter-framework.jar 在 adapter_out/（避免双源漂移）。
    bcp_paths = []
    # 2026-04-30 G2.13: adapter-mainline-stubs.jar canonical path = out/adapter/
    # (per feedback_mainline_stubs_single_source.md / G2.8 dual-source fix).
    # Scanner now resolves each BCP jar by checking aosp_fwk first, then
    # adapter_out — matches the G2.8 deployment topology.
    for name in BCP_JARS:
        p_aosp = aosp / name
        p_adapter = adapter / name
        if p_aosp.is_file():
            bcp_paths.append(p_aosp)
        elif p_adapter.is_file():
            bcp_paths.append(p_adapter)
        else:
            sys.stderr.write(f"WARN: {name} not in aosp_fwk or adapter, skipping\n")
    oh_adapter_fwk = adapter / "oh-adapter-framework.jar"
    if oh_adapter_fwk.is_file():
        bcp_paths.append(oh_adapter_fwk)
    else:
        sys.stderr.write(f"WARN: {oh_adapter_fwk} not found, skipping\n")

    bcp_defined = set()
    per_jar_count = {}
    for p in bcp_paths:
        d = scan_jar(args.dexdump, str(p), "defined")
        bcp_defined |= d
        per_jar_count[p.name] = len(d)
        print(f"      {p.name}: {len(d)} classes", file=sys.stderr)

    # 3. compute gap
    gap = (fwk_refs - bcp_defined)
    gap_filtered = sorted([c for c in gap if not is_whitelisted(c)])
    gap_whitelisted_count = len(gap) - len(gap_filtered)

    # 4. write report
    print(f"[3/3] writing report → {args.report}", file=sys.stderr)
    with open(args.report, "w", encoding="utf-8") as f:
        f.write("# B.16 BCP class gap scan report\n")
        f.write(f"# generated: {os.popen('date -u +%Y-%m-%dT%H:%M:%SZ').read().strip()}\n")
        f.write(f"# framework.jar refs: {len(fwk_refs)}\n")
        f.write(f"# BCP defined: {len(bcp_defined)}\n")
        f.write(f"# raw gap: {len(gap)}\n")
        f.write(f"# whitelisted (java/javax/kotlin/sun/jdk/libcore/...): {gap_whitelisted_count}\n")
        f.write(f"# remaining gap (mainline / unknown to fix): {len(gap_filtered)}\n\n")
        f.write("# Per-jar defined class count:\n")
        for n, c in per_jar_count.items():
            f.write(f"#   {n}: {c}\n")
        f.write("\n")
        # Group by namespace prefix
        by_pkg = {}
        for c in gap_filtered:
            pkg = "/".join(c.split("/")[:3]) if "/" in c else c
            by_pkg.setdefault(pkg, []).append(c)
        f.write("# === GAP CLASSES (sorted by package) ===\n\n")
        for pkg in sorted(by_pkg.keys()):
            f.write(f"# {pkg}/  ({len(by_pkg[pkg])} classes)\n")
            for c in sorted(by_pkg[pkg]):
                f.write(f"  {c.replace('/', '.')}\n")
            f.write("\n")

    print(f"DONE. {len(gap_filtered)} mainline class gaps in report.",
          file=sys.stderr)

    # 5. optionally generate stub Java sources (outer + nested inner classes)
    if args.gen_stubs and gap_filtered:
        stubs_dir = Path(args.gen_stubs)
        stubs_dir.mkdir(parents=True, exist_ok=True)

        # Group gap classes by their outer-most class.
        # For "android/foo/Outer$Inner$Deeper", outer = "android/foo/Outer"
        # Each outer becomes its own .java file; inners are static-class members.
        groups = {}  # outer_path -> list of (cls_path, depth_chain)
        for c in gap_filtered:
            parts = c.split("/")
            last = parts[-1]
            chain = last.split("$")  # ["Outer"] or ["Outer", "Inner", "Deeper"]
            outer_simple = chain[0]
            outer_path = "/".join(parts[:-1] + [outer_simple])
            groups.setdefault(outer_path, []).append((c, chain))

        gen_count = 0
        skipped = 0
        for outer_path, members in groups.items():
            outer_parts = outer_path.split("/")
            outer_simple = outer_parts[-1]
            pkg = ".".join(outer_parts[:-1])
            pkg_dir = stubs_dir.joinpath(*outer_parts[:-1])
            pkg_dir.mkdir(parents=True, exist_ok=True)
            stub_path = pkg_dir / f"{outer_simple}.java"
            if stub_path.exists():
                # Don't clobber hand-written stubs (e.g. existing TetheringManager.java)
                skipped += 1
                continue

            # Sort members so outer comes first, then inner sorted by depth
            members.sort(key=lambda x: (len(x[1]), x[1]))

            with open(stub_path, "w", encoding="utf-8") as fs:
                fs.write("// Auto-generated by scan_bcp_class_gap.py (B.16/B.18)\n")
                fs.write(f"// {pkg}.{outer_simple} — empty mainline stub + nested inner classes\n")
                fs.write("// Per overall_design §15.1 第 3 条原则:\n")
                fs.write("//   HelloWorld 不需要 → 空 stub；HelloWorld 必需路径 → 手工补 method 真路由\n")
                fs.write(f"package {pkg};\n\n")
                # Build nested tree
                # Each member: chain=[Outer], [Outer, Inner], [Outer, Inner, Deeper]
                # Print outer class { ... inner classes ... }
                tree = {}
                for _path, chain in members:
                    cur = tree
                    for seg in chain:
                        cur = cur.setdefault(seg, {})

                def emit(name, subtree, indent):
                    pad = "    " * indent
                    fs.write(f"{pad}public static class {name} {{\n")
                    fs.write(f"{pad}    public {name}() {{}}\n")
                    for child_name, child_tree in sorted(subtree.items()):
                        emit(child_name, child_tree, indent + 1)
                    fs.write(f"{pad}}}\n")

                # Outer class is special — not "static class" since it's top-level
                outer_subtree = tree.get(outer_simple, {})
                fs.write(f"public class {outer_simple} {{\n")
                fs.write(f"    public {outer_simple}() {{}}\n")
                for child_name, child_tree in sorted(outer_subtree.items()):
                    emit(child_name, child_tree, 1)
                fs.write("}\n")
            gen_count += 1
        total_classes = sum(len(m) for m in groups.values())
        print(f"Generated {gen_count} stub source files (covering {total_classes} classes "
              f"including inner; skipped {skipped} pre-existing) under {stubs_dir}",
              file=sys.stderr)

    return 0 if not gap_filtered else 1


if __name__ == "__main__":
    sys.exit(main())
