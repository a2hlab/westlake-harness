"""For each aconfig package javac could not find, name the java_aconfig_library that generates it."""
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
wanted = set(sys.argv[2:])
decl_pkg, lib_decl = {}, {}
module = re.compile(r'^(\w+)\s*\{(.*?)^\}', re.S | re.M)
for bp in root.rglob("*.bp"):
    try:
        text = bp.read_text(errors="replace")
    except OSError:
        continue
    for kind, body in module.findall(text):
        name = re.search(r'\bname:\s*"([^"]+)"', body)
        if not name:
            continue
        if kind == "aconfig_declarations":
            pkg = re.search(r'\bpackage:\s*"([^"]+)"', body)
            if pkg:
                decl_pkg[name.group(1)] = (pkg.group(1), bp.relative_to(root))
        elif kind == "java_aconfig_library":
            decl = re.search(r'\baconfig_declarations:\s*"([^"]+)"', body)
            mode = re.search(r'\bmode:\s*"([^"]+)"', body)
            if decl:
                lib_decl.setdefault(decl.group(1), []).append((name.group(1), mode.group(1) if mode else "production"))
for decl, (pkg, where) in sorted(decl_pkg.items(), key=lambda kv: kv[1][0]):
    if pkg in wanted:
        print(f"{pkg:40s} decl={decl:45s} libs={lib_decl.get(decl)}  ({where})")
