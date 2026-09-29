# tagsoup 墙 —— 定因与最小照抄法(Wikipedia 专线,20 分钟限时,交 cc-wiki)

证据:5ea run `20260930T004115-bd93cd69` wikipedia hilog L85759-85830(一手)+ v3a payload jar 逐个 dex 内扫描(一手)。

## ① route-A 空壳在哪(一手,dex 级)

`org/ccil/cowan/tagsoup` 出现在 **三个 jar 的 dex 里**(字符串级扫描):

| jar | dex | tagsoup 类 | 形态 |
|---|---|---|---|
| `framework.jar` | classes3.dex | 2(Parser/HTMLSchema) | **空壳**(`mainline-stubs/java/org/ccil/cowan/tagsoup/Parser.java` 9 行,`public Parser(){}`,注释明言"HelloWorld 不需要→空 stub") |
| `framework-classes.dex.jar` | classes3.dex | 2 | 同上(同一生成物) |
| `adapter-mainline-stubs.jar` | classes.dex | 2 | 同上 |

**BOOTCLASSPATH 顺序里 framework.jar 先于 oh-adapter-runtime.jar**(BCP 惯例:core→framework→ext;runtime jar 是后挂的 adapter 层)——所以即使 runtime jar 带完整 tagsoup,**BCP 首见即赢,空壳继续被解析**。Wikipedia 死点原文:`NoSuchMethodError: No virtual method setProperty(...)V in class Lorg/ccil/cowan/tagsoup/Parser;`,栈 `Html.fromHtml(Html.java:235) ← LanguageUtil.fromHtml ← ForYouCard`(`[W-ROOM-SURVIVE]` 吞不掉——不在容忍名单)。

## ② Westlake 的完整 tagsoup —— **不存在**

vm-copies/westlake-current 与 00.Workspace 的**全部 5 份拷贝都是同一个 9 行空壳**(scan_bcp_class_gap.py 自动生成);Westlake 树内没有任何完整 tagsoup 实现或 jar。Westlake 的 Wikipedia 跑通依赖的是它的 **Html.fromHtml 桩行为不同**(其 framework 桩不在 :235 触 tagsoup),不是它有真 tagsoup。**无可抄源。**

## ③ 最小照抄法(结论:改 runtime jar 不够,必须动空壳 jar;但有两条更优路)

- **方案 1(不引入 tagsoup,最小且最像 Westlake)**:改 `Html.fromHtml` 的桩/实现——首屏只需要**纯文本化**。Wikipedia 调 `fromHtml` 是为把 HTML 片段变可显示文本(LanguageUtil),不需要真 DOM。把 framework 桩里的 `fromHtml` 换成"剥标签返回纯文本"的 30 行实现(正则/状态机),tagsoup 根本不会被触碰。**改哪个**:framework.jar 里 Html 类(method 级 dex 替换)或 runtime jar 里同签名覆盖(Html 若在 runtime 可见优先级——需先验 Html 类的首见 jar)。**此为推荐**:风险最小、无 BCP 顺序问题(改的就是首见实现本身)。
- **方案 2(真 tagsoup,若 cc-wiki 需要完整解析)**:取上游 tagsoup 1.2.1(AOSP `external/tagsoup`,Maven central 也有)编译 class → **替换 framework.jar classes3.dex 里的空壳 Parser/HTMLSchema**(单文件 jar 替换,B9 风格:改 jar 不改代);**不能用 runtime jar 覆盖层**(②已证 BCP 首见在 framework.jar)。
- 方案 3(验证用):板上先 `unset`/重排 BCP 不可行(系统级),跳过。

## 可执行步骤(cc-wiki)

1. 确认 `android.text.Html` 的首见 jar(同法 dex 扫描,预计 framework.jar);若 Html 在 runtime jar 可覆盖,优先在 runtime jar 实现 `fromHtml` 纯文本化(方案 1 无侵入);
2. 否则单文件替换 framework.jar(方案 1 改 Html 或方案 2 换 tagsoup,均按 B9 单文件+回滚惯例);
3. 验证:Wikipedia 首屏后 `LanguageUtil.fromHtml` 不再出现在 UNCAUGHT 栈;`[W-ROOM-SURVIVE]` 只容忍非首屏线程。

## 诚实限界

- 未在板上实证 BCP 顺序(读 appspawn environ 的 tr 不可用),按 AOSP 惯例推断 framework.jar 先于 adapter jar——cc-wiki 上板第一步先验;
- 方案 1 的"纯文本化够用"基于 Wikipedia 首屏调用形态(LanguageUtil/ForYouCard 错误视图),若文章正文渲染也走 fromHtml 需要更强实现(方案 2);
- 30 分钟窗口内未编产物(方案 1 需先定 Html 首见 jar,是 cc-wiki 第 1 步)。
