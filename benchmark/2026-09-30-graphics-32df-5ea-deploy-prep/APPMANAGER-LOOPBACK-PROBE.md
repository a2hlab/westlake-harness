# AppManager『正在验证』回环 connect 探针(cc-wiki #80,offline prep)

## 目标
证/否 AppManager hang 的平台差异结论(NEXTWALL-TRIAGE-…json ③):OH 回环 TCP connect 到
**无监听的闭合端口**是否**不快速返回 ECONNREFUSED**(而是挂住),导致 `Ops.connectAdb` 永久阻塞、
到不了 `fallbackToNoRoot` → SplashActivity 卡『正在验证』。真 Android 对照(参考机允许)预期即时 ECONNREFUSED。

## 探针(两种,先 nc 一行,不行再上小程序)

### 快路:nc 一行(若 OH toybox 有 nc)
```
# step0 查有无 nc:
hdc -t <serial> shell "which nc toybox; toybox 2>/dev/null | tr ' ' '\n' | grep -x nc"
# 有则(-w 超时 2s;记是立即返回 refused 还是等满 2s):
hdc -t <serial> shell "T0=\$(date +%s%N); nc -v -w2 127.0.0.1 59999; echo rc=\$?; T1=\$(date +%s%N); echo ms=\$(((T1-T0)/1000000))"
```
判据:立即(<100ms)`Connection refused` = 快拒;等满 ~2s 超时无 refused = 挂(平台差异)。

### 稳路:loopback_probe(自写,blocking connect 无超时 + 10s 看门狗)
见 loopback_probe.c。编译并推送:
```
# 编译(OH clang arm64):
$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang --target=aarch64-linux-ohos -static -O2 \
    loopback_probe.c -o loopback_probe
hdc -t <serial> file send loopback_probe /data/local/tmp/loopback_probe
hdc -t <serial> shell "chmod +x /data/local/tmp/loopback_probe; /data/local/tmp/loopback_probe 59999"
# 端口 59999 应无监听;也测 5555(adb 口,若板上无 adbd 亦闭合)。
```
输出解读(程序自带判词):
- `ECONNREFUSED in <100 ms -> FAST-REFUSE` → **不是挂**(我的结论错,需重审 AppManager)。
- `connect still BLOCKED after 10s -> HANG` → **确认平台差异挂**(OH 回环闭合端口不发即时 RST)。
- `connect SUCCEEDED` → 该端口有监听,换一个确无监听的端口重测。

## 真 Android 对照(参考机)
同一 loopback_probe(NDK 编 aarch64-linux-android)或 `nc -w2 127.0.0.1 59999`,预期 **ECONNREFUSED <100ms**。
只装测试小程序/probe,不动头条与用户数据。

## 判据汇总表
| 环境 | connect 到闭合回环端口 | 结论 |
|---|---|---|
| 真 Android(参考机) | ECONNREFUSED 即时(<100ms) | 基线:内核 RST 快拒 |
| OH 板 | 若 ECONNREFUSED 即时 | 平台差异**不成立** → AppManager hang 另有因,重审 |
| OH 板 | 若挂住/等满超时无 refused | 平台差异**成立** → OH 回环不快拒;修向 cx-t0(回环闭合端口发 RST / 或给有界 connect 超时) |

## 退路
- OH 无 nc 且推 probe 受阻(SELinux/权限)→ 用 `hdc shell` 起一个 `python`(若有)做 socket 测;都不行则
  以 AppManager 自身行为佐证(已观测:线程静默、永卡『正在验证』= 挂签名),标 confidence=observed-inferred。
- 不深挖(外环定调):判出挂/快拒即出一行结论给 cx-t0,不追内核 netstack 实现。

## 归属
结果一行写黑板给 cx-t0(平台/网络层)。若确认挂:cx-t0 让 OH 回环对闭合端口快拒(RST),或在适配层给
ADB connect 有界超时兜底(app 收失败→fallbackToNoRoot→MainActivity 点亮)。
