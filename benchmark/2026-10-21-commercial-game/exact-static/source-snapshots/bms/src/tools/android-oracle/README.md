# Android oracle / task #70 golden-reference capture

Cindy 捕获清单落地（设备未到机时的即插即用骨架）。

## 捕获清单对照

| # | 项 | 脚本行为 |
|---|---|---|
| 1 | 原神冷启→下载页：strace + logcat + screenrecord | `capture-genshin-golden.sh` |
| 2 | 类初始化扣 Zygote preload | 人工对照 `/system/etc/preloaded-classes`（设备到手拉取） |
| 3 | 先定性 root；无 root 则 strace 跳过，保留 logcat+screen | `meta/device.txt` 记 `root_ok=` |
| 4 | 事件五元组 `(seq,pid,tid,name,effect)` | `parse-events.py` → `events/*.csv`（时间戳只排序） |

## 用法

```bash
export ADB=/tmp/task70-android/platform-tools/adb   # or brew platform-tools
export ANDROID_SERIAL=<serial>                      # optional
export OUTDIR=/tmp/task70-android/run-$(date +%Y%m%d-%H%M%S)
export PKG=com.miHoYo.Yuanshen
bash src/tools/android-oracle/capture-genshin-golden.sh
python3 src/tools/android-oracle/parse-events.py \
  --logcat "$OUTDIR/logcat/all.txt" \
  --strace "$OUTDIR/strace/strace.txt" \
  --outdir "$OUTDIR/events"
```

## 阻塞

mac-server：`adb devices` 空。等 owner 告知插口机位或 `adb connect host:port`。

产出喂给：#68（dlopen 闭包）、fix83 TLV 差分（epoll/eventfd）、#66 逐屏基线（screenrecord）。
