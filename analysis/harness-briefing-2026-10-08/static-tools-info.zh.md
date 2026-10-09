# 静态分析底层工具：各能拿到什么信息

配套对外介绍第 6、7 页。分工：解析文件格式交给下面这些业界标准工具，我们自己的脚本只管「问什么、怎么判」。
「我们怎么用」一栏以仓库源码为准(`scripts/lab/`、`harness/westlake_gap/`、各 `benchmark/` 专项)。

## 一、Android SDK

| 工具 | 能拿到的信息 | 我们怎么用 |
|---|---|---|
| **dexdump**(build-tools) | DEX 文件头与校验和;每个类的类名、父类、接口、访问标志;字段和方法签名;方法的字节码反汇编(`-d`):每条指令、调用了哪个方法、读写了哪个字段 | `deployed_class_diff`:新 JAR 和板上那份比类集合，查有没有类被删或被改;`generation_static_checks`:生成件检查;专项里查「谁调用了这个方法」(如 bitmap-colorspace 的首个致命调用点) |
| **aapt2**(build-tools) | `dump badging`:包名、版本、minSdk/targetSdk、权限、启动 Activity、图标、uses-library;`dump resources`:资源表，每个资源 ID 在各配置(语言、分辨率、夜间)下的取值，style 的父类和属性;`dump xmltree`:二进制 XML(清单、布局)解成树 | 专项：主题扫描(哪个 style 缺属性)、自适应图标栅格化(图标名对应哪个 res 文件) |
| **apkanalyzer**(cmdline-tools) | APK 文件和大小;清单;DEX 包、类、方法数和引用;单个方法反编译成字节码;资源和配置 | 专项：读某个方法的具体代码(如 libretube 的 `onCreate`、bitmap-colorspace 的调用点) |

## 二、LLVM(Homebrew LLVM 22)

| 工具 | 能拿到的信息 | 我们怎么用 |
|---|---|---|
| **llvm-objdump** | 机器码反汇编(arm64),每条指令和它的地址;重定位(谁调用了哪个外部函数、`dlopen` 的参数从哪来);节表;动态符号表 | `open_site_scan`:逐个 PC 找出每个 `dlopen`/`dlopen_ns` 调用点及其 (namespace、路径、flags);`abi_diff`:新旧 .so 的调用图;`westlake-apk-gap`:把未解析的 native 导入归到触达它的 JNI 方法;REA 测试里扫数据地址被谁写 |
| **llvm-readelf** | ELF 头、架构;程序头(段、权限);节;动态段:`DT_NEEDED`(依赖哪些库)、`SONAME`、`RUNPATH`;符号版本;notes 里的 build-id | `native_predeploy` / `native_needed_gate`:部署前查依赖库是否都在、能不能解析;`deployed_strings_diff`:配合 strings 比新旧 .so |
| **llvm-nm** | 符号表：哪些函数和变量是本库定义的、哪些是要从外部拿的(undefined);符号类型和地址 | `abi_diff`:新旧 .so 导出函数增删;`open_site_scan`:符号定位 |
| c++filt | 把 C++ 修饰名还原成可读的函数签名 | `abi_diff`:导出函数比对时显示可读签名 |
| strings | 二进制里的可打印字符串(路径、日志文案、类名) | `deployed_strings_diff`:新旧 .so 的字符串增删(比如某个库路径有没有被删掉) |

## 三、smali / baksmali(2.5.2)

| 工具 | 能拿到的信息 | 我们怎么用 |
|---|---|---|
| **baksmali** | DEX 反汇编成 smali 文本：每个方法的完整指令、寄存器、常量、`invoke-*` 调用目标、字段读写、try/catch 范围 | `null_producer`:顺着寄存器追，判断空指针来自框架返回值还是应用自己的代码 |
| **smali** | 反向：把 smali 文本汇编回 DEX | 补丁流水线：改框架 JAR 里的某个方法后重新打回 DEX |

## 四、Python 库

| 工具 | 能拿到的信息 | 我们怎么用 |
|---|---|---|
| **androguard** | 解析 APK:二进制清单(包名、组件、权限、intent-filter、uses-library)、签名、所有 DEX;对 DEX 做全局分析：类、方法、交叉引用(谁调用谁)、方法内的调用和字段访问 | `westlake-apk-gap`:全语料缺口扫描的主力。每个 APK 引用了哪些框架类和方法、调了哪些 `getSystemService`、清单声明了什么 |
| **pyelftools** | 在 Python 里解析 ELF:节、动态段、`DT_NEEDED`、动态符号、重定位、只读数据 | `westlake-apk-gap`:APK 里每个 .so 依赖哪些库、导入哪些符号;native 代码通过 JNI 反调 Java 时用的类名、方法名(`FindClass`/`Get*ID` 的字符串参数) |

## 五、其他

| 工具 | 能拿到的信息 | 我们怎么用 |
|---|---|---|
| **oatdump**(构建机上，从 AOSP 14 源码编) | boot image 和 oat 文件的内容：编译了哪些方法、每个方法的机器码入口、镜像里的类和对象、记录的 dex 校验和 | G2 门禁：新烘焙的镜像和已知能用的那版逐个方法比编译入口 |
| **REA + Hopper**(新接入) | native 库反编译成伪代码;函数的调用者和被调用者;字符串被哪里引用 | 辅助判断 native 崩溃点。2026-10-09 已知答案测试纠正了 localsend 崩溃点的错误归因;它给出的结论仍要回到原始指令上核一遍,数据地址的交叉引用仍靠 llvm-objdump |

## 六、这些信息最后汇成什么:westlake-apk-gap 的缺口类别

全语料扫描(`static_pipeline` 调 `westlake-apk-gap` 的 `scan` → `oh-resolve` → `gap-map`)把上面的原始信息归成以下类别，每行都带证据和可信度:

| 类别 | 从哪些信息推出 |
|---|---|
| Java 框架 API | APK 的 DEX 引用 − 我们 boot jar 里有的,按 API 级别过滤 |
| 系统服务 | `getSystemService` 的名字 → AOSP 里谁提供 → Westlake 有没有 → 对应 OH 子系统 |
| 密钥与加密 | 代码选用的 JCA provider 名 → 运行时装了哪些 → OH HUKS |
| 包管理与清单 | 清单 features、PackageManager 调用 → Westlake 的包管理语义 |
| Activity、窗口、进程 | 原本由 system_server 回答、现在由 Westlake 进程内回答的接口 |
| 窗口与 Surface | 首屏怎么渲染、需不需要独立 Surface → OH 窗口模型 |
| 运行时数据 | 结果依赖运行时数据的调用(时区、ICU)→ 运行时加载了什么 |
| 框架 native | 应用用到的平台类 → 它们的 native 方法 → 运行时从哪个库注册 |
| native 反调 Java | .so 里 `FindClass`/`Get*ID` 的名字 → boot jar 里有没有 |
| native 平台符号 | .so 的导入符号 → OH 加上我们打包的 NDK 能不能提供 |
| native 加载与打包 | 库怎么打包 → OH 链接器能不能映射 |
| 进程沙箱与策略 | 代码要创建的对象 → OH SELinux 允不允许 |
| 外部服务与 SDK | 依赖 Google 服务或探测设备的 SDK |

**注意**:这些都是「引用了」,不是「运行时一定会走到」。静态计数只是上界(例：某符号 50 个应用导入，实际因它失败的只有 2 个),排序以实测的首个致命错误为准。
