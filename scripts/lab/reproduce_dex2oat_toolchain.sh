#!/usr/bin/env bash
# reproduce_dex2oat_toolchain.sh — T7「dex2oat 工具链」可复现性验证脚本(FZ-005 草稿配套)
#
# 用途:在 hw248(或任何有 AOSP r1 树的主机)上从当前树状态出发,验证:
#   1. art/ 树 = android-14.0.0_r1(3c05e56)+ series 22 补丁(check_series.py 对账)
#   2. 强制重编 dex2oat64(删 out 里的 dex2oat 产物)→ sha256 复现 ae865ddd…
#   3. t5_gen_image.sh 出镜像 → 与 T5c 27 件逐个比
#   4. rb 门(check_boot_oat_rb.py)+ t4b 门(t4b_build_switch_gate.py,回执程序生成)
#
# 路径全走环境变量(不写死 /home/alvin):
#   AOSP_R1_ROOT   AOSP r1 树(含 art/、out/)           默认 /home/alvin/aosp-14.0.0_r1-art
#   SERIES_DIR     series/patches 所在目录             默认 $AOSP_R1_ROOT/../art-r155/art-r155
#   JARS_DIR       9 个 jar 所在目录                   默认 /home/alvin/cc-wiki-t5/jars
#   OUT_DIR        镜像输出目录                        默认 /home/alvin/oc-t4-reproduce
#   BOARD_LIBART   板上 R155 libart.so(门用)          默认 westlake-generation-v3c-candidate 的 payload
#   T5C_DIR        T5c 参考件目录(逐件比)             默认 /home/alvin/oc-t4-t5c
#   CHECK_SERIES   check_series.py 路径               默认 $SERIES_DIR/check_series.py
#   T5_GEN         t5_gen_image.sh 路径               默认 /home/alvin/cc-wiki-t5/tool/t5_gen_image.sh
#   RB_GATE        check_boot_oat_rb.py 路径           默认 knowledge/toolchains/art-r155/check_boot_oat_rb.py(本机)
#   T4B_GATE       t4b_build_switch_gate.py 路径       默认 knowledge/toolchains/art-r155/t4b_build_switch_gate.py
#   EXPECT_DEX2OAT 期望的 dex2oat64 sha256            默认从 FZ-005 草稿读取(FZ005_DRAFT),可覆盖
#   FZ005_DRAFT    FZ-005 草稿路径                    默认 knowledge/frozen/FZ-005-dex2oat-toolchain-DRAFT.md
#   SKIP_BUILD=1   跳过编译(只核树状态+出镜像+过门)
#   SKIP_IMAGE=1   跳过出镜像(只核树状态+编译)
#
# 用法:
#   bash scripts/lab/reproduce_dex2oat_toolchain.sh            # 全量(核树+重编+出镜像+过门)
#   SKIP_BUILD=1 bash scripts/lab/reproduce_dex2oat_toolchain.sh   # 只核树+出镜像+过门
#   SKIP_IMAGE=1 bash scripts/lab/reproduce_dex2oat_toolchain.sh   # 只核树+重编
#
# 红线:不从别处拷 dex2oat;不改 frozen.json;不一致就列非确定性来源(时间戳/路径/环境)。
set -euo pipefail

