#!/bin/bash
# #66 启动捕获一条龙（fix83/IMSE 件 + GLES 供件落地后一键执行）
# 用法: bash genshin-launch-capture.sh [genshin|vitalslayer|both|godot] [帧数=90]
# 产出: /tmp/task48-5ce/task66-launch/{gl,vs,gd1..4}_*.jpeg + {genshin,vitalslayer,godot-l*}-launch.mp4
# 双路依据: Cindy 8095e839「IMSE 落地后 原神/VitalSlayer 双路试，哪个先亮屏报哪个」
# godot 模式: #76 cc1 四级梯（com.westlake.godotladder.l1-4，ability=bm dump 现解 isLauncherAbility，
#             兜底 org.godotengine.godot.GodotAppLauncher）；锁屏即 OnPause——唤醒步本脚本本有
set -u
HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
BOARD=5ce24a7800000000000000000923012c
MODE=${1:-both}
FRAMES=${2:-90}
OUT=/tmp/task48-5ce/task66-launch
mkdir -p "$OUT"

# 双路 bundle/ability（VitalSlayer launcher ability 板上实证 bm dump:
# isLauncherAbility=true = UnityPlayerGameActivity，UnityPlayerActivity 非 launcher）
GS_B=com.miHoYo.Yuanshen;      GS_A=com.miHoYo.GetMobileInfo.MainActivity
VS_B=org.P8QS.QSCrawler;       VS_A=com.unity3d.player.UnityPlayerGameActivity

# 0) 板钟对时（TLS 需要；取 mac 当前时间）
NOW=$(date +"%m%d%H%M%Y.%S")
$HDC -t $BOARD shell "date $NOW; echo clock-set:; date"

# 1) 布防 hilog 持久捕获 + 清观察位
$HDC -t $BOARD shell "rm -f /data/local/tmp/task66-launch-hilog.txt; mkdir -p /data/local/tmp/task66; rm -f /data/local/tmp/task66/gl_*.jpeg /data/local/tmp/task66/vs_*.jpeg /data/local/tmp/task66/gd*.jpeg; nohup hilog > /data/local/tmp/task66-launch-hilog.txt 2>&1 & echo armed-\$!; ls /data/log/faultlog/temp/ | wc -l"

# 2) 解锁回桌面（视频开场 = 桌面）
$HDC -t $BOARD shell "power-shell wakeup; power-shell display -s 255; sleep 1; uinput -T -d 600 1600 -u 600 400; sleep 1; uinput -K -d 1 -u 1; sleep 2"

run_one() {  # $1=tag(gl|vs|gd1..4) $2=bundle $3=ability $4=frames
  local tag=$1 bundle=$2 ability=$3 n=$4
  echo "== aa start $bundle / $ability =="
  $HDC -t $BOARD shell "aa start -b $bundle -a $ability 2>&1 | head -3"
  $HDC -t $BOARD shell "for i in \$(seq -w 1 $n); do power-shell wakeup; snapshot_display -f /data/local/tmp/task66/${tag}_\$i.jpeg >/dev/null 2>&1; sleep 1; done; ls /data/local/tmp/task66/${tag}_*.jpeg | wc -l"
  # 回桌面再进下一路
  $HDC -t $BOARD shell "uinput -K -d 1 -u 1; sleep 2"
}

resolve_ability() {  # $1=bundle → stdout=launcher ability（bm dump 现解，兜底=aapt 实解的 alias 名）
  local b=$1 a
  a=$($HDC -t $BOARD shell "bm dump -b $b 2>/dev/null | grep -B40 'isLauncherAbility = true' | grep 'name =' | tail -1 | sed 's/.*name = //;s/\r//g'" | tr -d '\r')
  if [ -z "$a" ]; then a=com.godot.game.GodotAppLauncher; fi   # alias→targetActivity com.godot.game.GodotApp（四包 manifest 同构实证）
  echo "$a"
}

run_godot() {  # 四级梯 L1→L4 逐级（同包族 com.westlake.godotladder.l1-4）
  local lv b a
  for lv in 1 2 3 4; do
    b=com.westlake.godotladder.l$lv
    a=$(resolve_ability "$b")
    echo "== godot L$lv: $b / $a =="
    run_one gd$lv "$b" "$a" "$FRAMES"
  done
}

case "$MODE" in
  genshin)     run_one gl "$GS_B" "$GS_A" "$FRAMES" ;;
  vitalslayer) run_one vs "$VS_B" "$VS_A" "$FRAMES" ;;
  both)        run_one gl "$GS_B" "$GS_A" "$FRAMES"; run_one vs "$VS_B" "$VS_A" "$FRAMES" ;;
  godot)       run_godot ;;
  *) echo "bad mode: $MODE"; exit 1 ;;
esac

# 3) 回捞
for f in $($HDC -t $BOARD shell "ls /data/local/tmp/task66/*.jpeg" | tr -d '\r'); do
  base=$(basename "$f")
  [ -f "$OUT/$base" ] || $HDC -t $BOARD file recv "$f" "$OUT/$base" >/dev/null 2>&1
done

# 4) 拼 mp4（每路各一）
python3 - "$OUT" <<'PY'
import sys, os, glob, imageio.v2 as imageio
out = sys.argv[1]
pairs = [('gl', 'genshin'), ('vs', 'vitalslayer')] + [(f'gd{i}', f'godot-l{i}') for i in range(1, 5)]
for tag, name in pairs:
    files = sorted(glob.glob(os.path.join(out, f'{tag}_*.jpeg')))
    if not files: continue
    frames = [imageio.imread(f) for f in files]
    mp4 = os.path.join(out, f'{name}-launch.mp4')
    w = imageio.get_writer(mp4, fps=3, codec='libx264', quality=7,
                           pixelformat='yuv420p', macro_block_size=None)
    for f in frames: w.append_data(f)
    w.close()
    print(name, 'frames:', len(frames), '-> mp4:', os.path.getsize(mp4), 'bytes')
PY
echo "DONE: $OUT"
