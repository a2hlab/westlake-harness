spec: project
name: "Ordinary launch increment evidence"
---
## 意图
离线准备61b普通日志增量观察器，仅记录日志可见区间和进程身份，不推断请求接收时间。
## 约束
- 本轮只实现与本地合成验证，不调用设备；后续运行须由外环显式选择execute。
- 不启动停止应用，不向设备进程发信号，不读取控制实现或env，不使用REA，不修改既有冻结文件。