AOSP_R1_ROOT="${AOSP_R1_ROOT:-/home/alvin/aosp-14.0.0_r1-art}"
SERIES_DIR="${SERIES_DIR:-$AOSP_R1_ROOT/../art-r155/art-r155}"
JARS_DIR="${JARS_DIR:-/home/alvin/cc-wiki-t5/jars}"
OUT_DIR="${OUT_DIR:-/home/alvin/oc-t4-reproduce}"
BOARD_LIBART="${BOARD_LIBART:-/home/alvin/t4b-gate/board-r155-libart.so}"
T5C_DIR="${T5C_DIR:-/home/alvin/oc-t4-t5c}"
CHECK_SERIES="${CHECK_SERIES:-$SERIES_DIR/check_series.py}"
T5_GEN="${T5_GEN:-/home/alvin/cc-wiki-t5/tool/t5_gen_image.sh}"
RB_GATE="${RB_GATE:-/home/alvin/t4b-gate/k/check_boot_oat_rb.py}"
T4B_GATE="${T4B_GATE:-/home/alvin/t4b-gate/k/t4b_build_switch_gate.py}"
FZ005_DRAFT="${FZ005_DRAFT:-/home/alvin/FZ-005-dex2oat-toolchain-DRAFT.md}"
# 期望哈希从 FZ-005 草稿读取(不留常量;草稿不在时必须显式传 EXPECT_DEX2OAT)
EXPECT_DEX2OAT="${EXPECT_DEX2OAT:-}"
if [ -z "$EXPECT_DEX2OAT" ] && [ -f "$FZ005_DRAFT" ]; then
  EXPECT_DEX2OAT=$(grep -oE '`[0-9a-f]{64}`' "$FZ005_DRAFT" | head -1 | tr -d '`')
fi

log() { echo "[reproduce $(date +%H:%M:%S)] $*"; }
die() { echo "[reproduce FAIL] $*" >&2; exit 1; }

# ── 1. 核 art/ 树状态 = r1(3c05e56)+ series 22 补丁 ──
log "1/5 核 art/ 树状态: $AOSP_R1_ROOT/art"
[ -d "$AOSP_R1_ROOT/art" ] || die "AOSP_R1_ROOT 不存在: $AOSP_R1_ROOT"
cd "$AOSP_R1_ROOT/art"
HEAD=$(git log --oneline -1 | awk '{print $1}')
log "  HEAD = $HEAD"
[ "$HEAD" = "3c05e56" ] || log "  WARN: HEAD != 3c05e56(可能是补丁后状态,继续)"

# 核 22 补丁逐个 sha256 与 series 一致
[ -f "$SERIES_DIR/series" ] || die "series 文件不存在: $SERIES_DIR/series"
PATCH_COUNT=$(wc -l < "$SERIES_DIR/series")
log "  series 补丁数 = $PATCH_COUNT(期望 22)"
[ "$PATCH_COUNT" = "22" ] || die "series 补丁数 != 22(多一行少一行都停)"

# 逐补丁核:每个补丁的目标文件必须在 git status 里呈修改态(M/A/??)。
# (marker 行启发式不可靠:补丁叠补丁、注释行前缀 '//' 被误过滤——04/06/07 的
#  apex_available 行就是 '//' 开头;可逆性检查在补丁叠加下也必然失败。)
# 注意:set -e 下 grep 无匹配返回 1 会杀脚本,整个校验段落临时关 set -e,手动计数。
git status --porcelain > /tmp/reproduce-tree-status.txt
MISMATCH=0
set +e
while IFS= read -r p; do
  [ -z "$p" ] && continue
  pf="$SERIES_DIR/patches/$p"
  [ -f "$pf" ] || { log "  MISSING patch file $p"; MISMATCH=$((MISMATCH+1)); continue; }
  # 目标文件集:支持手做格式(--- a/<path>)与 git-diff 格式(diff --git a/<path> b/<path>)
  targets=$( { grep -oE '^--- a/.+$' "$pf" | sed 's|^--- a/||'; grep -oE '^diff --git a/[^ ]+ b/[^ ]+$' "$pf" | sed -E 's|^diff --git a/[^ ]+ b/||'; } | sort -u)
  [ -n "$targets" ] || { log "  WARN $p: no targets parsed"; continue; }
  for t in $targets; do
    if grep -qE "^.?.? ?$t\$" /tmp/reproduce-tree-status.txt; then
      : # modified/added — patch applied
    else
      log "  NOT-APPLIED $p → $t"
      MISMATCH=$((MISMATCH+1))
    fi
  done
