#!/bin/bash
# 板 5ce2dcee 直通器（本地 hdc 版）。
#
# 路由：本机 hdc -s 127.0.0.1:18710
#        └─ ssh -L 18710 → mac-server:8710（hdc server）
#             └─ ssh -L 16013 → alexyLinux(69.194.3.128:60022) → 192.168.8.13:22
#      绕开 69.194.3.128:6001（那条 ssh 端口一被高频重试就限流，实测半小时不恢复）。
#      隧道由 ensure_tunnels() 自愈，掉了自动重建。
#
# 用法:  board.sh <<'EOF'
#          grep -anE "A|B" /path/log | tail -5
#        EOF
# stdin 收一段脚本 -> base64 -> hdc file send -> hdc shell sh，零引号嵌套
# （板上 hdc shell 里嵌套引号会把 hdc 挂死，实测卡满 300s）。
# 板是 toybox+musl，脚本以 sh 跑。
set -u
T="${TARGET:-5ce2dcee00000000000000000923012c}"
HS="-s 127.0.0.1:18710"

probe() { bash -c "exec 3<>/dev/tcp/127.0.0.1/$1 && head -1 <&3" 2>/dev/null; }

hdc_up() { hdc $HS list targets 2>/dev/null | grep -q .; }

# 起 18710 -> mac-server:8710 的转发。$1 = 到 mac-server 的 ssh 端口，$2 = 主机。
dial_macserver() {
  pkill -f "18710:127.0.0.1:8710" 2>/dev/null
  SSHPASS=$(security find-generic-password -s macserver_ssh_password -w) \
  sshpass -e ssh -f -N -o StrictHostKeyChecking=no -o PreferredAuthentications=password \
    -o ConnectTimeout=25 -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 \
    -L 18710:127.0.0.1:8710 -p "$1" "mac-server@$2" || return 1
  sleep 3
  hdc_up
}

# [2026-07-31] 原来只认「经 alexyLinux(60022) 跳板」这一条路，alexyLinux 一挂就整个
# 报 FATAL，哪怕 6001 是通的。改成三段式：已通就不动 → 先试直连 6001 → 再试跳板。
# 6001 的限流是真的（见文件头注释），所以把它排在跳板之前但**只试一次**，不重试。
ensure_tunnels() {
  hdc_up && return 0

  dial_macserver 6001 69.194.3.128 && return 0
  echo "  [tunnel] 6001 直连没成，改试 alexyLinux 跳板" >&2

  if ! probe 16013 | grep -q SSH; then
    SSHPASS=$(security find-generic-password -s alexylinux_ssh_password -w) \
    sshpass -e ssh -f -N -o StrictHostKeyChecking=no -o PreferredAuthentications=password \
      -o ConnectTimeout=25 -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 \
      -L 16013:192.168.8.13:22 -p 60022 alexyang@69.194.3.128 || return 1
    sleep 3
  fi
  dial_macserver 16013 127.0.0.1
}

ensure_tunnels || { echo "FATAL: 隧道建不起来" >&2; exit 91; }

TMP=$(mktemp /tmp/wl-board-cmd.XXXXXX.sh)
cat > "$TMP"
hdc $HS -t "$T" file send "$TMP" /data/local/tmp/wl-board-cmd.sh >/dev/null 2>&1
hdc $HS -t "$T" shell sh /data/local/tmp/wl-board-cmd.sh 2>&1 | tr -d '\r'
rm -f "$TMP"
