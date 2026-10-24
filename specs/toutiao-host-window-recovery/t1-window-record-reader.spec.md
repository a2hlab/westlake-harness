spec: task
name: "Native host window record reader"
inherits: project
satisfies: [REQ-TTHOST]
tags: [native, window, recovery]
---
## 意图
实现后续native窗口重关联实际调用的有界只读记录入口，从现有宿主window-state.json提取候选父窗口ID。普通记录是候选信息，不能代替SSM窗口归属核验或实机读取验收；本任务不执行重关联。
## 已定决策
- 新文件放在独立候选目录，不编辑已绑定或冻结源；C++接口提供path、expected UID/GID输入，返回typed status与候选windowId及文件身份，不内置用户工作区绝对路径。
- 复用可取得并固定SHA的JSON解析器，完整解析单个JSON对象，拒绝重复键、尾部垃圾、过深嵌套；不得用正则或搜索id字符串代替JSON解析。
- 文件至多8192字节、JSON深度至多16；open使用NOFOLLOW和NONBLOCK，拒绝symlink、非regular、错误owner/GID和world可写文件；实采同UID/GID的0660文件允许；不执行文件内容、不发IPC、不修改文件。
- 同一次读核前后dev/inode/size/mtime与当前路径身份；截断、替换或短读返回unavailable/drift，不发布半截记录。不能宣称检出采样间完全恢复的内容改写。
- 仅接受window-ready/details.id或stage-event/details.window.id，id为1..2147483647的整数；不接受bool/string/fraction。foreground/background及不含id的正常事件返回unavailable，绝不清除已有绑定。
- 成功只返回candidate，不返回authenticated/attached；同UID与root可读不证明现役child可读。检测周期、SSM调用和渲染恢复由后继任务承担。
- Candidate保留来源事件类别与可选的整数stage event，不将hidden记录混成visible；stage-event缺少event时仍是候选但状态unknown。下游据SDK的SHOWN=1/ACTIVE=2、INACTIVE=3/HIDDEN=4区分，reader不自行执行窗口动作。
- 测试运行生产C++ reader，覆盖真实本地文件、symlink和FIFO拒绝；不调用设备、SSH、REA、编译生产bridge或修改控制配置。
## 边界
### 允许修改
- benchmark/2026-10-24-native-host-window-recovery/record-reader/**
- tools/spec-checks/tests/host_window_record_reader.rs
### 禁止
- 现役或冻结源码、Java/JAR/HAP、设备操作、进程信号、停止的控制器/执行器/配置、REA和推送。
## 验收标准
场景: 两种实际宿主记录
  测试: host_window_record_reader_fixtures
  假设真实本地同UID/GID的0660 regular文件分别含window-ready/details.id32和stage-event/details.window.id62
  当生产C++ reader读取完整记录
  那么分别返回candidate32和candidate62与文件身份且不写输入文件
  并且分别保留window-ready类别和stage-event类别及其event值或unknown
场景: 正常事件暂不含窗口
  测试: host_window_record_reader_fixtures
  假设记录是foreground或background或缺少id
  当reader读取
  那么返回unavailable且没有清除现有关联的动作
场景: 非法JSON与非法ID
  测试: host_window_record_reader_fixtures
  假设输入含重复id键或尾部垃圾或截断JSON或id为0负数布尔小数字符串超int32
  当reader解析
  那么拒绝并不产生candidate
场景: 文件边界和漂移
  测试: host_window_record_reader_fixtures
  假设输入为symlink或FIFO或owner/GID错误或world可写或超过8192字节或前后身份漂移
  当reader执行实际文件入口及生产元数据判据
  那么有界拒绝且不读FIFO阻塞不修改文件不发命令
场景: 合法输出不升级权限或窗口结论
  测试: host_window_record_reader_fixtures
  假设输入是合法窗口62记录
  当reader成功返回
  那么结果仍为candidate且没有SSM认证或已关联字段
## 排除范围
现役child实际读权限、窗口身份认证、检测线程、SSM会话创建、完整白屏修复与封板；后继任务必须完成这些范围，不能以本任务通过结束主目标。
