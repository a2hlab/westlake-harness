// ============================================================================
// android_media_MediaPlayer.cpp
//
// JNI bindings for android.media.MediaPlayer — L12 视频/媒体插件楼层的第一个
// 具体实现尝试（HelloWorld "L12 视频探针"测试场景，2026-07-10）。
//
// WHY (evidence, 本次会话决定性订正了此前 L12 视频预研 memory 条目里一处过度
// 宣称):
//   route3-rssurface-stack-confirmed.md "L12视频/媒体预研"一节此前只查了
//   framework/mainline-stubs/java/android/media/ 目录（只有 5 个 mainline
//   module 边界 stub 文件），据此断言"MediaPlayer.java 本身也是空白"。这个
//   推论找错了目录：mainline-stubs 只装 packages/modules/* 的 Java 源
//   （见 build/inner/compile_mainline_real.sh 注释），MediaPlayer/MediaCodec/
//   MediaExtractor/MediaFormat 是 frameworks/base/media/java/android/media/
//   下的**核心框架类**，走的是完全不同的 framework.jar 编译流程（Soong，
//   build_aosp_fw.sh 里被标为"REJECTED here, ECS-only"，不在 mainline-stubs
//   范畴）。
//
//   本次用已部署 framework.jar 的一份真实备份
//   （/opt/21.Game/artifacts/coherent_jars/framework.jar）做决定性核查：
//     - unzip -l 该 jar：0 个 android/media/*.class（这份 jar 本身不存
//       .class，是 dex 格式，见下）；但 classes2.dex 用 dexdump 反汇编确认
//       **Landroid/media/MediaPlayer; 类定义真实存在**（Class descriptor 命中
//       且带完整的 direct/virtual method 列表），MediaCodec/MediaExtractor/
//       MediaFormat 的类型引用也都在 classes.dex/classes2.dex/classes3.dex/
//       classes4.dex 里出现。
//   结论订正（范围已按 codex round1 挑刺收紧，不过度泛化）：**对
//   MediaPlayer 这一个类，Java 类定义层不是 gap**（已经在真实 framework.jar
//   里，随 AOSP 源码整体编译带入）——这条证据是针对 coherent_jars 备份的
//   framework.jar 得出的，**证明的是"这份 artifact 备份里有"，不是"设备当前
//   部署的 boot image 就是这份"**（未做设备侧 sha256/boot provenance 核对，
//   4 份独立位置的备份 sha256 相同，不排除同源）。native 侧确定缺失：
//   `grep -rn "register_android_media" framework/android-runtime` 零命中，
//   `kRegJNI[]`（AndroidRuntime.cpp）里也没有任何 android.media.* 条目。
//   下面这份文件补的是 **MediaPlayer 这一条 native 注册路径**的 gap——
//   MediaCodec/MediaExtractor 等其它 android.media.* 类的 native 注册依然
//   完全空白，不在本次改动范围内，不要泛化成"整个 android.media.* 的 gap
//   已修复"。
//
//   kMediaPlayerMethods 的 49 个 (name, signature) 全部从上述 classes2.dex
//   用 `dexdump` 反汇编真实提取（非从记忆/网上 AOSP 源码猜测），是这份具体
//   部署 framework.jar 版本真实的 native 方法表——比对着记忆库常见的旧版
//   AOSP MediaPlayer.java 会发现这版本更新（Parcel-based IMediaPlayer 客户端
//   + VolumeShaper/DRM/OutputDevice 等新增能力），如果只凭旧版记忆手写会
//   完全对不上。
//
// SEMANTICS — 桩实现，不做真实解码。与 L12 音频 W15 修复（FMOD 触碰的
//   android.media.AudioSystem.getMaxChannelCount 等少数方法"→ 2"式桩）同一
//   档次的"不崩溃优先"修复，不是完整媒体框架移植：
//
//   真实 AOSP 实现（frameworks/base/media/jni/android_media_MediaPlayer.cpp）
//   是一层瘦 Parcel/Binder 客户端，通过 IMediaPlayerService 连到独立的
//   mediaserver 进程做真正解码（libstagefright / Codec2 HAL）。这整条系统
//   服务在这套 adapter 里完全不存在，原样移植不可行，也超出本次"探"视频
//   L12 是否可以从"完全崩溃/UnsatisfiedLinkError"推进到"不崩溃、走完
//   MediaPlayer 生命周期"这一档验证目标的范围。
//
//   本桩实现明确不做的事（诚实标注，不夸大"能播放视频"）：
//     - 不真正打开/解析任何媒体文件内容（_setDataSource 系列忽略实际数据）。
//     - 不做任何真实解码（H264/HEVC/...），不驱动任何真实渲染管线。
//     - 不向 Surface 写入任何像素 —— 这需要 ANativeWindow_lock /
//       ANativeWindow_unlockAndPost，本 adapter 当前未导出这两个符号
//       （只有 fromSurface/acquire/release/getWidth/getHeight/getFormat/
//       setBuffersGeometry，见 android_graphics_compat_shim.cpp）。裸写
//       未验证过的 buffer-lock 代码风险太高（可能踩坏 RS 侧内存），本次
//       不冒险实现，如实标注为"证明 Surface 交接通了，未证明有画面"。
//     - getVideoWidth/getVideoHeight/getCurrentPosition/getDuration 等只读
//       查询一律返回 0，不编造虚假分辨率/进度数字。
//
//   本桩实现做的事：
//     - native_init / native_setup：缓存 postEventFromNative 方法 ID +
//       保存 weakThis 全局引用，不触碰 Java 侧任何实例字段（不需要 —— 无
//       状态桩，用一个模块级、加锁的单实例状态代替，见下方"单实例限制"）。
//     - _setVideoSurface(Surface)：调用已经在这个 .so 里验证过的
//       ANativeWindow_fromSurface（L09/L10 首帧墙沿用的同一条 Surface→
//       ANativeWindow 桥接路径，android_graphics_compat_shim.cpp）拿到
//       ANativeWindow* 并记录 width/height/format——这一步真实证明"Surface
//       从 Java 层交接到 native MediaPlayer 路径"这条链路本身是通的。
//     - _prepareAsync/_prepare：回调 Java 侧 postEventFromNative(...) 派发
//       MEDIA_PREPARED（事件码=1，AOSP 自 1.0 起对外稳定的公开 API 常量，
//       未逐一 dex 反汇编复核但作为跨版本从未变过的公开常量按高置信度直接
//       使用），让 app 的 OnPreparedListener 走完整回调链——不代表真解码
//       完成。
//     - _start/_pause/_stop/_reset/_release：只维护一个进程内 bool 状态。
//     - 其余（DRM/VolumeShaper/OutputDevice/Retransmit/BatteryData 等）：
//       本 HelloWorld L12 探针场景不会触达，同样注册但只返回安全默认值
//       （0/false/null），避免它们被间接触达时抛 UnsatisfiedLinkError。
//
//   单实例限制（诚实标注）：为避免引入按 Java 实例做 field-ID 缓存/映射的
//   额外复杂度和未经设备验证的风险，本桩用一个模块级（非按实例）状态变量
//   保存 weakThis + playing 标志——**同一进程同时只支持一个"正在使用"的
//   MediaPlayer 实例**，多实例并发场景状态会互相覆盖。HelloWorld L12 探针
//   场景只会创建一个 MediaPlayer，这条限制在验证范围内无影响；如果后续要
//   把这条桩实现推广到真实游戏场景（多实例），需要补 field-ID 版本的
//   per-instance 状态（工作量增加但技术路径清楚）。
//
// 逐方法 fault-tolerant 注册（镜像 android_os_Debug.cpp 的模式）：任何一个
// 方法名/签名在未来 boot image 版本漂移，只跳过那一个，不会让整个类注册
// 失败。
// ============================================================================

