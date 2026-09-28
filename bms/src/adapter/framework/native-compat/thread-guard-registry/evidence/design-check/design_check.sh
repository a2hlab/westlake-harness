#!/bin/bash
# HanBing 设计一致性 — 机械门 (skill hanbing-design-check 步骤0)
# 用法: design_check.sh <libart.so | class_linker.cc | source_tree_dir> [--gz05]
# 机械验可自动判的铁律点；判断/语境留给 skill 的人工 5 问门。
T="${1:?用法: design_check.sh <libart.so|class_linker.cc|tree> [--gz05]}"
REMOTE=""; [ "$2" = "--gz05" ] && REMOTE="ssh gz05"
run(){ if [ -n "$REMOTE" ]; then $REMOTE "$1"; else eval "$1"; fi; }
echo "════ HanBing 机械门: $T ════"

# 铁律1 — class_linker/vtable 补丁 (FIX-VTABLE-A 越界)
echo "── [铁律1] ART/class_linker 补丁检查 ──"
if echo "$T" | grep -q '\.so$'; then
  N=$(run "strings '$T' 2>/dev/null | grep -c 'FIX-VTABLE-A'")
  if [ "${N:-0}" -gt 0 ]; then echo "  ❌ Q1 红: libart 含 $N 个 FIX-VTABLE-A 标记 = 改了 class_linker = 背离铁律1"; else echo "  ✅ Q1: 无 FIX-VTABLE-A (干净 libart)"; fi
elif echo "$T" | grep -q 'class_linker'; then
  N=$(run "grep -c 'FIX-VTABLE-A' '$T' 2>/dev/null")
  if [ "${N:-0}" -gt 0 ]; then echo "  ❌ Q1 红: class_linker.cc 含 $N 个 FIX-VTABLE-A 块 = 背离铁律1 → 移除"; else echo "  ✅ Q1: class_linker 无 FIX-VTABLE-A"; fi
else
  N=$(run "grep -rc 'FIX-VTABLE-A' '$T/art/runtime/class_linker.cc' 2>/dev/null")
  echo "  class_linker FIX-VTABLE-A 计数 = ${N:-?} (>0 → ❌ 铁律1)"
fi

# 铁律4 (基础) — asm_defines POINTER_SIZE (D600 须 0x8 / D200 须 0x4)
if echo "$T" | grep -qv '\.so$' && echo "$T" | grep -qv 'class_linker'; then
  echo "── [铁律4 基础] asm_defines POINTER_SIZE ──"
  PS=$(run "grep -m1 POINTER_SIZE '$T/art/asm_defines.h' 2>/dev/null | grep -oE '0x.'")
  echo "  $T/art/asm_defines.h POINTER_SIZE = ${PS:-缺}  (D600-arm64 须 0x8 / D200-arm32 须 0x4)"
fi

echo "════ 机械门完。剩余 Q2(BCP)/Q3(适配层)/Q5(truly-cold) 走 skill 人工 5 问门 ════"
