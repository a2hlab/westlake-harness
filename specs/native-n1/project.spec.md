spec: project
name: "N1 native cluster batch"
---

## 意图

在统一 U0 上交付一版覆盖当前 native 死因簇的候选，保留冻结 API，通过短窗单变量验收后交 U1 三板全量。

## 约束

- 源码按 Mac、OrbStack、hw248 顺序查找，优先复用验证过的 Westlake 实现。
- FZ-001/002 产物及 FZ-003 源文件不变，构建与出版前检查冻结登记。
- 只在授权且持锁的板上写入，短窗验收后回统一态并释放锁。
- 截图终判由外环负责，facts 原样报告；不以进程存活代替点亮。
