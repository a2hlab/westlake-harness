spec: project
name: "Genshin bounded offline intake"
satisfies: [REQ-GENSHIN-STATIC]
---

## 意图
只建立原神现有合法输入及静态兼容性证据，为后续是否值得安排独立任务提供依据；不承诺可启动、可登录或可玩。

## 约束
- 所有设备保持，尤其61b；禁止ADB/HDC、设备读写、锁窗、部署、重启、登录、下载、运行APK或其代码、修改运行时及冻结项。
- 只读现有文件与仓内记录；不绕过签名、授权或安全机制。未获合法来源依据的包不得进入分析，来源状态保留unknown。
- 原始命令、rc、stdout/stderr与输入SHA存持久私有目录；公开仓库只提交脱敏小证据和路径别名，不提交APK、资产、凭据或个人信息。
- 静态导入、Unity或图形符号存在不等于实际provider、namespace、首致命点或运行通过；头条与BoatAttack证据不得冒充原神实测。单app线索不触发API冻结。
- 本轮只有t1可派发；无输入可明确MISSING收口，不创建虚假t2或自动推进设备任务，不推送。

## 已定决策
- 由现有cc-video执行包定位和普通静态读取，不调用REA；需要精确二进制分析时列出对象SHA/问题交外环另派Codex或octoscode，不在t1无限扩展。
- 第一次执行最多15分钟，优先已有包索引与已验证BoatAttack源码/构建/观察记录；到界限输出已得证据、缺项和最小下一动作。
