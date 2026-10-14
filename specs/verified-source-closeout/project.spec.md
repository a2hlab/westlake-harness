spec: project
name: "Close already validated implementation delivery"
---
## 约束
- 只收齐已验证实现的实际源码、补丁、构建入口与可追溯输入；不开发新API、不动设备。
- 保留历史冻结和签认；真实执行日志与失败均保留，不将源码存在等同历史产物精确复现。
- 默认发布分支是a2hlab/master；公开代码不得含凭据、大二进制或用户绝对路径。
- 内环使用隔离工作树；外环复验后合入并推送。重构建在a2hlab同一时刻仅一个，其他重构建用hw248。
