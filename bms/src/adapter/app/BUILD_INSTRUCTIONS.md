# Hello World APK 本地编译指南

## 当前 canonical host gate（2026-07-14）

唯一受支持的工作区内构建命令是：

```bash
cd /opt/21.Game/02.unity.cardwords/adapter
bash build/inner/build_helloworld_apk.sh
```

该入口只读取本 adapter 的 `app/` 源码/资源；Android SDK/JBR 仅作为已安装
toolchain 使用，不下载依赖。成功产物及完整 provenance 固定写入 `out/app/`：

- `hello2.apk`
- `BUILD_RECEIPT.md`
- `PRODUCT_INPUTS.sha256`
- `TOOLCHAIN.tsv`
- `ARTIFACTS.sha256`

下方 Windows/Android Studio/ECS 步骤仅为历史人工说明，不是当前构建 gate，也
不得用来替代上述 receipt。

本指南用于在本机 (Windows) 通过 Android Studio 编译 `hello2.apk`,然后部署到 OpenHarmony DAYU200 设备。

## 前置条件

- 本机已安装 Android Studio (任意版本,推荐 2023.x 或更新)
- 有 JDK 17+ (Android Studio 自带)
- (可选) 本机有 ADB 工具用于调试

**APK 与适配层完全无关**,可以用任何标准 Android SDK 编译。这是项目的核心约束 — 详见 `CLAUDE.md` "APK 透明适配原则"。

## 步骤 1: 在 Android Studio 中创建项目

1. Android Studio → **New Project** → **Empty Activity** (Java)
2. 配置:
   - **Name**: `hello2`
   - **Package**: `com.example.hello2`
   - **Save location**: `D:\code\adapter\app_studio\` (或任意路径)
   - **Language**: **Java** (不要选 Kotlin)
   - **Minimum SDK**: **API 21 (Android 5.0)**
   - **Build configuration language**: Groovy DSL (build.gradle)
3. 点击 **Finish**

## 步骤 2: 替换源代码

把 `D:\code\adapter\app\java\com\example\helloworld\` 下的 4 个 .java 文件复制到新项目的 `app\src\main\java\com\example\helloworld\`,**覆盖** Android Studio 自动生成的 MainActivity.java:

```
HelloWorldApplication.java
HelloService.java
MainActivity.java
SecondActivity.java
```

## 步骤 3: 替换 AndroidManifest.xml

把 `D:\code\adapter\app\AndroidManifest.xml` 复制到新项目的 `app\src\main\AndroidManifest.xml`,**覆盖** Android Studio 生成的版本。

## 步骤 4: 删除/调整自动生成的资源文件

Android Studio 生成的 `app\src\main\res\layout\activity_main.xml` 不需要(MainActivity 用纯 Java 代码构建 UI)。可以保留也可以删除。

如果有报错关于 `R.layout.activity_main`,确认 MainActivity.java 没有引用它(应该用 `setContentView(layout)` 而不是 `setContentView(R.layout.xxx)`)。

## 步骤 5: 调整 build.gradle (app 模块)

`app\build.gradle` 中确认:

```groovy
android {
    namespace 'com.example.hello2'
    compileSdk 34

    defaultConfig {
        applicationId "com.example.hello2"
        minSdk 21
        targetSdk 34
        versionCode 1
        versionName "1.0"
    }

    buildTypes {
        release {
            minifyEnabled false
        }
    }
    compileOptions {
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }
}
```

**不要添加任何 implementation 依赖** — 项目应该是空依赖,只用标准 SDK。

## 步骤 6: 编译 APK

Android Studio 菜单 → **Build** → **Build APK(s)**

或者命令行:
```cmd
cd D:\code\adapter\app_studio
gradlew assembleDebug
```

输出 APK 在: `app\build\outputs\apk\debug\app-debug.apk`

## 步骤 7: 复制到 out/ 目录

```cmd
mkdir D:\code\adapter\out\app
copy app_studio\app\build\outputs\apk\debug\app-debug.apk D:\code\adapter\out\app\hello2.apk
```

## 步骤 8: 推送到 ECS (可选,用于完整部署包整合)

```cmd
scp D:\code\adapter\out\app\hello2.apk oh-build:/home/HanBingChen/adapter/out/app/
```

## 步骤 9: 部署到 DAYU200 设备

待设备到位后:

```bash
# 通过 hdc (从 ECS 或本地)
hdc file send hello2.apk /data/local/tmp/
hdc shell pm install /data/local/tmp/hello2.apk

# 或者把 APK 放到 system/app 目录(需要 root)
hdc file send hello2.apk /system/app/hello2/hello2.apk
hdc shell sync
hdc shell reboot
```

## 验证适配层是否生效

**不要在 APK 内做检查**。通过 logcat 在外部观察:

```bash
# 启动 APK 后看 logcat
hdc shell logcat | grep -E 'OH_AMAdapter|HelloWorld|OH_WMAdapter'
```

预期看到:
- `OH_AMAdapter` 标签 — 说明 framework.jar L5 patch 被触发,Adapter 类被加载
- `HelloWorld_Main: === MainActivity.onCreate() ===` — 说明 Application 启动正常
- `OH_WMAdapter` 标签 — 说明 WindowManager Adapter 被激活

## 故障排除

| 问题 | 原因 | 解决方法 |
|---|---|---|
| 编译时找不到 `adapter.core.OHEnvironment` | APK 仍引用了适配层类 | 确认你用的是 `D:\code\adapter\app\java\` 下的版本,grep 一下不应该有任何 `import adapter.*` |
| Gradle 同步失败 | SDK 版本不匹配 | Tools → SDK Manager 安装 Android 14 (API 34) |
| APK 安装失败 (signature) | DAYU200 拒绝 debug 签名 | 用 platform 证书重签 (从 AOSP 复制 platform.pk8/x509.pem) |
| 启动时 UnsatisfiedLinkError | libhwui.so 中某个 native 方法没注册 | 检查 logcat 报哪个方法,可能需要在 typeface_minimal_stub.cpp 加入对应 register_xxx |
| 启动时 ClassNotFoundException: adapter.* | framework.jar L5 patch 没生效 | 确认 ECS 上的 framework.jar 已重编 + boot image 已 regen + 部署到 `/system/android/framework/` |

## 注意事项

- **不要** import 任何 `adapter.*` 类 — APK 必须是纯 Android 代码
- **不要** 在 build.gradle 添加 `oh-adapter-framework` 依赖
- **不要** 在源代码中检查 OH 环境 — 适配层应该对 APK 完全透明
- **可以** 加日志 (`Log.i(TAG, ...)`),日志会被 ECS 上的 logcat 工具捕获,用于外部验证

## 项目核心承诺

> 任何 Android APK,不重新编译,直接安装到部署了适配层的 OH 设备上即可运行。

如果这个 Hello World APK 需要为 OH 做任何修改,那就违反了项目的核心承诺。本指南确保 APK 保持纯 Android 代码,所有适配工作都在 APK 之外完成。
