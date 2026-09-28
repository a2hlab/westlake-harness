#!/bin/bash
# 板 5ce2dcee 直通器（走 mac-server 本地 hdc，不再拿 28 MB 挤本地端口转发）。
#
# 为什么不用 board.sh 那条路：
#   board.sh 把 mac-server 的 hdc server 端口 8710 转发到本地 18710，然后本地 hdc 直连。
#   传小命令没问题，传 28 MB 的 libart 会在转发上断，实测传完 sha 不对（截断）。
#   改成：文件先 rsync 到 mac-server（断点续传），再由 mac-server 上的 hdc 本地发板——
#   本地链路 1.4 秒传完 28 MB，且不受 6001 抖动影响。
#
# 坑（2026-07-31 踩过）：`ssh -S sock host` 在 sock 失效时会**静默退回默认 22 端口**，
#   而 69.194.3.128:22 是 yue1，绝对不能碰。所以这里一律先 `ssh -O check`，
#   不通就重拨，且每条命令都显式带 -p 6001。
#
# 用法:
#   msboard.sh <<'EOF'          # stdin 收板上脚本
#     grep -an X /path/log | tail -5
#   EOF
#   msboard.sh --push <本地文件> <板上路径>    # 传文件（本地→mac-server→板）
#   msboard.sh --pull <板上路径> <本地文件>    # 取文件
set -u
T="${TARGET:-5ce2dcee00000000000000000923012c}"
SOCK=/tmp/wl-ms.sock
MS=mac-server@69.194.3.128
PORT=6001
HDC=/Users/mac-server/.slock/agents/4e6cde49-8cd5-4f2e-8acd-df407cb585b5/tools/sdk-extract/toolchains/hdc

ensure_master() {
  ssh -O check -S "$SOCK" -p $PORT "$MS" >/dev/null 2>&1 && return 0
  rm -f "$SOCK"
  SSHPASS=$(security find-generic-password -s macserver_ssh_password -w) \
  sshpass -e ssh -M -S "$SOCK" -fN \
    -o StrictHostKeyChecking=no -o PreferredAuthentications=password \
    -o NumberOfPasswordPrompts=1 -o ConnectTimeout=25 \
    -o ServerAliveInterval=20 -o ServerAliveCountMax=6 \
    -p $PORT "$MS" 2>/dev/null || return 1
  ssh -O check -S "$SOCK" -p $PORT "$MS" >/dev/null 2>&1
}

ensure_master || { echo "FATAL: mac-server(6001) 连不上" >&2; exit 91; }

msh() { ssh -S "$SOCK" -p $PORT "$MS" "$@"; }

case "${1:-}" in
  --push)
    rsync -e "ssh -S $SOCK -p $PORT" --partial --append-verify --inplace "$2" "$MS:/tmp/" || exit 92
    msh "$HDC -s 127.0.0.1:8710 -t $T file send /tmp/$(basename "$2") '$3'" 2>&1 | tr -d '\r' | tail -1
    ;;
  --pull)
    msh "$HDC -s 127.0.0.1:8710 -t $T file recv '$2' /tmp/$(basename "$3")" >/dev/null 2>&1
    rsync -e "ssh -S $SOCK -p $PORT" "$MS:/tmp/$(basename "$3")" "$3" || exit 93
    ls -l "$3"
    ;;
  *)
    TMP=$(mktemp /tmp/wl-msb.XXXXXX.sh)
    cat > "$TMP"
    rsync -e "ssh -S $SOCK -p $PORT" -q "$TMP" "$MS:/tmp/wl-msb-cmd.sh" || exit 94
    msh "$HDC -s 127.0.0.1:8710 -t $T file send /tmp/wl-msb-cmd.sh /data/local/tmp/wl-cmd.sh >/dev/null 2>&1
         $HDC -s 127.0.0.1:8710 -t $T shell sh /data/local/tmp/wl-cmd.sh" 2>&1 | tr -d '\r'
    rm -f "$TMP"
    ;;
esac