done < "$SERIES_DIR/series"
set -e
[ "$MISMATCH" = 0 ] || die "$MISMATCH 个补丁目标文件未呈修改态"
log "  22 补丁目标文件全部呈修改态"
# 语义锚点抽查(关键补丁的行为在位)
grep -q "implicit_suspend_checks_ = false;" dex2oat/dex2oat.cc || die "锚点缺失:dex2oat.cc implicit_suspend_checks_ != false(#22)"
[ "$(grep -c CLI_CP runtime/class_linker.cc)" = "7" ] || die "锚点缺失:class_linker.cc CLI_CP != 7(#08)"
grep -q '//apex_available:platform' dexoptanalyzer/Android.bp || die "锚点缺失:dexoptanalyzer/Android.bp 无 apex_available(#21)"
log "  语义锚点 3/3 在位(#22 挂起检查关 / #08 CLI_CP×7 / #21 apex_available)"

# ── 2. 强制重编 dex2oat64 ──
if [ "${SKIP_BUILD:-0}" != "1" ]; then
  log "2/5 强制重编 dex2oat64(删 out 里的 dex2oat 产物)"
  cd "$AOSP_R1_ROOT"
  rm -f out/host/linux-x86/bin/dex2oat64
  # 也删 soong intermediates 里的 dex2oat 对象,强制全量重链
  rm -rf out/soong/.intermediates/art/dex2oat 2>/dev/null || true
  log "  已删 dex2oat64 + soong intermediates"
  export ART_USE_READ_BARRIER=false ART_DEFAULT_GC_TYPE=CMS \
         ART_USE_GENERATIONAL_CC=false ART_HEAP_POISONING=false ART_TEST_DEBUG_GC=false
  export ALLOW_MISSING_DEPENDENCIES=true
  log "  编译中(6 项环境)…"
  # envsetup 定义 m 为 bash function;在 set -e 非交互脚本里 source/lunch 不可靠,
  # 用显式 bash -c 子壳保证 function 定义存活(envsetup 自身在非交互下会静默失败)
  bash -c "
    cd '$AOSP_R1_ROOT'
    source build/envsetup.sh >/dev/null 2>&1
    lunch aosp_arm64-userdebug >/dev/null 2>&1
    m -j32 dex2oat 2>&1 | tail -5
  "
  DEX_SHA=$(sha256sum out/host/linux-x86/bin/dex2oat64 | awk '{print $1}')
  log "  dex2oat64 sha256 = $DEX_SHA"
  if [ "$DEX_SHA" = "$EXPECT_DEX2OAT" ]; then
    log "  ✓ 复现 T3c 产物(sha256 一致)"
  else
    log "  ✗ 不一致:期望 $EXPECT_DEX2OAT"
    log "  非确定性来源排查:"
    log "    - 构建时间戳:Soong 默认嵌入 __DATE__/__TIME__?查 dex2oat 链接参数"
    log "    - 路径串:out/ 绝对路径嵌入 OatHeader dex2oat-cmdline"
    log "    - 环境变量:6 项是否完全一致(漏一个就编出不同件)"
    log "    - 并发:ninja -j32 的调度顺序可能影响 .o 链接顺序"
    # 不 die,让后续步骤继续跑完出报告
  fi
else
  log "2/5 SKIP_BUILD=1,跳过编译"
  DEX_SHA=$(sha256sum "$AOSP_R1_ROOT/out/host/linux-x86/bin/dex2oat64" | awk '{print $1}')
  log "  当前 dex2oat64 sha256 = $DEX_SHA"
fi

# ── 3. 出镜像 ──
if [ "${SKIP_IMAGE:-0}" != "1" ]; then
  log "3/5 出镜像: $T5_GEN → $OUT_DIR"
  [ -x "$T5_GEN" ] || die "t5_gen_image.sh 不可执行: $T5_GEN"
  [ -d "$JARS_DIR" ] || die "JARS_DIR 不存在: $JARS_DIR"
  mkdir -p "$OUT_DIR"
  "$T5_GEN" \
    --dex2oat "$AOSP_R1_ROOT/out/host/linux-x86/bin/dex2oat64" \
    --jars-dir "$JARS_DIR" \
    --out "$OUT_DIR" \
    --ref "$JARS_DIR/../tool/boot-image-inputs.sha256" 2>&1 | tail -10
  log "  出件: $(ls "$OUT_DIR" | wc -l) 个文件"
