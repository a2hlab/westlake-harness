#!/bin/bash
# start_container_build_on_gz05.sh
# 在 GZ05 上用 Docker 容器 + tmux 启动编译
# 编译输出到 GZ02:/data/adapter (via NFS /mnt/gz02_nfs)
#
# 用法：
#   ssh -p 58222 AlexYang@1.95.175.212 "bash /data/adapter/build/start_container_build_on_gz05.sh"
#
# tmux 跟踪：
#   ssh -p 58222 AlexYang@1.95.175.212 "tmux attach -t adapter_build"

set -e

# ============================================================
# 配置
# ============================================================

ADAPTER_ROOT="/data/adapter"  # GZ05 本地路径
ADAPTER_OUT="/mnt/gz02_nfs/adapter/out"  # GZ02 NFS 挂载点
BUILD_LOG="$ADAPTER_OUT/build_$(date +%Y%m%d_%H%M%S).log"
TMUX_SESSION="adapter_build"
BUILD_MODE="${1:-both}"  # arm, arm64, or both

# ============================================================
# 前置检查
# ============================================================

echo "[$(date)] 检查环境..."

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装"
    exit 1
fi

# 检查 NFS 挂载
if ! mountpoint -q /mnt/gz02_nfs; then
    echo "❌ NFS 挂载点 /mnt/gz02_nfs 不可用"
    exit 1
fi

# 检查 tmux
if ! command -v tmux &> /dev/null; then
    echo "⚠️  tmux 未安装，尝试安装..."
    apt-get update && apt-get install -y tmux || {
        echo "❌ 无法安装 tmux"
        exit 1
    }
fi

echo "✅ 环境检查完成"

# ============================================================
# 清理旧的 tmux session（如果存在）
# ============================================================

if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    echo "[$(date)] 杀死旧 tmux session: $TMUX_SESSION"
    tmux kill-session -t "$TMUX_SESSION"
fi

# ============================================================
# 创建编译脚本（在容器内运行）
# ============================================================

CONTAINER_BUILD_SCRIPT="/tmp/run_build_in_container.sh"

cat > "$CONTAINER_BUILD_SCRIPT" << 'SCRIPT_EOF'
#!/bin/bash
# 容器内运行的编译脚本

set -e

export OH_ROOT=/oh
export AOSP_ROOT=/aosp
export ADAPTER_ROOT=/adapter
export ADAPTER_OUT=/adapter/out
BUILD_MODE=${1:-both}

cd $ADAPTER_ROOT

echo "[$(date)] 容器内编译开始"
echo "  OH_ROOT: $OH_ROOT"
echo "  AOSP_ROOT: $AOSP_ROOT"
echo "  ADAPTER_ROOT: $ADAPTER_ROOT"
echo "  BUILD_MODE: $BUILD_MODE"
echo ""

# 运行统一编译脚本
bash build/build_universal_arm_arm64.sh "$BUILD_MODE"

echo "[$(date)] 容器内编译完成"
echo "  输出目录: $ADAPTER_OUT"
ls -lh $ADAPTER_OUT/

SCRIPT_EOF

chmod +x "$CONTAINER_BUILD_SCRIPT"

# ============================================================
# 创建 tmux session 并启动编译
# ============================================================

echo "[$(date)] 创建 tmux session: $TMUX_SESSION"

# 新建 session
tmux new-session -d -s "$TMUX_SESSION" -x 200 -y 50

# 在 session 内执行编译
tmux send-keys -t "$TMUX_SESSION" "cd $ADAPTER_ROOT && \
docker run \
  --rm \
  --name adapter_build_container \
  -v $ADAPTER_ROOT:/adapter \
  -v /home/aosp:/aosp \
  -v /home/oh:/oh \
  -v $ADAPTER_OUT:/adapter/out \
  -e BUILD_MODE=$BUILD_MODE \
  -e TERM=xterm-256color \
  ubuntu:22.04 \
  bash $CONTAINER_BUILD_SCRIPT $BUILD_MODE 2>&1 | tee $BUILD_LOG" Enter

# ============================================================
# 显示 tmux 接入命令
# ============================================================

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║ 编译已启动！"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "📊 监控编译进展："
echo ""
echo "   tmux attach -t $TMUX_SESSION"
echo ""
echo "   或在 SSH 中运行："
echo "   ssh -p 58222 AlexYang@1.95.175.212 'tmux attach -t $TMUX_SESSION'"
echo ""
echo "📝 日志位置："
echo "   - 实时日志：$BUILD_LOG"
echo "   - GZ02 位置：/data/10.AlexProject/adapter/out/build_*.log"
echo ""
echo "📦 编译输出："
echo "   - GZ05 本地：$ADAPTER_ROOT/out/"
echo "   - GZ02 NFS：$ADAPTER_OUT/"
echo ""
echo "⏱️  预计编译时间："
echo "   - arm 仅：2-3 小时"
echo "   - arm64 仅：2-3 小时"
echo "   - 两者：4-5 小时"
echo ""
echo "🔌 断线重连："
echo "   tmux attach -t $TMUX_SESSION"
echo ""
echo "🛑 停止编译："
echo "   tmux kill-session -t $TMUX_SESSION"
echo ""

# ============================================================
# 显示实时日志
# ============================================================

echo ""
echo "=== 实时日志（按 Ctrl+C 退出，编译继续后台运行）==="
echo ""

sleep 2
tail -f "$BUILD_LOG" 2>/dev/null || echo "等待日志文件生成..."

