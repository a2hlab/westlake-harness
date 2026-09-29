# Current integration (cx-t0, B91)

The retained 84695d62 bridge already exports the complete CommonEvent backend.
The production candidate builds only `common_event_registration.cpp` into
liboh_android_runtime, preserving c835a93e VelocityTracker/SQLite. Five method
bodies/signatures are copied from the reference below; ability registrations
are deliberately not duplicated. The other files are unchanged provenance,
not additional backend objects in this candidate. Use the verified recipe in
`benchmark/2026-09-30-commonevent-registration/`, not the original reference
build.sh below. Device registration/IPC/callback evidence is still pending.

# westlake-commonevent — CommonEvent JNI 供给包(#91,照抄自 Westlake)

来源(Mac 副本 `/Users/zhaoyue/orca/workspaces/vm-copies/westlake-current/`,#90 定因:r15c 17 个 unsat-link 中 CommonEvent 族 JNI 缺失是主因之一):**7 个文件原样拷贝(cmp 字节级核验),零改动**。

## 文件 → 方法 → 救哪些 app

| 文件 | 提供 | 救(r15c 实测死点) |
|---|---|---|
| `activity_manager_adapter.cpp`(framework/activity/jni,L140-250) | **5 个 CommonEvent native 的实现 + 注册表**:`nativeSubscribeCommonEvent`(L154)、`nativeUnsubscribe`(L163)、`nativePublish`(L167)、`nativeFinish`(L181)、`nativeGetSticky`(L189);`kMethods[]` L196-234 + `register_ActivityManagerAdapter` L237(一次 RegisterNatives 10 个方法,5 ability + 5 CommonEvent) | **直接救 r15c 已证死的 3 个**:vlc(`nativePublishCommonEvent` No implementation)、fd-gallery(`nativeSubscribeCommonEvent`)、fd-etar(`nativeSubscribeCommonEvent`);17 个 unsat-link 桶中其余命中 CommonEvent 签名的在编进后一并解除 |
| `oh_common_event_client.cpp/.h`(framework/broadcast/jni,221+117 行) | OH 侧真实现:subscribe/unsubscribe/publish/finishReceiver/getStickyEvent(经 OH `common_event_manager.h` 等 sysroot 头) | 上述 native 的后端 |
| `common_event_subscriber_adapter.cpp/.h`(125+50 行) | 订阅回调桥(OH→Java receiver) | 同上 |
| `CommonEventReceiverBridge.java` / `BroadcastEventConverter.java`(framework/broadcast/java) | Java 侧接收桥与事件转换(runtime jar 用) | 广播接收型 app |

## r15c 17 个 unsat-link 桶的覆盖预估

- **明确覆盖**(死点原文就是 CommonEvent native):vlc、fd-gallery、fd-etar —— 3 个直接
- **待编后复跑确认**:桶内其余(fd-com-kunzisoft/fd-fennec[JNA 另案]/fd-fluffychat/fd-immich/fd-kitchenowl[Flutter guest-dlopen 另案]/fd-libre/fd-meet/fd-minetest/fd-saber/fd-shatteredpixeldungeon/firefox/localsend/opencamera/termux)——各自的 UnsatisfiedLinkError 原文需逐个比对;Flutter 线程门与 JNA resource 释放不在本包范围(已在外环新墙清单)

## 接线(cx-t0)

- build.sh(dockbuild,`OHOS_SYSROOT` 环境给;**7 源缺一即失败**):产出 3 个 `.o`——链接进 runtime 的 native 库,启动时调 `register_ActivityManagerAdapter(env)`(Westlake 的接线点:AndroidRuntime 注册表)。
- **注意**:该 cpp 同时注册 5 个 ability native(与现桥可能重名)——cx-t0 链接时只取 CommonEvent 5 项或解决重名;注册表保持与 Westlake 字节一致是刻意的(降低分叉)。
- sysroot 需含 OH `common_event_manager.h / common_event_data.h / common_event_publish_info.h / common_event_subscribe_info.h / matching_skills.h`(OH C SDK);缺则 build.sh exit 2 并提示。