#include "AndroidRuntime.h"

#include <jni.h>
#include <stdint.h>
#include <string.h>
#include <mutex>

// android_graphics_compat_shim.cpp（同一个 .so，见 SRCS）已经导出并在设备上
// 验证过这几个符号（L09/L10 Surface→ANativeWindow 桥接路径的一部分）。这里
// 只做前向声明复用，不重新实现、不改动那条已验证的路径。
struct ANativeWindow;
extern "C" ANativeWindow* ANativeWindow_fromSurface(JNIEnv* env, jobject surface);
extern "C" int32_t ANativeWindow_getWidth(ANativeWindow* w);
extern "C" int32_t ANativeWindow_getHeight(ANativeWindow* w);
extern "C" int32_t ANativeWindow_getFormat(ANativeWindow* w);

// 与本目录其它文件（android_graphics_compat_shim.cpp / android_util_Log.cpp
// 等）同一约定：不 #include <hilog/log.h>，自己 extern "C" 声明 HiLogPrint，
// 用 ALOGI/ALOGW 同款的 type=3(LOG_CORE) / level=4(INFO)/5(WARN) 魔数。
extern "C" int HiLogPrint(int type, int level, unsigned int domain,
                          const char* tag, const char* fmt, ...)
    __attribute__((__format__(printf, 5, 6)));

