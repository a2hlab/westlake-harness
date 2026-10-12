# Java/API 分片：来源与交件口径

写入树：westlake-harness-t0；只写本分片三个文件。零板/VM/远程/运行时构建；master只读。原有arsc_resolver.cpp修改未动。

共120个知识能力组、67个catalog来源、65个行内SHA来源；不是独立API总数、Android SDK穷举或当前部署支持率。

## 判读与版本

- implemented只描述窄能力，例如值对象/上游callback；partial有受限路径，stub默认/no-op/unsupported，missing绑定历史generation，unknown缺足够证据。
- Java类型存在、非空manager、BCP可link、host ART单测都不能替代真实OH功能。
- JAVA-019是AES/GCM进程自检支撑工具，非API修复，不计新增能力或点亮增益。
- JAVA-001是FZ-007完整TagSoup替代前的T7c历史行，关联REG-007；不能当现态缺口。旧U9 NSD/蓝牙与U15类型候选只关联，不改成服务已支持。
- r84/r86/r87/r88/r89是另一source-build/host路线，不套U13现态或demo128。drawing/听音均reported，没在本轮目视。
- Android源码、API level、targetSdk、Android设备对照、OH测试分别写；host ART不是Android参考机，unknown不扩兼容范围；平台context由外环集中写。

## 状态（不是点亮数）

- implemented: 6
- partial: 59
- stub: 29
- missing: 17
- unknown: 9

## 已覆盖

- U6 api-repairs和member/source摘录；U9实际部署服务清单优先于旧source snapshot。
- B7/user/nativeLibraryDir/alias/XML-only icon；B89网络声明、后台启动ACL/APL、launcher、arsc bitmap/adaptive图标与libinstalls校验。
- U11–U15 Provider发布/authority、Settings call、GCM失败及v3、WebView typed stubs/PrivateAccess/NWeb候选、主题覆写顺序与生命周期时序。
- net members按类列DEX精确签名，NSD值对象/接口/unsupported分行，BLEcallback与旧BCP缺类分行。
- r84–r89的task-root、own service/broadcast/Intent、memory/label/quota、global config/onPostCreate/focus/resume、runtime permission/CEunlock、serial拒绝/LauncherApps/profile、microphone/timezone、VPN未授权、legacy keypair/platform android包。

## 关键历史结果的诚实边界

- cclauncher枚举成功且first frame drawn，但透明windowShowWallpaper仍只见host；clauncher白色clock/hints在light host上不显，r88黑host才显、wallpaper仍缺。
- NewPipe/Retro Music是platform android包NameNotFound消失、媒体服务起来；不等于所有音视频功能通过。
- socks5/blockads的VPN异常消失或drawing不等于隧道建立/转发。
- MuseKit报告host MICROPHONE授予后调音器可见且能听音；仍保留reported，非本轮测试。

## 缺口与未分类

- JAVA-110 Android15 CEunlock精确method未找到，保留unknown而非凭记忆填。
- README-only source-build变化缺完整源码TU/产物SHA receipt；不伪造同源关系。
- 多数条目缺per-API targetSdk/Android设备对照/OH完整ROM/ABI，不能当通用版本矩阵。
- 当前部署及最终类加载/JNI绑定winner没有本轮核验；325条native-stub表由native shard负责，不重复当Java实现数。
- unclassified保留input-only与native-only边界；只覆盖列出的来源族，没把未读benchmark当全部已穷尽。

## 离线检查原样输出

```
production atlas.validate_rows(java.rows): PASS rows=120 unique_hashed_row_sources=65
KNOWN_ANSWER wrong SHA: REJECT (expected)
KNOWN_ANSWER missing required field: REJECT (expected)
source catalog SHA: PASS 67; IDs JAVA-001..JAVA-120 unique; historical UI stays reported
```

Rust api_progress_java固定读master/shards/java.json；本轮不拷到master，直接用同一生产validate_rows对本树真实120行及SHA核验。外环落库后可跑Rust/agent-spec lifecycle，本轮不声称该selector已通过。

## 交件

- java.json：顶层rows/sources/coverage_notes/unclassified。
- java-notes.md：本说明。
- java-landing-paths.txt：仅这三件，外环代落；不push。

交件预检原样：

```
preflight OK: 3 files, 0 too large, 0 user-path hit(s), 0 data file(s) with home paths
```
