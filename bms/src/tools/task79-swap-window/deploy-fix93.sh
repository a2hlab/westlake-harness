#!/usr/bin/env bash
# deploy-fix93.sh — 板 5ce2dcee 的"一窗打完"脚本：
#   装 fix93 libart → 重起 daemon → 拉 Noice → 抓 child stderr → 拉回本地 → 直接出判词
#
# 为什么要这个脚本：板挂在 mac-server 上，入口（yue1 frp 6001）时通时断，
# 每个可用窗口可能只有几分钟。手敲十几条命令必然在窗口里手忙脚乱，
# 而且容易漏掉 sha 对账。这里把整个窗口固化成一条命令，每步都带对账，
# 任何一步对不上就停，不往下走。
#
# 用法：
#   bash src/tools/task79-swap-window/deploy-fix93.sh            # 全流程
#   bash src/tools/task79-swap-window/deploy-fix93.sh --check    # 只做入口/件预检，不碰板
#   bash src/tools/task79-swap-window/deploy-fix93.sh --nolaunch # 只换件，不拉 Noice
#
# 前置：/tmp/wl-fix93/libwestlake_art-fix93.so 在位（sha 见下）。
#   不在位就从编译机取：
#   scp compiler_root:/home/yao/westlake-local-build/task41-cardtable-align-20260727/\
#task13-base/build-ohos-arm64-r9/lib/libwestlake_art.so /tmp/wl-fix93/libwestlake_art-fix93.so
#
# 纪律（照 runbook.sh / wall8 口径）：
#   - libart 换件**不需要** repin daemon（daemon 只钉 liboh_android_runtime.so 的 sha+BuildID）
#   - daemon 启停**只走 /data/local/tmp/start-a13.sh**，禁 begetctl 直拉
#   - 换件前先备份现役件到板上 + 记 sha；对不上就停
#   - 板 5ce2dcee 禁止：wipe / flash / 替换 framework jar / 覆盖原 substrate / reboot
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MSB="$HERE/msboard.sh"
T="${TARGET:-5ce2dcee00000000000000000923012c}"

# 件优先取 ~/wl-artifacts（/tmp 会被清），取不到再退回 /tmp 的暂存
ART_LOCAL="${ART_LOCAL:-}"
if [ -z "$ART_LOCAL" ]; then
  for c in "$HOME/wl-artifacts/libwestlake_art-fix93.so" /tmp/wl-fix93/libwestlake_art-fix93.so; do
    [ -f "$c" ] && { ART_LOCAL="$c"; break; }
  done
  ART_LOCAL="${ART_LOCAL:-$HOME/wl-artifacts/libwestlake_art-fix93.so}"
fi
ART_SHA="${ART_SHA:-9a1ca27b1d5e9496baad529e20084724a5bb9371e8e71842cad4634db631965c}"
SLOT=/system/android/lib64/libart.so
STAGE=/data/local/tmp/wl-art-fix93.so
BAK_DIR=/data/local/tmp/wl-art-backup
CHILD_DIR=/data/service/el1/public/appspawnx
BN=com.github.ashutoshgngwr.noice
EV="${EV:-/tmp/wl-fix93-window}"

MODE="${1:-full}"
mkdir -p "$EV"

say() { printf '\n=== %s\n' "$*"; }
die() { printf '\n!!! 停：%s\n' "$*" >&2; exit 1; }
board() { bash "$MSB"; }   # 从 stdin 读板上脚本

