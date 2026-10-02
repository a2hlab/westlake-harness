#!/bin/bash
# patch_irtoc.sh — neutralize irtoc build commands by replacing them with
# `touch` of the expected output .o files. irtoc's `run_ark_executable.py`
# action segfaults when processing interpreter_inline.bc; the resulting
# empty .o files are sufficient to satisfy the link graph since this project
# does not need libarkruntime.so / libani_helpers.z.so at runtime.
#
# OLD brittle approach: hard-coded sed at line 87148 — broken whenever OH
# toolchain.ninja layout shifts between gn runs.
#
# NEW robust approach: discover irtoc action rules dynamically by their
# target name pattern `gen/ark_sig/irtoc_*.o`, find the corresponding
# `rule <name> ... command = ...` block, and rewrite the command to a
# `touch ${out}` that uses ninja's per-edge output variable so one rule
# change covers every irtoc edge sharing that rule.
set -e

PROD="${OH_PRODUCT_NAME:-rk3568}"
NINJA_FILE="${OH_ROOT:-$HOME/oh}/out/$PROD/toolchain.ninja"

if [ ! -f "$NINJA_FILE" ]; then
    echo "[patch_irtoc] ERROR: $NINJA_FILE not found — skipping (gn gen not run yet?)" >&2; exit 1
fi

python3 - "$NINJA_FILE" << 'PYEOF'
import re
import sys

path = sys.argv[1]
with open(path, 'r') as f:
    lines = f.readlines()

# Find `build gen/ark_sig/irtoc_*.o: <rule> ...` edges
build_pat = re.compile(r'^build\s+(gen/ark_sig/irtoc_[a-z_]+\.o)\s*:\s*(\S+)')
edges = []
for i, line in enumerate(lines):
    m = build_pat.match(line)
    if m:
        edges.append((i, m.group(1), m.group(2)))

if not edges:
    print("[patch_irtoc] no irtoc build edges found — nothing to patch")
    sys.exit(0)

rule_names = set(e[2] for e in edges)

# For each unique rule, replace its command with `touch ${out}`
patched = 0
i = 0
while i < len(lines):
    m = re.match(r'^rule\s+(\S+)', lines[i])
    if m and m.group(1) in rule_names:
        j = i + 1
        while j < len(lines) and (lines[j].startswith(' ') or lines[j].startswith('\t')):
            if re.match(r'^\s*command\s*=', lines[j]):
                lines[j] = '  command = touch ${out}\n'
                patched += 1
                break
            j += 1
    i += 1

if patched:
    with open(path, 'w') as f:
        f.writelines(lines)
    print(f"[patch_irtoc] patched {patched} rules covering {len(edges)} irtoc edges")
    for edge_idx, out, rule in edges:
        print(f"  line {edge_idx+1}: {out} via rule {rule}")
else:
    print(f"[patch_irtoc] {len(edges)} edges found but no matching rule blocks (already phony?)")
PYEOF