#define MP_LOGI(fmt, ...) \
    HiLogPrint(3, 4, 0xD000F00u, "OH_MediaPlayerStub", fmt, ##__VA_ARGS__)
#define MP_LOGW(fmt, ...) \
    HiLogPrint(3, 5, 0xD000F00u, "OH_MediaPlayerStub", fmt, ##__VA_ARGS__)

namespace android {
namespace {

// AOSP MediaPlayer 公开事件码（frameworks/base .../MediaPlayer.java 自 1.0
// 起未变过的稳定公开常量，见文件头注释）。只用到 PREPARED，其余列出备查。
constexpr jint kMediaPrepared = 1;

// ---- 模块级单实例状态（见文件头"单实例限制"）----------------------------
struct StubState {
    std::mutex mu;
    jobject weakThisGlobal = nullptr;  // GlobalRef to WeakReference<MediaPlayer>
    bool playing = false;
};
StubState g_state;

jclass g_mediaPlayerClass = nullptr;         // GlobalRef, cached in native_init
jmethodID g_postEventFromNative = nullptr;   // static (Object,I,I,I,Object)V

// 2026-07-10 codex round1 挑刺修订：原实现在持锁期间直接调用
// CallStaticVoidMethod（把 Java 执行放进 native 锁内）——如果 Java 侧
// postEventFromNative 的 Handler 分发路径将来重入 release()/reset()（本探针
// 场景不会，但作为通用桩不该假设），会自锁死。改为：持锁只拷贝一份
// GlobalRef，解锁后再回调，用完立即释放这份拷贝。
void firePreparedEvent(JNIEnv* env) {
    jobject weakThisCopy = nullptr;
    {
        std::lock_guard<std::mutex> lk(g_state.mu);
        if (!g_mediaPlayerClass || !g_postEventFromNative || !g_state.weakThisGlobal) {
            MP_LOGW("firePreparedEvent: skip (native_init cache or weakThis missing — "
                    "OnPreparedListener will not fire, but this is not a crash)");
            return;
        }
        weakThisCopy = env->NewGlobalRef(g_state.weakThisGlobal);
    }
    env->CallStaticVoidMethod(g_mediaPlayerClass, g_postEventFromNative,
                               weakThisCopy, kMediaPrepared, 0, 0, nullptr);
    if (env->ExceptionCheck()) {
        MP_LOGW("firePreparedEvent: postEventFromNative threw, clearing");
        env->ExceptionClear();
    }
    env->DeleteGlobalRef(weakThisCopy);
}

// ---- 生命周期 --------------------------------------------------------------

void JNICALL MP_native_init(JNIEnv* env, jclass clazz) {
    if (!g_mediaPlayerClass) {
        g_mediaPlayerClass = reinterpret_cast<jclass>(env->NewGlobalRef(clazz));
    }
    if (!g_postEventFromNative && g_mediaPlayerClass) {
        g_postEventFromNative = env->GetStaticMethodID(
            g_mediaPlayerClass, "postEventFromNative",
            "(Ljava/lang/Object;IIILjava/lang/Object;)V");
        if (!g_postEventFromNative && env->ExceptionCheck()) env->ExceptionClear();
    }
    MP_LOGI("native_init: STUB — cached postEventFromNative=%{public}p "
            "(no real media pipeline initialized)",
            (void*)g_postEventFromNative);
}

void JNICALL MP_native_setup(JNIEnv* env, jobject /*thiz*/, jobject weakThis,
                              jobject /*parcel*/, jint /*sessionId*/) {
    std::lock_guard<std::mutex> lk(g_state.mu);
    if (g_state.weakThisGlobal) {
        env->DeleteGlobalRef(g_state.weakThisGlobal);
        g_state.weakThisGlobal = nullptr;
    }
    if (weakThis) g_state.weakThisGlobal = env->NewGlobalRef(weakThis);
    g_state.playing = false;
    MP_LOGI("native_setup: STUB — weakThis cached=%{public}d (single-instance "
            "state, see file header)", g_state.weakThisGlobal != nullptr);
}

void JNICALL MP__release(JNIEnv* env, jobject /*thiz*/) {
    std::lock_guard<std::mutex> lk(g_state.mu);
    g_state.playing = false;
    if (g_state.weakThisGlobal) {
        env->DeleteGlobalRef(g_state.weakThisGlobal);
        g_state.weakThisGlobal = nullptr;
    }
    MP_LOGI("_release: STUB — state cleared");
}

// 2026-07-10 codex round1 挑刺修订：native_finalize **不**转发到 MP__release。
// 原实现会转发，风险：g_state 是模块级单实例状态（非 per-instance），如果旧
// MediaPlayer 实例 A 已经被显式 release() 过、但它的 Java GC finalizer 延迟到
// 新实例 B 已经 native_setup() 之后才跑，A 的 finalize 会把 B 正在用的
// weakThisGlobal 误清掉——这比"同一时刻只支持一个实例"更严格："同一进程里
// 连续创建/销毁多个实例也不安全"。本探针场景（HelloWorld 单个 Activity 单个
// MediaPlayer，onDestroy 里显式 release）不会触发，但作为桩实现不该埋这个坑。
// 修法：finalize 只记日志，不碰共享状态；显式 release() 才清（这是本探针场景
// 唯一真正依赖的路径）。代价：如果调用方从不显式 release()，
// weakThisGlobal 的 GlobalRef 不会被释放（进程内存泄漏，不是崩溃/状态错乱），
// 对探针工具这个量级可接受，生产化需要 per-instance 状态（file header 已说明）。
void JNICALL MP_native_finalize(JNIEnv*, jobject) {
    MP_LOGI("native_finalize: STUB no-op (see comment above — does NOT touch "
            "shared g_state to avoid a delayed-finalizer-clobbers-live-instance "
            "hazard; call release() explicitly to free the cached weak ref)");
}

// ---- 数据源（全部 no-op，忽略真实内容）------------------------------------

void JNICALL MP__setDataSource_fd(JNIEnv*, jobject, jobject /*fd*/, jlong offset, jlong length) {
    MP_LOGI("_setDataSource(fd,off=%{public}lld,len=%{public}lld): STUB no-op, "
            "content ignored", (long long)offset, (long long)length);
}

void JNICALL MP__setDataSource_mds(JNIEnv*, jobject, jobject /*mediaDataSource*/) {
    MP_LOGI("_setDataSource(MediaDataSource): STUB no-op, content ignored");
}

void JNICALL MP_nativeSetDataSource(JNIEnv*, jobject, jobject /*httpServiceBinder*/,
                                     jstring /*path*/, jobjectArray /*keys*/,
                                     jobjectArray /*values*/) {
    MP_LOGI("nativeSetDataSource(uri): STUB no-op, content ignored");
}

// ---- Surface 交接（唯一真正touch了已验证桥接路径的方法）-------------------

void JNICALL MP__setVideoSurface(JNIEnv* env, jobject /*thiz*/, jobject surface) {
    if (!surface) {
        MP_LOGI("_setVideoSurface(null): STUB — clearing surface, no-op");
        return;
    }
    ANativeWindow* win = ANativeWindow_fromSurface(env, surface);
    if (!win) {
        MP_LOGW("_setVideoSurface: ANativeWindow_fromSurface returned null "
                "(Surface handoff into native MediaPlayer path FAILED)");
        return;
    }
    int32_t w = ANativeWindow_getWidth(win);
    int32_t h = ANativeWindow_getHeight(win);
    int32_t fmt = ANativeWindow_getFormat(win);
    MP_LOGI("_setVideoSurface: ANativeWindow acquired w=%{public}d h=%{public}d "
            "fmt=%{public}d — STUB proves Surface handoff reaches native "
            "MediaPlayer path; NO pixels written, NO real decode", w, h, fmt);
}

// ---- prepare / playback state machine -------------------------------------

jint JNICALL MP__prepare(JNIEnv* env, jobject, jobject /*parcel*/) {
    MP_LOGI("_prepare: STUB — no real decode; synthesizing MEDIA_PREPARED so "
            "the (rare) synchronous prepare() caller unblocks");
    firePreparedEvent(env);
    return 0;
}

jint JNICALL MP__prepareAsync(JNIEnv* env, jobject, jobject /*parcel*/) {
    MP_LOGI("_prepareAsync: STUB — synthesizing MEDIA_PREPARED callback "
            "immediately (no real background prepare, no real media opened)");
    firePreparedEvent(env);
    return 0;
}

void JNICALL MP__start(JNIEnv*, jobject) {
    std::lock_guard<std::mutex> lk(g_state.mu);
    g_state.playing = true;
    MP_LOGI("_start: STUB — playing=true, no real render pipeline driven");
}

void JNICALL MP__pause(JNIEnv*, jobject) {
    std::lock_guard<std::mutex> lk(g_state.mu);
    g_state.playing = false;
}

void JNICALL MP__stop(JNIEnv*, jobject) {
    std::lock_guard<std::mutex> lk(g_state.mu);
    g_state.playing = false;
}

void JNICALL MP__reset(JNIEnv*, jobject) {
    std::lock_guard<std::mutex> lk(g_state.mu);
    g_state.playing = false;
}

jboolean JNICALL MP_isPlaying(JNIEnv*, jobject) {
    std::lock_guard<std::mutex> lk(g_state.mu);
    return g_state.playing ? JNI_TRUE : JNI_FALSE;
}

// ---- 只读查询：诚实返回 0/false/null，不编造数字 ---------------------------

jint JNICALL MP_getVideoWidth(JNIEnv*, jobject)  { return 0; }
jint JNICALL MP_getVideoHeight(JNIEnv*, jobject) { return 0; }
jint JNICALL MP_getCurrentPosition(JNIEnv*, jobject) { return 0; }
jint JNICALL MP_getDuration(JNIEnv*, jobject) { return 0; }
jint JNICALL MP_getAudioSessionId(JNIEnv*, jobject) { return 0; }
jboolean JNICALL MP_isLooping(JNIEnv*, jobject) { return JNI_FALSE; }
void JNICALL MP_setLooping(JNIEnv*, jobject, jboolean) {}
void JNICALL MP_attachAuxEffect(JNIEnv*, jobject, jint) {}
jobject JNICALL MP_getPlaybackParams(JNIEnv*, jobject) { return nullptr; }
jobject JNICALL MP_getSyncParams(JNIEnv*, jobject) { return nullptr; }
void JNICALL MP_setPlaybackParams(JNIEnv*, jobject, jobject) {}
void JNICALL MP_setSyncParams(JNIEnv*, jobject, jobject) {}
void JNICALL MP_setNextMediaPlayer(JNIEnv*, jobject, jobject) {}

// ---- 其余：本探针场景不会触达，安全默认值兜底 ------------------------------

jint JNICALL MP__getAudioStreamType(JNIEnv*, jobject) { return 3; /* STREAM_MUSIC, arbitrary default */ }
void JNICALL MP__notifyAt(JNIEnv*, jobject, jlong) {}
void JNICALL MP__setAudioStreamType(JNIEnv*, jobject, jint) {}
void JNICALL MP__setAuxEffectSendLevel(JNIEnv*, jobject, jfloat) {}
void JNICALL MP__setVolume(JNIEnv*, jobject, jfloat, jfloat) {}
void JNICALL MP__seekTo(JNIEnv*, jobject, jlong, jint) {}
void JNICALL MP__prepareDrm(JNIEnv*, jobject, jbyteArray, jbyteArray) {}
void JNICALL MP__releaseDrm(JNIEnv*, jobject) {}
jint JNICALL MP_native_applyVolumeShaper(JNIEnv*, jobject, jobject, jobject) { return 0; }
void JNICALL MP_native_enableDeviceCallback(JNIEnv*, jobject, jboolean) {}
jboolean JNICALL MP_native_getMetadata(JNIEnv*, jobject, jboolean, jboolean, jobject) { return JNI_FALSE; }
jobject JNICALL MP_native_getMetrics(JNIEnv*, jobject) { return nullptr; }
jint JNICALL MP_native_getRoutedDeviceId(JNIEnv*, jobject) { return 0; }
jobject JNICALL MP_native_getVolumeShaperState(JNIEnv*, jobject, jint) { return nullptr; }
jint JNICALL MP_native_invoke(JNIEnv*, jobject, jobject, jobject) { return 0; }
jint JNICALL MP_native_pullBatteryData(JNIEnv*, jclass, jobject) { return 0; }
void JNICALL MP_native_setAudioSessionId(JNIEnv*, jobject, jint) {}
jint JNICALL MP_native_setMetadataFilter(JNIEnv*, jobject, jobject) { return 0; }
jboolean JNICALL MP_native_setOutputDevice(JNIEnv*, jobject, jint) { return JNI_FALSE; }
jint JNICALL MP_native_setRetransmitEndpoint(JNIEnv*, jobject, jstring, jint) { return 0; }
jboolean JNICALL MP_setParameter(JNIEnv*, jobject, jint, jobject) { return JNI_FALSE; }

// ---- 注册表：49 个方法，name+signature 全部来自 classes2.dex 反汇编 -------

struct MethodSpec {
    const char* name;
    const char* sig;
    void* fn;
};

const MethodSpec kMediaPlayerMethods[] = {
    { "_getAudioStreamType",        "()I",                                                          (void*)MP__getAudioStreamType },
    { "_notifyAt",                  "(J)V",                                                         (void*)MP__notifyAt },
    { "_pause",                     "()V",                                                          (void*)MP__pause },
    { "_prepare",                   "(Landroid/os/Parcel;)I",                                       (void*)MP__prepare },
    { "_prepareAsync",              "(Landroid/os/Parcel;)I",                                       (void*)MP__prepareAsync },
    { "_prepareDrm",                "([B[B)V",                                                      (void*)MP__prepareDrm },
    { "_release",                   "()V",                                                          (void*)MP__release },
    { "_releaseDrm",                "()V",                                                          (void*)MP__releaseDrm },
    { "_reset",                     "()V",                                                          (void*)MP__reset },
    { "_seekTo",                    "(JI)V",                                                        (void*)MP__seekTo },
    { "_setAudioStreamType",        "(I)V",                                                         (void*)MP__setAudioStreamType },
    { "_setAuxEffectSendLevel",     "(F)V",                                                         (void*)MP__setAuxEffectSendLevel },
    { "_setDataSource",             "(Landroid/media/MediaDataSource;)V",                           (void*)MP__setDataSource_mds },
    { "_setDataSource",             "(Ljava/io/FileDescriptor;JJ)V",                                (void*)MP__setDataSource_fd },
    { "_setVideoSurface",           "(Landroid/view/Surface;)V",                                    (void*)MP__setVideoSurface },
    { "_setVolume",                 "(FF)V",                                                        (void*)MP__setVolume },
    { "_start",                     "()V",                                                          (void*)MP__start },
    { "_stop",                      "()V",                                                          (void*)MP__stop },
    { "nativeSetDataSource",        "(Landroid/os/IBinder;Ljava/lang/String;[Ljava/lang/String;[Ljava/lang/String;)V", (void*)MP_nativeSetDataSource },
    { "native_applyVolumeShaper",   "(Landroid/media/VolumeShaper$Configuration;Landroid/media/VolumeShaper$Operation;)I", (void*)MP_native_applyVolumeShaper },
    { "native_enableDeviceCallback","(Z)V",                                                         (void*)MP_native_enableDeviceCallback },
    { "native_finalize",            "()V",                                                         (void*)MP_native_finalize },
    { "native_getMetadata",         "(ZZLandroid/os/Parcel;)Z",                                     (void*)MP_native_getMetadata },
    { "native_getMetrics",          "()Landroid/os/PersistableBundle;",                             (void*)MP_native_getMetrics },
    { "native_getRoutedDeviceId",   "()I",                                                         (void*)MP_native_getRoutedDeviceId },
    { "native_getVolumeShaperState","(I)Landroid/media/VolumeShaper$State;",                        (void*)MP_native_getVolumeShaperState },
    { "native_init",                "()V",                                                         (void*)MP_native_init },
    { "native_invoke",              "(Landroid/os/Parcel;Landroid/os/Parcel;)I",                    (void*)MP_native_invoke },
    { "native_pullBatteryData",     "(Landroid/os/Parcel;)I",                                       (void*)MP_native_pullBatteryData },
    { "native_setAudioSessionId",   "(I)V",                                                         (void*)MP_native_setAudioSessionId },
    { "native_setMetadataFilter",   "(Landroid/os/Parcel;)I",                                       (void*)MP_native_setMetadataFilter },
    { "native_setOutputDevice",     "(I)Z",                                                         (void*)MP_native_setOutputDevice },
    { "native_setRetransmitEndpoint","(Ljava/lang/String;I)I",                                      (void*)MP_native_setRetransmitEndpoint },
    { "native_setup",               "(Ljava/lang/Object;Landroid/os/Parcel;I)V",                    (void*)MP_native_setup },
    { "setParameter",               "(ILandroid/os/Parcel;)Z",                                      (void*)MP_setParameter },
    { "attachAuxEffect",            "(I)V",                                                         (void*)MP_attachAuxEffect },
    { "getAudioSessionId",          "()I",                                                         (void*)MP_getAudioSessionId },
    { "getCurrentPosition",         "()I",                                                         (void*)MP_getCurrentPosition },
    { "getDuration",                "()I",                                                         (void*)MP_getDuration },
    { "getPlaybackParams",          "()Landroid/media/PlaybackParams;",                             (void*)MP_getPlaybackParams },
    { "getSyncParams",              "()Landroid/media/SyncParams;",                                 (void*)MP_getSyncParams },
    { "getVideoHeight",             "()I",                                                         (void*)MP_getVideoHeight },
    { "getVideoWidth",              "()I",                                                         (void*)MP_getVideoWidth },
    { "isLooping",                  "()Z",                                                         (void*)MP_isLooping },
    { "isPlaying",                  "()Z",                                                         (void*)MP_isPlaying },
    { "setLooping",                 "(Z)V",                                                         (void*)MP_setLooping },
    { "setNextMediaPlayer",         "(Landroid/media/MediaPlayer;)V",                               (void*)MP_setNextMediaPlayer },
    { "setPlaybackParams",          "(Landroid/media/PlaybackParams;)V",                            (void*)MP_setPlaybackParams },
    { "setSyncParams",              "(Landroid/media/SyncParams;)V",                                (void*)MP_setSyncParams },
};

}  // namespace

int register_android_media_MediaPlayer(JNIEnv* env) {
    jclass clazz = env->FindClass("android/media/MediaPlayer");
    if (!clazz) {
        if (env->ExceptionCheck()) env->ExceptionClear();
        MP_LOGW("register_android_media_MediaPlayer: FindClass failed — "
                "android.media.MediaPlayer not in this boot image's framework.jar?");
        return -1;
    }
    // 逐个注册、单个失败不影响其它（镜像 android_os_Debug.cpp 的模式）：
    // boot image 版本漂移时，签名对不上的方法被跳过而不是整批失败。
    //
    // 2026-07-10 codex round1 挑刺修订：原先"任意 ≥1 个方法注册成功就算
    // success"对 MediaPlayer 不成立——跟 android_os_Debug.cpp 那 4 个方法
    // 平权不同，MediaPlayer 的 native_init 是 class 静态初始化块必调的
    // （类一旦被 FindClass/触碰就跑），如果它没注册成功，即便其它随便几个
    // 方法注册成功了，class 初始化那一步照样 UnsatisfiedLinkError，"registered
    // > 0 -> success" 这个判断会给出假阳性。改为要求 native_init +
    // native_setup 这两个"类初始化 + 本探针路径最小起点"必须都注册成功，
    // 否则整体判失败（调用方应当能感知"这个 boot image 版本用不了"，而不是
    // 被虚假的成功状态误导）。
    bool nativeInitOk = false;
    bool nativeSetupOk = false;
    int registered = 0;
    for (const MethodSpec& m : kMediaPlayerMethods) {
        JNINativeMethod jm = { m.name, m.sig, m.fn };
        if (env->RegisterNatives(clazz, &jm, 1) == JNI_OK) {
            ++registered;
            if (strcmp(m.name, "native_init") == 0) nativeInitOk = true;
            if (strcmp(m.name, "native_setup") == 0) nativeSetupOk = true;
        } else {
            if (env->ExceptionCheck()) env->ExceptionClear();
            MP_LOGW("register_android_media_MediaPlayer: %{public}s%{public}s "
                    "did not match — skipped", m.name, m.sig);
        }
    }
    env->DeleteLocalRef(clazz);
    MP_LOGI("register_android_media_MediaPlayer: %{public}d/%{public}zu methods "
            "registered, native_init=%{public}d native_setup=%{public}d "
            "(STUB implementation — see file header for exact scope)",
            registered, sizeof(kMediaPlayerMethods) / sizeof(kMediaPlayerMethods[0]),
            nativeInitOk, nativeSetupOk);
    if (!nativeInitOk) {
        MP_LOGW("register_android_media_MediaPlayer: native_init NOT registered "
                "-> class static init will UnsatisfiedLinkError regardless of "
                "other methods; treating as overall FAILURE");
    }
    return (nativeInitOk && nativeSetupOk) ? 0 : -1;
}

}  // namespace android
