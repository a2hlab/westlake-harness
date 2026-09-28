#!/bin/bash
# task79 换装窗 runbook — liboh_android_runtime.so 合件 + oh-adapter-framework.jar 合件 一窗双闸
# 板 5ce24a78（或 failover 5ce2dcee）。纪律=备份双端独立 sha 预验 → mv-swap 新 inode → chcon → 644 → 一 reboot → 回执捕。
# 用法: 逐 PHASE 手动执行（set -e 不全局开，每步看输出再进）。TARGET 按板填。
# 验收回执形=sol-ultra 7ce39ef6 + cc6 闸收据规约。作者 cc5，2026-07-30。
#
# 【永入·cc6 坑账 r1.4】**runtime 换装 ⟹ daemon admission 钉必同窗更新**：appspawn-x.real .rodata 钉
#   runtime sha256+BuildID 各×2（Load/Verify 双函数 -D 宏注入族）。换装前：strings daemon 核旧钉计数；
#   换装时：等长 hex 补钉（64→64/40→40，零偏移漂移）或同管线重出件。漏此步=daemon exit(1)
#   "exact Android runtime admission failed"，startReg 永不执行。同查 jar 钉（strings 零命中再动刀）。
#   判活口径=pidof appspawn-x.real（shim spawn 后名）。label 坑：跨 fs mv=type_transition 落 label，
#   槽基线（含 appspawn_exec/system_lib_file 特例）须 mv 后原地 chcon 复刻。
#
# 【failover 5ce2dcee quirks（cc4 807028f1 在案）】
#   - daemon 启停**只走 /data/local/tmp/start-a13.sh**（禁 begetctl 直拉）；板钟不准→时序排序以 hilog seq 为准
#   - 活栈=/system/android；/system/android.newgen=staged 死树勿动
#   - 备份已预置（cc5 换板令窗）：backup-window/ 四宗（runtime a52ae9ca/jar 8d2e350f/桥 8ea5455a/libappms 7ce5397e）三向验毕
#
# 参数（窗时填）:
#   TARGET=hdc 目标串  CAND_SO=合件 so 本地路径  CAND_JAR=合件 jar 本地路径
#   GATE_SO_SHA=闸登记 sha  GATE_JAR_SHA=闸登记 sha

HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
T="${TARGET:-5ce24a7800000000000000000923012c}"
SO_SLOT=/system/android/lib64/liboh_android_runtime.so
JAR_SLOT=/system/android/framework/oh-adapter-framework.jar
BAK=/data/local/tmp/backup-window
CAP=/data/local/tmp/task79-window
EV=${EVDIR:-/tmp/task79-window-evidence}

h() { "$HDC" -t "$T" shell "$1"; }

phase0_precheck() { # 窗前核态：daemon/板态/工具目
  h "echo P0; pidof appspawn-x || echo DAEMON_DOWN; mount | grep ' / '; param get persist.sys.abilityms.timeout_unit_time_ratio; mkdir -p $BAK $CAP; ls $BAK"
}

phase1_backup() { # 双端备份+独立 sha 预验（分开命令，纪律）
  h "cp $SO_SLOT $BAK/liboh_android_runtime.preswap.bak; cp $JAR_SLOT $BAK/oh-adapter-framework.preswap.bak; echo CP_DONE"
  h "sha256sum $SO_SLOT $BAK/liboh_android_runtime.preswap.bak $JAR_SLOT $BAK/oh-adapter-framework.preswap.bak"
  mkdir -p "$EV/backup"; "$HDC" -t "$T" file recv "$BAK/liboh_android_runtime.preswap.bak" "$EV/backup/" && "$HDC" -t "$T" file recv "$BAK/oh-adapter-framework.preswap.bak" "$EV/backup/"
  shasum -a 256 "$EV/backup/"*.bak
  echo "目对: 上两 sha 四行须两两全合才准进 phase2"
}

phase2_candidate() { # 合件 sha 对闸账
  shasum -a 256 "$CAND_SO" "$CAND_JAR"
  echo "须逐字合闸登记: SO=$GATE_SO_SHA JAR=$GATE_JAR_SHA"
}

phase3_swap() { # remount rw → 推件到 tmp → mv-swap 新 inode → chcon → 644
  h "mount -o remount,rw / && echo RW_OK"
  "$HDC" -t "$T" file send "$CAND_SO" /data/local/tmp/swap-in.so && "$HDC" -t "$T" file send "$CAND_JAR" /data/local/tmp/swap-in.jar
  h "sha256sum /data/local/tmp/swap-in.so /data/local/tmp/swap-in.jar"   # 板端落件 sha 独立验
  h "chcon system_lib_file:s0 /data/local/tmp/swap-in.so; chcon system_file:s0 /data/local/tmp/swap-in.jar; chmod 644 /data/local/tmp/swap-in.so /data/local/tmp/swap-in.jar"
  h "mv /data/local/tmp/swap-in.so $SO_SLOT.swap && mv $SO_SLOT.swap $SO_SLOT && mv /data/local/tmp/swap-in.jar $JAR_SLOT.swap && mv $JAR_SLOT.swap $JAR_SLOT && echo SWAP_DONE"
  h "ls -laZ $SO_SLOT $JAR_SLOT; sha256sum $SO_SLOT $JAR_SLOT"           # 槽位 sha+label 终验
}

