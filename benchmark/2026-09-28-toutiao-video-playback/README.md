# Toutiao 视频不能播放 — 根因定位（2026-09-28，板 5cd1e3dd）

**现象**：feed 图文、封面、频道、底栏全部正常；点开任一视频卡 → 进入视频详情页
(`com.ss.android.ugc.detail.activity.TikTokActivity`)，但画面**停在封面帧不动**。

**结论**：解码不是瓶颈。卡在**视频二级 Surface 的缓冲呈现层**——桥接把 Android
`ReliableSurface`（ANativeWindow 的缓冲预留封装）stub 成空实现，同时 OH 渲染服务侧
这块 surface 的 BufferQueue `SetMetadata` 失败。解出来的帧没有可用的缓冲去提交，
视频 Surface 永远是空的。

## 证据链（全部在 5cd1e3dd 实测，tt pid 20465）

| # | 检查 | 结果 | 说明 |
|---|---|---|---|
| 1 | 点播放后隔 5s 各截一张，板上 `md5sum` | `687e7c86…` == `687e7c86…` | 画面一帧没动 = 没在播 |
| 2 | RT `lib/arm64-v8a/` 找解码库 | `libByteVC1_dec.so` `libbyteVC2dec.so` `libttmplayer.so` `libvcn.so` 都在 | 字节自研软解 + TTMPlayer 引擎，CPU 解码不依赖硬件 MediaCodec → **不是缺解码器** |
| 3 | app stderr grep MediaCodec/OMX/decoder | 0 条 | 没走 Android MediaCodec 路径（与 #2 一致：自带软解） |
| 4 | app stderr 统计 `stub` 函数 | `ReliableSurface::reserveNext returning OK` ×37265；`ReliableSurface::init no-op` ×27；构造 ×27 / 析构 ×23 | **二级 Surface 缓冲管线被 stub**：init 空实现、reserveNext 假装成功 |
| 5 | OH hilog（点播放后先 `hilog -r` 清 buffer） | `C01401/Bufferqueue: surface_buffer_impl.cpp:714 SetMetadata Failed with -5` ×280 | 渲染服务(pid 839)侧给该 surface 缓冲设元数据失败 |

截图：`feed-with-video-cards.jpeg`（财经频道，视频卡正常显示封面）、
`video-detail-frozen-on-cover.jpeg`（详情页停在封面帧）。

## 为什么图文正常、唯独视频不行

- **主窗口**走 EGL/GLES（`EglManager::swapBuffers` 正常，计数持续增长）——feed 的
  文字、图片、视频**封面**都画在这条已桥接好的路径上。
- **视频**用独立的二级 Surface（SurfaceView/TextureView + 自己的生产者/消费者
  BufferQueue）。这条路径 app 侧被 stub（#4）、OH 侧提交失败（#5）。

与 LocalSend/Flutter 首帧渲染 pc=0（Impeller GLES 扩展 proc 缺失）同属**图形层
二级/离屏 Surface 缺口**，见 `.octos/KNOWLEDGE-DIGEST.md` D补 LocalSend 条。

## 修法方向（未实施）

1. app 侧：把 `ReliableSurface`（dequeue/queue/reserveNext）真实现，后接 OH
   `OHNativeWindow`/`NativeBuffer` 的 BufferQueue。
2. OH 侧：查 `SetMetadata -5`——多半是桥接递交的 metadata key 不被 OH 支持，或
   生产者/消费者角色没对上。先从 `surface_buffer_impl.cpp:714` 的 key 着手。

量级：runtime 图形桥工程（nativewindow/surface 桥），非配置可解。

## 复现命令

```
SE=<RT>/private-tmp/adapter_child_<tt_pid>.stderr
BASE=$(hdc -t <key> shell "wc -l < $SE")
hdc -t <key> shell "hilog -r"
hdc -t <key> shell "uinput -T -c <x> <y>"          # 点视频卡播放键
hdc -t <key> shell "tail -n +$BASE $SE | grep -v TOUCH21-POLL | grep -iE 'surface|stub|egl'"
hdc -t <key> shell "hilog -x | grep -c 'SetMetadata Failed with -5'"
```

stderr 会被 `[TOUCH21-POLL]` 输入轮询刷到数十万行，**必须先记基线行再只看新增**，
否则媒体相关行被淹没。

## 演示建议

以图文 feed 为主，不点开视频播放。
