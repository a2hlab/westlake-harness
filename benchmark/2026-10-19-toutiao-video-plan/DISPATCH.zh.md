# 视频 t1 即时派单卡

角色：视频内环静态调查；与图标重开内环并行，不占板、不改主任务文件。
契约：`specs/toutiao-video-playback/t1-static-evidence.spec.md`。
允许写：`benchmark/2026-10-19-toutiao-video-playback/static/**`；契约修改先由外环复核。
输入：本目录 source-index.json + 外环提供的当前 serial/boot/APK/runtime 只读身份。没有当前身份时先完成静态源/调用路径，报告缺口不阻塞并行任务。
动作：区分下载/服务、软硬解选择、SurfaceView/TextureView及ANW输出、音频路由、暂停/恢复/退出；源/部署件按namespace和消费者绑定。搜索本地→a2hlab→hw248，优先已验证来源。不要从MediaPlayer stub推断头条使用MediaPlayer，不从缺MediaCodec日志推断必定软件解码，不从ReliableSurface日志推断其就是视频surface。
交件：prediction.json、路径/来源表、首致命点证据或最小观察请求、selected-change.json（仅确认根因后）、SHA及所需实验判据/退路。首致命点unknown或external不得交伪造修复清单。
验收：`ttvideo_static_receipt`真实回执绑定 + 外环human复核；commit到analysis分支，不push。无设备操作权限，本轮不争61b锁。
后续：t2收到首致命点和精确文件清单才开建；t3空闲板先验，成功后与图标任务合流61b。
