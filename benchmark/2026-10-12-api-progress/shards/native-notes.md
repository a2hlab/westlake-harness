# Native API 能力分片：证据范围与限制

## 检查点与计数
- 172 行能力组（NATIVE-001..NATIVE-172）、46 个实际来源 SHA；不是独立 API 数、完成率或点亮率。
- 历史 NDK 25 库/API33 的 4449 符号：OH 2613、Westlake 117、missing 1719；另一 source-build profile 为 OH 2613、Westlake 307、missing 1529。主表38组只列代表成员，完整4449由外环CSV附录承载。导出供应未知功能，不标 implemented。
- ac59/source4d5 JNI census：reported 325 方法、160 条原声明；解析302名称形成76个类/返回行为组。压缩声明与表级数量不是同一分母；原表未解析Trace行保留 unclassified。
- 后续46能力组与12个 AMedia 行补全；AMedia原21个status接口保持 NATIVE-123，另12行拆 NULL/无样本/释放/回调容器/真实Format int32 等行为。50个Unity实际导入全覆盖；AMediaFormat_new是额外实现，不混作第51个实际导入。
- 实现状态计数：missing=23 / unknown=18 / stub=81 / partial=22 / implemented=28。状态按列出的能力，不等于完整 Android 子系统。

## 两条路线不能混并
r84/r86/r87/r88/r89 是独立 source-build/host profile，不能视为 U13 部署件。
r86 的 Surface.lockCanvas 后期实现单列 NATIVE-142；ac59 返回0导致 fd-plus 的未锁Canvas异常仍留在历史桩行。两者不同代际，不是互相否定。
r87 input 是永不到app的空queue shim，aaaaxy载库后仍缺glGenVertexArrays；随后GLESv2句柄转OH GLESv3才绘图。不能将该GL成果算为NativeActivity真实输入。
r88 PPSSPP/STK默认路由成功与U14 PPSSPP dlext非零flags仍拒是不同profile；r89 usp GL/HWUI抢同一个surface仍未修。

## 真实实现、兼容降级与缺口
- SQLite：U13 18763dd4真实TU/注册表，Boat adc125f4是旧libandroid的49字节改件错别名到runtime，四SQLite registrar弱return0。静态注册不保证当前winner、可开文件或CANTOPEN已修。Boat五触摸/LAP不能验证数据库。
- AMedia：8fc0752d的Format新建/int32读写/链表释放、DataSource callback holder是真实小容器；Extractor仅未配置容器。Codec/Image接口有类型返回unsupported=-10002/NULL/无样本，没移植Stagefright。不得将50接口全称真实解码，也不能全称空桩。
- OpenSLES：宽度/IID/连续队列原语有离线测试；OH05d8 PLAY callback返回12，真实completion与route-A media owner注册未完成。上游ledger不作本route点亮凭证。
- Bionic：ctype原表/locale数字转换/cleanup真实转接与版本节点、app namespace、relocation scope分行；名称存在不等于所有app能解析。dlext没有后端时非零flags拒绝，PPSSPP不伪报修复。
- 图形：M1/M5/M6/U16 Flutter resolver按具体runtime/bridge/private槽记录；候选静态变化不推当前三板状态。Bitmap ColorSpace native真实注册但源值null，Java修补属于Java分片。

## APK证据与版本
所有历史绘图/播放/过墙描述用 reported；候选闭包/UND/表差用 static。未重看截图，没有新增 t20_ui/functional 签认。
逐APK保留正反例：Discord解死锁且OsmAnd带shim反而abort；CNN statvfs后draw；Emacs fts载库仍首Activity失败；Material Files 6/6对照；USP四次surface竞争；MuseKit授权后可监听。没有逐API APK A/B的r86 Canvas/Process/socket/collation/hint行明确无该归因，不能借311drawing总数代填。
Android源码tag/API level/APK targetSdk/Android对照版本/OH实际版本/ABI是不同字段。无直接钉值保持 unknown，未知ABI不由目录名称推AArch64；AMedia ABI由明确构建回执钉LP64。
source_location给源码/注册摘录或报告指针及产物谱系；只有短SHA的旧报告不伪造完整SHA。主树实存来源用相对路径；本树独有Boat接班摘要用 $WORKSPACES/westlake-harness-bms/ 路径加SHA。

## 未归类与边界
unclassified保留原Trace压缩声明、source-build尚缺TU/完整产物同源回执、已读图形构造器/代理注册器材料、abort/properties未拆能力成员。不新增范围、不穷尽新扫描。注册器代理整体调用保留自身初始化，不能一概称漏gOffsets；静态构造器存在也不证明所有输入成功。
本轮只写native.json、本说明、native-landing-paths.txt。零板/VM/远程/运行时构建/冻结或门表修改；不push，不修改其它树。
使用主树 atlas.validate_rows 做生产schema与SHA校验及错SHA/缺字段负向检查；check_user_paths与land.py --preflight输出贴黑板。api_progress_native selector由外环落入主树后运行，本轮不冒报Rust选择器/lifecycle已过。
