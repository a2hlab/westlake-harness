# 仅替换 Adapter 的反证实验——无效

## 原计划回答的问题

只把已部署 adapter 从基线
`7db99e1b760cf843b1a99db1382a3299f189c8cbca786ec411b7c35a2af6ffb9`
改为候选
`84695d62f515cfec6bb317c959ec55b1d5085bf82303f792a764cf549a22267a`
能否让执行越过缺失的 AbilityStage 回执？

APK、appspawn、child、provider、runtime、runtime JAR 和原始 Unity 库均有意保持不变。

## 实际结果

实验没有进入生命周期代码。封印 provider 在加载 runtime 之前拒绝了混代组合：

```text
exact adapter bridge admission failed before runtime load
WLCGATE:LSP:FAIL_PROVIDER
```

OH 随后报告 `Start Process Specified Ability TimeOut!`，但这只是子进程退出后宿主给出的超时分类，不能证明 `AddAbilityStageDone` 或 `ScheduleAcceptWantDone` 曾经执行。

## 可以成立的结论

- generation 隔离生效，阻止了跨代次 `.so` 混用。
- 该实验不能用于证明生命周期因果关系。
- 下一项直接反证必须重新构建或部署同代次的 adapter/provider/child/appspawn 闭包；不能只覆盖一个 `.so`。
- 临时 bind 已经卸载，设备 adapter 已确认恢复到基线哈希 `7db99e1b...ffb9`。