# ---------------------------------------------------------------- 0 预检
say "0 入口 + 件预检"
for P in 6001 60022; do
  printf '  69.194.3.128:%s -> ' "$P"
  bash -c "exec 3<>/dev/tcp/69.194.3.128/$P 2>/dev/null || { echo 'TCP不通'; exit 0; }
           read -t 12 -u 3 L
           if [ -n \"\$L\" ]; then echo \"活（\$L）\"; else echo '通但无banner —— 后端 frpc 掉了'; fi"
done

[ -f "$ART_LOCAL" ] || die "件不在：$ART_LOCAL"
got=$(shasum -a 256 "$ART_LOCAL" | cut -d' ' -f1)
[ "$got" = "$ART_SHA" ] || die "件 sha 不对：$got != $ART_SHA"
echo "  件 OK：$ART_LOCAL ($ART_SHA)"
# 件里必须同时有 fix91/92/93 三条日志串（fix93 是累积件）
for k in fix91 fix92 fix93; do
  n=$(strings "$ART_LOCAL" | grep -c "\[$k\]")
  [ "$n" -ge 1 ] || die "件里找不到 [$k] 日志串——编错了？"
  printf '  件含 [%s] 串 ×%s\n' "$k" "$n"
done
[ "$MODE" = "--check" ] && { echo; echo "预检完，未碰板。"; exit 0; }

# ---------------------------------------------------------------- 1 板前核态 + 备份
say "1 板前核态 + 备份现役 libart"
board <<EOF > "$EV/p1.txt" 2>&1 || die "板不通（msboard 拨号失败）"
echo "daemon: \$(pidof appspawn-x.real 2>/dev/null || echo DOWN)"
echo "版本: \$(param get const.product.software.version 2>/dev/null)"
mkdir -p $BAK_DIR
echo "现役 slot:"; sha256sum $SLOT 2>&1
cur=\$(sha256sum $SLOT 2>/dev/null | cut -c1-8)
if [ -n "\$cur" ] && [ ! -f $BAK_DIR/libart.so.\$cur ]; then
  cp $SLOT $BAK_DIR/libart.so.\$cur && echo "备份 -> $BAK_DIR/libart.so.\$cur"
else
  echo "备份已存在（或读不到 slot）"
fi
ls -l $BAK_DIR 2>&1
EOF
cat "$EV/p1.txt"
grep -q "daemon: DOWN" "$EV/p1.txt" && echo "  注意：daemon 当前是 DOWN，换完件会拉起"
PRE_SHA=$(grep -oE '^[0-9a-f]{64}' "$EV/p1.txt" | head -1)
[ -n "$PRE_SHA" ] || die "读不到现役 slot 的 sha，先别动"
echo "  换件前 slot = $PRE_SHA"
[ "$PRE_SHA" = "$ART_SHA" ] && { echo "  已经是 fix93 了，跳过换件"; SKIP_SWAP=1; } || SKIP_SWAP=0

# ---------------------------------------------------------------- 2 传件 + 板端独立对账
if [ "$SKIP_SWAP" = 0 ]; then
  say "2 传件到板 + 板端 sha 独立对账"
  bash "$MSB" --push "$ART_LOCAL" "$STAGE" || die "传件失败"
  board <<EOF > "$EV/p2.txt" 2>&1
sha256sum $STAGE 2>&1
EOF
  cat "$EV/p2.txt"
  grep -q "$ART_SHA" "$EV/p2.txt" || die "板上落件 sha 对不上——传输截断，重传（别直接换件）"
  echo "  板端对账通过"

  # ------------------------------------------------------------ 3 换件
  say "3 换件（cp 覆盖 + 755 + system_lib_file 标签）"
  board <<EOF > "$EV/p3.txt" 2>&1
mount -o remount,rw / 2>&1 && echo RW_OK
cp $STAGE $SLOT && echo CP_OK
chmod 755 $SLOT && echo CHMOD_OK
chcon u:object_r:system_lib_file:s0 $SLOT 2>&1 && echo CHCON_OK
ls -laZ $SLOT 2>&1
sha256sum $SLOT 2>&1
EOF
  cat "$EV/p3.txt"
  grep -q "$ART_SHA" "$EV/p3.txt" || die "槽位 sha 不是 fix93——换件没生效"
  echo "  槽位对账通过"
fi

# ---------------------------------------------------------------- 4 重起 daemon
say "4 重起 daemon（只走 start-a13.sh）"
board <<EOF > "$EV/p4.txt" 2>&1
nohup sh /data/local/tmp/start-a13.sh >/data/local/tmp/wl-a13.log 2>&1 &
sleep 8
echo "daemon: \$(pidof appspawn-x.real 2>/dev/null || echo DOWN)"
tail -5 /data/local/tmp/wl-a13.log 2>&1
EOF
cat "$EV/p4.txt"
grep -q "daemon: DOWN" "$EV/p4.txt" && die "daemon 没起来，看 $EV/p4.txt 和板上 /data/local/tmp/wl-a13.log"

[ "$MODE" = "--nolaunch" ] && { echo; echo "换件完成，按要求不拉 Noice。"; exit 0; }

# ---------------------------------------------------------------- 5 拉 Noice
say "5 拉 Noice + 等 child"
board <<EOF > "$EV/p5.txt" 2>&1
touch /data/local/tmp/wl-mark
aa start -b $BN -m entry -a EntryAbility 2>&1 | head -3
sleep 25
echo "--- 本窗新出的 child stderr ---"
find $CHILD_DIR -name 'adapter_child_*.stderr' -newer /data/local/tmp/wl-mark 2>/dev/null
echo "--- 最新一个 ---"
ls -t $CHILD_DIR/adapter_child_*.stderr 2>/dev/null | head -1
EOF
cat "$EV/p5.txt"
CHILD=$(grep -oE "$CHILD_DIR/adapter_child_[0-9]+\.stderr" "$EV/p5.txt" | tail -1)
[ -n "$CHILD" ] || die "没抓到 child stderr —— child 可能压根没 spawn，看 $EV/p5.txt"
echo "  child 日志：$CHILD"

# ---------------------------------------------------------------- 6 取日志 + 判词
say "6 取日志回本地 + 判词"
LOCAL_LOG="$EV/$(basename "$CHILD")"
bash "$MSB" --pull "$CHILD" "$LOCAL_LOG" || die "取日志失败"
wc -l "$LOCAL_LOG"

echo
echo "---------------- 判词 ----------------"
printf '[fix93] 命中(HIT)      : %s\n' "$(grep -c '\[fix93\].*HIT'  "$LOCAL_LOG")"
printf '[fix93] 未命中(MISS)   : %s\n' "$(grep -c '\[fix93\].*MISS' "$LOCAL_LOG")"
printf '[fix92] 代理虚方法调用 : %s\n' "$(grep -c '\[fix92\] proxy call' "$LOCAL_LOG")"
printf '[fix91] 代理构造器     : %s\n' "$(grep -c '\[fix91\] proxy ctor' "$LOCAL_LOG")"
printf 'UnsatisfiedLinkError   : %s\n' "$(grep -c 'UnsatisfiedLinkError' "$LOCAL_LOG")"
printf 'providers populated    : %s\n' "$(grep -o 'providers populated: [0-9]*' "$LOCAL_LOG" | tail -1)"
echo
echo "— 最后 5 条异常/致命 —"
grep -nE 'Exception|FATAL|signal |abort|_exit' "$LOCAL_LOG" | tail -5
echo
echo "— 尾 15 行（新墙在这儿）—"
tail -15 "$LOCAL_LOG"
echo
echo "证据都在 $EV/"