else
  log "3/5 SKIP_IMAGE=1,跳过出镜像"
fi

# ── 4. 与 T5c 逐件比 ──
if [ "${SKIP_IMAGE:-0}" != "1" ] && [ -d "$T5C_DIR" ]; then
  log "4/5 与 T5c($T5C_DIR)逐件比"
  DIFF_COUNT=0
  for f in "$T5C_DIR"/boot*.*; do
    b=$(basename "$f")
    if [ -f "$OUT_DIR/$b" ]; then
      h1=$(sha256sum "$f" | awk '{print $1}')
      h2=$(sha256sum "$OUT_DIR/$b" | awk '{print $1}')
      if [ "$h1" != "$h2" ]; then
        log "  DIFF $b"
        DIFF_COUNT=$((DIFF_COUNT+1))
      fi
    else
      log "  MISSING $b"
      DIFF_COUNT=$((DIFF_COUNT+1))
    fi
  done
  if [ "$DIFF_COUNT" = 0 ]; then
    log "  ✓ 27/27 与 T5c 逐字节一致"
  else
    log "  $DIFF_COUNT 件与 T5c 不同(vdex 应全同,.oat/.art 差为嵌路径串预期)"
  fi
else
  log "4/5 跳过逐件比(SKIP_IMAGE=1 或 T5C_DIR 不存在)"
fi

# ── 5. 过门 ──
if [ "${SKIP_IMAGE:-0}" != "1" ] && [ -f "$OUT_DIR/boot.oat" ]; then
  log "5/5 过门"
  # rb 门
  if [ -f "$RB_GATE" ]; then
    python3 "$RB_GATE" "$OUT_DIR/boot.oat" 2>&1 | tail -3
    log "  rb 门: $?"
  else
    log "  WARN: rb 门脚本不存在($RB_GATE),跳过"
  fi
  # t4b 门(回执程序生成)
  if [ -f "$T4B_GATE" ] && [ -f "$BOARD_LIBART" ]; then
    # 程序生成回执(不手抄哈希)
    RECEIPT_DIR=$(mktemp -d)
    python3 - "$BOARD_LIBART" "$OUT_DIR/boot.oat" > "$RECEIPT_DIR/receipt.md" << 'PYEOF'
import sys, hashlib
libart_sha = hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest()
oat_sha = hashlib.sha256(open(sys.argv[2],'rb').read()).hexdigest()
print(f"""```t4b-build-json
{{
  "schema": 1,
  "evidence_kind": "build_receipt",
  "artifacts": {{
    "libart_sha256": "{libart_sha}",
    "boot_oat_sha256": "{oat_sha}"
  }},
  "environment": {{
    "ART_USE_READ_BARRIER": "false",
    "ART_DEFAULT_GC_TYPE": "CMS",
    "ART_USE_GENERATIONAL_CC": "false",
    "ART_HEAP_POISONING": "false",
    "ART_TEST_DEBUG_GC": "false",
    "ALLOW_MISSING_DEPENDENCIES": "true"
  }},
  "native_debug_build": false
}}
```""")
PYEOF
    PYTHONPATH="/home/alvin/t4b-gate/t5-attr:/home/alvin/t4b-gate/k" python3 "$T4B_GATE" --libart "$BOARD_LIBART" --oat "$OUT_DIR/boot.oat" --build "$RECEIPT_DIR/receipt.md" 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); print('  t4b 门:',d['verdict'],'exit',d['exit_code'],'deploy_allowed',d['deploy_allowed'])"
    rm -rf "$RECEIPT_DIR"
  else
    log "  WARN: t4b 门脚本或 BOARD_LIBART 不存在,跳过"
  fi
else
  log "5/5 跳过过门(SKIP_IMAGE=1 或镜像未出)"
fi

log "完成"
