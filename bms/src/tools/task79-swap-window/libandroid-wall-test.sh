#!/bin/bash
# task79 hwui 墙 libandroid.so 实测脚本 —— 2026-07-31（已跑，结论回填）
#
# 【本窗结论：成立】板 5ce2dcee A/B/A 对照实证，软链接拆掉 ASurfaceControl_create 墙。
#   全账 var/evidence/task79-noice-lightup/libandroid-symlink-window-5ce2dcee/
#     A 基线 11624 无链 → ASurfaceControl 断言 ×2，死在 libhwui
#     B 测试 15150 有链 → 断言 ×0，推进到 Java 层 LoadedApk.makePaths NPE
#     A′对照 16855 撤链 → 断言 ×2 复现，死在 libhwui
#   新墙=makePaths NPE，根因 PackageManagerAdapter.nativeGetApplicationInfo 注册径
#   namespace 隔离（gate-baseline-r1.md:281-287 已定案），**与本窗无关，三跑全在**。
#
# 【落点定案】/system/android/lib64 —— 该目录确在 child 裸名 dlopen 搜索面内
#   （同目录 libhwui.so 被 runtime 裸名 dlopen 成功即证）。窗前 errno=2 是
#   ENOENT 文件不存在，不是路径不对。**不要**改 ld-musl-namespace ini，
#   **不要**放 /system/lib64/ndk（真 libandroid.so 带 16 枚 DT_NEEDED，多数只住 android 侧）。
#   软链接同 inode ⟹ musl 按 dev+ino 去重，命中已加载实例，无双实例。
#
# 【APerformanceHint 族】libhwui 20 枚致命断言里 6 枚该族全板零覆盖，窗前备了
#   `param set debug.hwui.use_hint_manager false`。**实测未用上**（B 跑零命中，
#   查找点在到达前已被新墙截停）。挂账备用，未验证。
#
# 【采集坑，必读】
#   - 板上 grep -a 对二进制**假阴性**（grep -ac nativeThemeCreate runtime.so → 0，
#     实为 1）。符号普查一律 hdc file recv 拉件后 `strings -a | grep -c`。
#   - 板钟不准 ⟹ ls -t 选不出最新 child。用 touch marker + find -newer。
#   - aa start 须全限定 ability 名，否则 10104001 ability does not exist。
#
# 【回滚】rm 软链接即可，一条命令。零换装、零覆盖。
# 【红线】板 5ce2dcee forbidden = wipe/flash/framework jar 替换/原 substrate 覆盖/**reboot**
#         daemon 启停只走 /data/local/tmp/start-a13.sh，禁 begetctl 直拉。
#         判活口径 = pidof appspawn-x.real（wrapper exec 后名，pidof appspawn-x 恒空）。

set -u
HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
T="${TARGET:-5ce2dcee00000000000000000923012c}"
SLOT=/system/android/lib64
PKG=com.github.ashutoshgngwr.noice
ABILITY=com.github.ashutoshgngwr.noice.activity.MainActivity
CHILD_DIR=/data/service/el1/public/appspawnx
MARK=/data/local/tmp/marker-libandroid-test

h() { "$HDC" -t "$T" shell "$1" 2>&1 | tr -d '\r'; }

p0_precheck() {   # 窗前核态
  h "param get const.ohos.fullname; echo DAEMON=\$(pidof appspawn-x.real)"
  h "ls -la $SLOT/libandroid.so 2>&1 | tail -1"
  h "grep -aE 'libhwui register' /data/local/tmp/appspawn-verifier-stderr.log | tail -1"
  echo "--- 期望: startReg 回执 = 'libhwui register: 50 ok / 1 fail'（B1 形）---"
}

_run() {          # 起一跑，回本窗新生 child 日志路径
  h "touch $MARK; aa start -b $PKG -a $ABILITY 2>&1 | head -1"
  sleep 30
  h "find $CHILD_DIR -name 'adapter_child_*.stderr' -newer $MARK 2>/dev/null"
}

_verdict() {      # $1=child 日志全路径
  local L="$1"
  h "echo size=\$(stat -c %s $L)
     echo -n 'ASurfaceControl断言: '; grep -ac ASurfaceControl $L
     echo -n 'APerformanceHint:    '; grep -ac APerformanceHint $L
     echo -n 'makePaths NPE:       '; grep -ac 'LoadedApk.makePaths' $L
     echo '--- 未解析 native ---'
     grep -aoE 'adapter\.[a-z]+\.[A-Za-z]+\.native[A-Za-z]+' $L | sort | uniq -c
     echo '--- 图形进度 ---'
     grep -aoE 'handleLaunchActivity|ThreadedRenderer|DecorView|Surface|Choreographer|eglCreateWindowSurface' $L | sort | uniq -c
     echo '--- 死点 ---'; tail -3 $L"
}

p1_baseline() { h "sh /data/local/tmp/start-a13.sh >/dev/null 2>&1"; sleep 5; _verdict "$(_run | tail -1)"; }

p2_apply() {      # 施加：软链接 + daemon 重起
  h "mount -o remount,rw / && echo RW_OK"
  h "ln -sf liboh_android_runtime.so $SLOT/libandroid.so && echo LINK_OK; ls -laZ $SLOT/libandroid.so"
  h "sh /data/local/tmp/start-a13.sh >/dev/null 2>&1"; sleep 5
  h "echo DAEMON=\$(pidof appspawn-x.real)"
}

p3_test() { _verdict "$(_run | tail -1)"; }

p4_rollback() {   # 回滚（仅需复现基线时用；软链接本身是净收益，常态保留）
  h "mount -o remount,rw / >/dev/null 2>&1; rm -f $SLOT/libandroid.so && echo LINK_REMOVED"
  h "sh /data/local/tmp/start-a13.sh >/dev/null 2>&1"; sleep 5
  h "echo DAEMON=\$(pidof appspawn-x.real)"
}

echo "载入完成。跑: p0_precheck → p1_baseline → p2_apply → p3_test （对照复现再 p4_rollback）"
echo "TARGET=$T  ABILITY=$ABILITY"