phase4_reboot() { h "reboot"; echo "等回连: watch hdc list targets"; }

# ==== r3 前门窗（libappms 路由补丁，cc6 ④-3 GO：c15bb1ba 直上，回滚件 7ce5397e 已在 backup-window）====
# 件源: cc4 抽件（5cd proven c15bb1ba）; 回滚件双端已备。daemon 启停走 start-a13.sh。
phaseR_swap() { # CAND_APPMS=本地 c15bb1ba 件路径
  h "mount -o remount,rw / && echo RW_OK"
  "$HDC" -t "$T" file send "$CAND_APPMS" /data/local/tmp/swap-appms.so
  h "sha256sum /data/local/tmp/swap-appms.so"   # 须=c15bb1ba 闸登记全 sha
  h "chcon system_lib_file:s0 /data/local/tmp/swap-appms.so; chmod 644 /data/local/tmp/swap-appms.so"
  h "mv /data/local/tmp/swap-appms.so /system/lib64/libappms.z.so.swap && mv /system/lib64/libappms.z.so.swap /system/lib64/libappms.z.so && echo APPMS_SWAP_DONE"
  h "ls -laZ /system/lib64/libappms.z.so; sha256sum /system/lib64/libappms.z.so"
}
phaseR_smoke() { # 冒烟=ability 路由（cc6 边界声明: 行为隐差当场见）; 起 daemon 发一 ability 看路由落点
  h "sh /data/local/tmp/start-a13.sh; sleep 3; pidof appspawn-x"
  echo "随后发 helloworld/目标 ability, hilog 看 AppSpawnX socket 路由（误路由=NWEBSPAWN 名=client 补丁缺席信号）"
}

phase5_state() { # reboot 后核态套（含常亮重放——不跨 reboot）
  h "echo P5; pidof appspawn-x || { rm /dev/unix/socket/AppSpawnX; begetctl start_service appspawn-x; sleep 2; pidof appspawn-x; }"
  h "mount | grep ' / '; param get persist.sys.abilityms.timeout_unit_time_ratio"
  h "power-shell timeout -o 2147483647 && echo KEEPAWAKE_REPLAYED"
  h "sha256sum $SO_SLOT $JAR_SLOT"  # 槽位件 reboot 后 sha 再验
}

phase6_capture() { # 回执捕：受控 daemon 重启全程留痕（同 boot_id 时序）
  h "begetctl stop_service appspawn-x 2>/dev/null; killall appspawn-x 2>/dev/null; sleep 1; rm -f /dev/unix/socket/AppSpawnX; echo CLEAN"
  h "nohup /system/bin/appspawn-x > $CAP/daemon-startup.log 2>&1 & echo DAEMON_MANUAL_STARTED"
  sleep 8; h "pidof appspawn-x"
  # 时序钉 grep（sol-ultra 清单）:
  h "grep -cE 'Runtime::Start|JNI_CreateJavaVM' $CAP/daemon-startup.log; grep -c 'JNI_OnLoad_icu' $CAP/daemon-startup.log; grep -E 'charset.*rc=0|Pattern.*rc=0|Matcher.*rc=0' $CAP/daemon-startup.log | head -5; grep -c 'fix86 REJECT.*PatternNative\|fix86 REJECT.*MatcherNative\|fix86 REJECT.*NativeConverter' $CAP/daemon-startup.log; grep -c 'WESTLAKE' $CAP/daemon-startup.log"
}

phase7_child() { # child 双探针（起 noice 后跑）: maps+comm+Build-ID 落账
  h "nohup sh /data/local/tmp/task66/r6-child-watch.sh \$(pidof appspawn-x) > /dev/null 2>&1 & echo WATCHER_UP"
  echo "随后触发 noice 启动; child 出现即: cat $CAP/child-tasks/*.comm; grep -E 'liboh_android_runtime|libicuuc|libicui18n' child maps 核路径"
}

phase8_pack() { # 证据打包回 Mac
  mkdir -p "$EV"
  for f in daemon-startup.log; do "$HDC" -t "$T" file recv "$CAP/$f" "$EV/"; done
  h "tar cf $CAP/child-tasks.tar -C $CAP child-tasks 2>/dev/null"; "$HDC" -t "$T" file recv "$CAP/child-tasks.tar" "$EV/"
  echo "补: README 判词 + git push（owner 队规）"
}

echo "runbook 载入。逐 phase 跑: phase0_precheck → phase1_backup → phase2_candidate → phase3_swap → phase4_reboot → phase5_state → phase6_capture → phase7_child → phase8_pack"
echo "当前: TARGET=$T"
