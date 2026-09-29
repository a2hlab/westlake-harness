# libwestlake_jni_gapfill.so — jni-noimpl 簇补缺(r17a 排名①)

sha16=c5ed50d53d20e97f;源+build.sh+host_test 同目录。

## 覆盖(r17a 簇 → 实现)

| 符号 | app | 实现 | 来源(一手行号) |
|---|---|---|---|
| android.os.Process.getElapsedCpuTime()J | fd-im-vector-app,fd-meet | **Westlake 真实现**:CLOCK_PROCESS_CPUTIME_ID 毫秒截断 | oh_process_cpu_time.cpp L14-28(android_os_Process.cpp L20-21 注册) |
| FileObserver$ObserverThread init/observe/startWatching/stopWatching | fd-com-amaze | **Westlake 真实现**:inotify 全套,回调 onEvent | class_library_services.cpp L68-127 + 注册 L410-427 |
| ActivityManagerAdapter.nativeStopServiceAbility(String,String)I | fd-catima | 桩 0(真实现随 #91 commonevent 包链接,避免重复定义) | activity_manager_adapter.cpp L130-135/L209 |
| android.hardware.Camera.getNumberOfCameras()I | opencamera | 桩 0(无相机设备语义,不 null 不抛) | Westlake 无 |
| EGLImpl._nativeClassInit()V | fd-shatteredpixeldungeon | no-op 桩 | Westlake 无 |
| fd-plus | (system library absent 签名,上板看具体符号再补) | — | — |

## 硬要求落实

每类 RegisterNatives 独立 try(FindClass 失败只 log `[JNI-GAPFILL]` 继续);空桩类型正确(0/V,绝不 null);JNI_OnLoad 自装(同 TLS/HTML 模式,cx-t0 --add 入包由 runtime JAR System.load)。cx-bms 全量清单出来后,Westlake 有实现的符号并入此处(追加点=install() 内 try_register 段)。

## host 测(./host_test 全过)

簇符号全覆盖/空桩返回类型合法/FileObserver 四方法全 verbatim/Camera 0 语义。
