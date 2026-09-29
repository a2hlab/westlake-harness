# libwestlake_html_compat.so — Html.fromHtml 单方法 JNI 转换(tagsoup 墙)

源:Westlake child_main.cpp L468-525(位修 fail-closed)、L905-917(ArtMethod 布局:declaring_class@0/access@+4/dex_method_index@+8/quick@+0x18,Android12+ ART=板 R155)、L536-593(开关+RegisterNatives)、L922-927(process_vm_readv 安全读)。

## 2026-09-30 外环三处修订(本版 sha16=26ac847bdec6552d)

1. **返回类型 Spanned**:native 签名 `(Ljava/lang/String;ILandroid/text/Html$ImageGetter;Landroid/text/Html$TagHandler;)Landroid/text/Spanned;`,4 参原样转发到替代类 `static android.text.Spanned fromHtmlCompat(String,int,ImageGetter,TagHandler)`;类/方法缺时 fallback=**new SpannedString(source)**(非原 jstring)。
2. **生效性核验+修补**(L468-560 语义的 image-backed 补全):RegisterNatives 后读回 quick@+0x18,与 `dlsym("art_quick_generic_jni_trampoline")`(符号存在性=Westlake art_runtime_stubs.cpp L384 弱桩注释放证)比对——相等=已生效只 log;**不等=原子写回 generic trampoline**(与 imageless Westlake 运行时转换的落点相同;树内无直接写 quick 的源码,此写法为其机制补全),写后回读验证;trampoline 取不到/读不了=只 log 不动。两路 before/after 全打。
3. 日志统一 `[HTML-COMPAT]`(18 处),验证观察点=fromHtmlCompat 被调次数。

## 用法(cc-wiki)

`WESTLAKE_HTML_COMPAT=1` + `WESTLAKE_HTML_COMPAT_CLASS=<替代类全名>`(cc-t3 出 `fromHtmlCompat` 实现,照 Westlake 不触 tagsoup 的 Html 桩)→ System.load 本 .so。默认关;全失败只 log。host 自测:位修五检(./host_test)。
