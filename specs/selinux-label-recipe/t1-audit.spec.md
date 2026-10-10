spec: task
name: "Read-only recursive label audit"
inherits: project
---

## 意图

按部署 target 清单递归读取 SELinux 标签，逐路径报告期望和实际值。

## 已定决策

- 配方放知识表并钉出处 SHA 和行号，不从文件名猜进程权限。
- appspawn-x 精确匹配 appspawn_exec；Android lib64、route 和 boot image 使用 system_lib_file。
- 采集失败、标签缺失、危险路径、未知清单格式均不得输出 PASS。

## 验收标准

场景: Canonical labels pass without board writes
  测试: selinux_label_recipe
  假设 A mocked plan contains the Android tree and init entry targets
  当 The audit reads recursive ls labels
  那么 It reports every path and uses only read-only shell commands

场景: Both observed label walls fail explicitly
  测试: selinux_label_recipe
  假设 The init entry has system_file or a mapped Android library has data_local_tmp
  当 The audit compares the captured labels to the recipe
  那么 It fails and prints each path expected label and actual label

场景: Incomplete evidence cannot pass
  测试: selinux_label_recipe
  假设 A read fails or a target is absent ambiguous or unsafe
  当 The collector validates the plan and readback
  那么 It refuses without attempting chcon or daemon start
