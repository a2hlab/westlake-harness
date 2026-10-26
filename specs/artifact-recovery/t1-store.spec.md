spec: task
name: Immutable artifact store and clean restore
satisfies: [REQ-ARTIFACT-RECOVERY]
---
## 意图
提供一个Python标准库CLI，从声明的输入归档内容寻址对象，并从独立存储恢复完整清单到新目录。错误输入不能污染已发布版本或覆盖已有工作文件。
## 已定决策
- scripts/lab/artifact_store.py，命令 ingest --manifest --source-root --store、verify --manifest --store、restore --manifest --store --dest；均输出JSON与明确退出码。
- schema=westlake-artifact-release/v1；release_id为安全标识；files每项path相对安全路径、sha256完整小写64hex、size非负、mode整数权限、role。其余provenance/build_status等元数据原样保存。
- store对象位置objects/sha256/<前2位>/<完整hash>；releases/<release_id>.json只在全部对象哈希通过后原子不可覆盖发布；同字节重入允许，异内容拒绝。
- ingest只读source-root下普通文件，拒symlink/穿越/重复路径/父子冲突/非法mode；流式校验及临时文件原子发布；并发发布同SHA不得覆盖异内容，已有坏对象报错不悄悄修。
- restore先验证完整清单和全部对象，dest必须不存在（父目录允许）；同级临时目录完成后原子发布，复制而非硬链接，失败不留下看似完成的dest。verify拒缺文件、size/hash不符或不安全路径。
- CLI不执行构建或部署；远程传输先通过原有SSH/rsync拉取到独立store，再调用verify/restore。外层负责远程收据，工具不自建服务器。
## 边界
### 允许修改
- scripts/lab/artifact_store.py
- scripts/lab/tests/test_artifact_store.py
- tools/spec-checks/tests/artifact_recovery.rs
### 禁止
- 删除原件、改设备、改其他工具、网络上传、依赖外部Python包
## 验收标准
场景: 无原worktree恢复
  测试: artifact_store_contract
  假设输入已归档且源目录被改名而消费端只有manifest和独立store
  当恢复到不存在的新目录
  那么所有文件hash和mode符合清单且修改恢复文件不改变store
场景: 损坏与缺失拒绝
  测试: artifact_store_contract
  假设任一对象缺失或内容损坏或size错误
  当执行verify和restore
  那么退出非零且目标目录不存在
场景: 路径与覆盖拒绝
  测试: artifact_store_contract
  假设输入含穿越或symlink或重复路径或目标已存在
  当归档或恢复
  那么退出非零且已有文件与已发布清单字节不变
场景: 不可变发布与中断
  测试: artifact_store_contract
  假设同release_id不同清单或中途源对象校验失败
  当归档
  那么拒绝覆盖且不发布不完整release
## 排除范围
设备安装、全源构建、自动清理、网页、远程认证配置。
