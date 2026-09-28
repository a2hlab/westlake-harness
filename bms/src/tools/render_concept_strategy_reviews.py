#!/usr/bin/env python3
"""Render Fn04-Fn07 textbook-style Concept route review pages."""

from __future__ import annotations

import base64
import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


DATA = {
    "Fn04": {
        "name": "Window / Surface / Rendering",
        "question": "Android 窗口、Surface 与一帧内容怎样在 SceneBoard 上保持 Android 可观察语义？",
        "definition": (
            "Fn04 不是“拿到一块屏幕”或“eglSwapBuffers 返回 true”。它要求同一代 "
            "WindowRecord 从 IWindowSession add/relayout，经 BufferQueue、NativeWindow、"
            "EGL/SurfaceControl、vsync/traversal 到真实 present/finish receipt 可关联；"
            "错误、销毁、焦点、resize、visibility 与独立 SurfaceTexture 分支也必须可观察。"
        ),
        "connect": (
            "当前部署没有 AOSP WMS。Bridge 的 scoped IWindowSession façade 是实际 server "
            "边界；Ability/SceneBoard 已创建的主 hostSession 仍拥有宿主窗口策略。主窗口必须"
            "复用并认证该 hostSession，不能把 legacy WM_OK 或新建 specific session 当成功。"
        ),
        "terms": [
            (
                "Window（窗口）",
                "Android 应用与窗口管理策略交互的逻辑对象：它携带窗口类型、token、层级、"
                "几何、可见性、焦点、insets 与生命周期，并把 ViewRoot 的请求关联到一个可管理的显示区域。",
                "不是像素、显存或可绘制缓冲区；Window 存在不代表已有画面。",
                "Android 侧身份由 IWindow binder/window token/session/generation 共同限定；宿主策略由 "
                "Ability/SceneBoard 的 SceneSession 持有。生命周期为 add→relayout/visibility/focus→remove。",
                "成功必须看到同代 WindowRecord 与已认证 hostSession 的双向 callback；仅返回 WM_OK、仅创建对象"
                "或仅打印 window id 都不算成功。销毁后 callback、错代 resize 和未授权 session 必须失败。",
            ),
            (
                "Surface（图形生产端）",
                "应用或渲染器向合成系统提交图形缓冲区的 producer endpoint。生产者从有界队列取得 buffer，"
                "写入一帧并带同步 fence 归还，消费者随后合成或采样该 buffer。",
                "不是 Window，也不是一张静态图片；同一个 Window 可在生命周期中换代 Surface，独立 "
                "SurfaceTexture 也可没有顶层 Window。",
                "身份由 producer endpoint、BufferQueue uniqueId 与 generation 限定；producer/consumer "
                "分持队列两端。生命周期为 create/connect→dequeue/queue→replace/disconnect/abandon。",
                "成功必须把 queue、fence、generation 和最终 consumer/present receipt 关联起来；"
                "abandoned queue、旧代 buffer、错误 uniqueId 或 fence 超时必须给出 typed failure。",
            ),
            (
                "Rendering（渲染）",
                "把 View/Unity 场景状态按时间顺序转换为绘制命令、GPU 工作和图形 buffer，并最终交由"
                "合成器显示的过程；典型链路是 vsync→traversal→draw→queue/transaction→compose→present。",
                "不是单个对象或 API 返回值；eglSwapBuffers 成功只表示提交发生，不表示用户已经看见该帧。",
                "Android 侧由 Choreographer/ViewRoot/RenderThread/EGL 或 Unity renderer 推进，OH 侧由 "
                "BufferQueue、RenderService/compositor 与显示管线消费；每帧以 frame/vsync/generation 标识。",
                "成功终点是同一帧的 present/finish receipt 或可校验像素；只看到 draw 日志、RSSurfaceNode "
                "析构、EGL 返回成功或进程存活均不算上屏。",
            ),
            (
                "BufferQueue / ProducerSurface",
                "连接图形生产者与消费者的有界缓冲协议，管理 slot、buffer 所有权、acquire/release fence、"
                "队列背压和换代。",
                "不是无界消息队列，也不是可以忽略同步的内存共享。",
                "producer 与 consumer 分别拥有可执行的队列端；重建或 reconnect 必须产生新 generation，"
                "旧 slot 不得跨代复用。",
                "以 dequeue/queue/acquire/release 的同代序列和 fence 状态判定；无 buffer 泄漏、死锁或"
                "销毁后继续提交才算生命周期闭合。",
            ),
            (
                "NativeWindow / ANativeWindow / OHNativeWindow",
                "供 EGL、Unity native renderer 等 C/C++ 生产者使用的 producer-Surface ABI façade；"
                "它把几何、格式、buffer dequeue/queue 操作暴露为 native 接口。",
                "不是 Android Window policy object，也不等同于 EGLSurface。",
                "wrapper 身份必须绑定一个确定的 producer Surface 与 generation；引用计数、connect/disconnect "
                "和宿主对象销毁必须对称。",
                "以真实 buffer dequeue/queue、格式/尺寸协商和销毁后的拒绝行为判定；仅能创建 wrapper 不算可渲染。",
            ),
            (
                "EGLSurface",
                "EGL 中绑定 NativeWindow 的渲染目标，使 OpenGL ES context 可以把结果提交到该 producer。",
                "不是 Android Surface 类，也不拥有窗口焦点、层级或 SceneSession。",
                "由 EGLDisplay/EGLContext 与目标 NativeWindow 的兼容配置共同约束；NativeWindow 换代时必须"
                "重建或显式重新绑定。",
                "eglCreateWindowSurface 与 eglSwapBuffers 成功只证明 EGL 提交边界；还需同帧 queue/present "
                "receipt 才能证明显示。",
            ),
            (
                "SurfaceControl",
                "面向合成器 layer 的控制句柄；通过原子 transaction 修改 layer 的位置、裁剪、透明度、"
                "层级、可见性和所挂 buffer。",
                "本身不承载像素，也不替代 BufferQueue producer。",
                "身份绑定 compositor layer/native object 与 generation；transaction apply、reparent 和 remove "
                "必须作用于同一存活 layer。",
                "以 transaction receipt 及对应 layer 状态/呈现结果判定；对已移除或错代 layer 的 mutation 必须失败。",
            ),
            (
                "RenderFrame / present receipt",
                "一次受 vsync 驱动、可跨 traversal、draw、buffer 与合成阶段关联的帧事务；receipt 是宿主已消费"
                "或呈现这一次事务的可核验证据。",
                "不是任意一行“frame done”日志，也不是进程 RSS 或函数返回值。",
                "帧身份至少包含 window/surface generation、frame sequence 与 vsync/时间戳；各阶段只能推进同一身份。",
                "同代链路完整且终点有 present/finish/像素证据才 PASS；丢帧、超时、错代或仅提交均应保持 NOT_PROVEN/FAIL。",
            ),
            (
                "SurfaceTexture",
                "以 BufferQueue 为生产端、以 OpenGL texture 为消费端的独立图形对象，常用于相机、视频或"
                "offscreen/texture-fed 内容；消费者通过 updateTexImage 获取新图像。",
                "不是普通顶层 Window 的别名，也不能继承 Window Surface 的验证结论。",
                "身份由 producer、GL texture、context attach 状态与 generation 构成；生命周期包括"
                "attach→frame available→update→detach/abandon。",
                "必须独立验证 attach/update/detach、context 切换、frame callback 与销毁失败；否则只能明确标为 typed unsupported。",
            ),
            (
                "SceneSession / hostSession",
                "OpenHarmony SceneBoard 管理窗口策略与宿主显示区域的会话对象；主 hostSession 通常由 Ability/"
                "SceneBoard 创建，并作为 Bridge 投影 Android Window 的宿主锚点。",
                "不是 Android IWindowSession，也不能因名称相似就承担 Android Window 语义。",
                "OH 是宿主策略 owner；Bridge 只保存经过认证、带 generation 的引用并进行可逆投影，不得秘密新建第二 owner。",
                "以 Ability 已有 hostSession 的 authenticated handoff、同代 callback 与 teardown 判定；"
                "legacy id 不能冒充成功；另建 specific child 必须显式归入 R1b 并验证 parent/child 双 identity，"
                "不得冒充 R1a direct reuse。",
            ),
        ],
        "nouns": [
            ("Fn04.C01 WindowRecord", "A03/A04/A07/A08/A09/A18/A19/A20", "caller session 与每窗口 identity、geometry、callback、destroy"),
            ("Fn04.C02 BufferQueueSurface", "A05/A12/A17", "producer、generation、buffer/fence；BLAST 独立判据"),
            ("Fn04.C03 NativeWindow", "A06/A10", "OH NativeWindow、ANativeWindow 与 EGLSurface 生命周期"),
            ("Fn04.C04 SurfaceControl", "A11/A14", "layer identity、transaction mutation/apply"),
            ("Fn04.C05 RenderFrame", "A02/A13/A15/A16", "vsync→traversal→draw→present/finish receipt"),
            ("Fn04.C06 SurfaceTexture", "A21", "GL consumer、attach/update/detach 或 typed unsupported"),
        ],
        "cases": [
            ("F04-H01", "p1612 / 25a0aa4", "VERIFIED_SOURCE_MECHANISM", "IWindowSession、OH session/surface、native-window、RS 与 EGL 同族形状；含 stub，不是设备 PASS。"),
            ("F04-H02/H03", "Anbox / ATL", "VERIFIED_WITH_BOUNDARY", "前者证明可逆 host-window projection；后者明确暴露非 subwindow type 不完整。"),
            ("F04-H04/H05", "libhybris / gfxstream", "VERIFIED_NATIVE_PATH", "独立证明 NativeWindow、buffer、EGL、fence 与 host-present 边界；compositor 身份不可照搬。"),
            ("F04-H06", "Wine", "VERIFIED_ANALOGY", "证明 foreign-window identity/geometry/teardown 的对称 projection；不是 Android/OH oracle。"),
            ("AOSP 14", "WMS/Surface/BLAST/SurfaceControl/Vsync oracle", "NORMATIVE_ORACLE", "定义 Android 应当观察什么，不是 A-on-B 成功案例。"),
            ("OH 6.1", "SceneBoard/ProducerSurface/NativeWindow/RS/NativeVSync", "HOST_CAPABILITY", "证明宿主原语存在，不自动等价。"),
            ("完整语料扫描", "62/62 sources · 6,608 raw hits · 0 errors", "SCAN_COMPLETE_NOT_EVIDENCE", "全量覆盖后逐源码升级；raw hit、目录存在和案例数量不计证据。"),
        ],
        "routes": [
            ("R1a", "直接复用对照假设", "Android top-level WindowRecord 直接复用 Ability hostSession；native 高频图形直连", "合同最简，但当前没有实现或 D600 行为证据。"),
            ("R1b", "当前证据领先假设", "Ability MainSession 作为认证 parent，Android top-level 使用独立 specific content child", "r18 已有身份、Surface/EGL/RS/像素窄证据；需裁决 child identity 是否满足透明语义。"),
            ("R2", "条件对照假设", "独立 native broker/add-on + 显式 IPC protocol", "隔离与诊断强，但增加高频 IPC、协议与生命周期成本。"),
            ("R3", "其他", "保留更完整 Android graphics stack，仅桥 compositor", "Android 保真高，系统体量与依赖闭包大。"),
            ("R4", "拒绝/局部 fallback", "OH UI/API 重实现或 offscreen copy", "不能作为透明 Unity 总路线；仅允许人类逐能力接受 bounded fallback。"),
        ],
        "route_details": [
            {
                "id": "R1a",
                "position": "合同基线对照；没有当前实现证据",
                "mechanism": "认证并复用 Ability/SceneBoard 主 hostSession；scoped IWindowSession façade "
                "承担有界 Android server 语义；Surface/EGL/RS/vsync 留在 native 数据面。",
                "for": "最贴合既定 ART + raw APK + appspawn-x 形态；不改 OH core；宿主 Window owner 仍在 "
                "SceneBoard；top-level 只有一个 OH session identity，focus/death/visibility ledger 最简单。",
                "against": "tracked worktree 仍是 legacy CreateWindow/AddWindow；frozen r18 artifact 也没有 direct reuse，"
                "而是另建 specific child。hostSession object handoff、Surface 绑定和 D600 行为全未证明。",
                "history": "F04-H01 p1612 提供同族 façade/native 边界；Anbox/Wine 支持可逆 host-window "
                "projection；libhybris/gfxstream 支持 native buffer/EGL/fence。ATL 的 subwindow 缺口是负证据。"
                "这些是多谱系源码 precedent，不是当前 D600 成功。",
                "experiment": "5eab live identity 对账直接证明 r18 不走 R1a：Ability MainSession=28，Android "
                "top-level 对应新 specific child=34。R1a 当前是 NOT_IMPLEMENTED/NOT_EXERCISED。",
                "needed": "只有存在 route-labelled R1a experimental artifact 后，才执行 D0 reachability、D1 hostSession "
                "identity/teardown、D2 BufferQueue/BLAST、D3 "
                "NativeWindow/EGL；D4 SurfaceControl；D5 present/pixel；D6 SurfaceTexture，均含正/负/失败例与独立复核。",
                "falsifier": "合法 hostSession handoff 不可得；必须依赖 WM_OK/no-op、parcel PID 安全绕过；"
                "或同代 buffer/transaction/finish 成立仍无 RS present/pixels。",
            },
            {
                "id": "R1b",
                "position": "当前证据领先；仍未达到人工主选资格",
                "mechanism": "以 Ability token 经 AMS 认证取得 MainSession persistentId，作为 parent；"
                "Android top-level WindowRecord 创建独立 APP_SUB_WINDOW specific session，持有真实 ISession、"
                "SurfaceNode、ProducerSurface 与 native/EGL 数据面。",
                "for": "不重复创建第二 MainSession；保留 Ability-owned parent；当前 frozen r18 已在 5eab "
                "证明 parent 28→child 34→RS node→producer→EGL→可见像素，远强于仅有源码形状的 R1a。",
                "against": "Android top-level 的 OH identity 是 child 34 而非 host 28；focus、geometry、visibility、"
                "death、teardown 和 recents 形成 parent/child 双 ledger；把 top-level 强制标成 subwindow 可能暴露 policy 差异。",
                "history": "OH specific-session/subwindow 与 host-window projection 案例支持 parented child 形状；"
                "ATL 的 subwindow 不完整性是直接警告。没有历史案例可替代本项目的 parent/child lifecycle 差分。",
                "experiment": "2026-07-25 cold run：recordId/MainSession=28；CreateAndConnectSpecificSession child=34；"
                "surfaceNodeId=38087769980929；producer uniqueId 与 EGLSurface 成立；RS occlusion 可见。exact loaded "
                "librender_service_base disassembly 证明没有 callingPid→client pid_ 安全 fallback。",
                "needed": "继续 D1 parent-survives/child-teardown、stale callback；D2 BLAST；D3 EGL negative；D4 "
                "transaction generation；D5 present/pixel/finish join；D6 SurfaceTexture，并测 focus/recents/back 对 parent-child 的影响。",
                "falsifier": "child 无法与 parent 同代认证；child 销毁污染 parent；focus/visibility/recents 与 Android "
                "top-level 语义持续差分；或必须依赖安全放宽/false success 才 present。",
            },
            {
                "id": "R2",
                "position": "条件候选；不能因 R1 尚未实现而自动升级",
                "mechanism": "独立 native broker/system add-on 持有 OH 资源和权限，app 侧通过显式 IPC "
                "传 window/surface/layer/frame identity、fence 与 terminal receipt。",
                "for": "权限、death、清理和多 app 隔离集中；协议和双侧 receipt 易审计；若 app process "
                "不能合法持有 host resource，可提供清晰的 ownership 边界。",
                "against": "多一跳 IPC 与双账本；buffer/fence/frame 高频时延、协议版本与恢复成本高；broker "
                "可能演化为第二 WMS/compositor，回滚还需 ledger migration。",
                "history": "Anbox 的 host/guest 分层和 gfxstream 的显式图形协议证明 broker 类结构可行；"
                "但没有与本项目 SceneBoard/appspawn-x 等形的本地完整实现，不能把邻域案例当直接成功。",
                "experiment": "没有 R2 broker artifact、service publication、permission、latency 或 D600 frame "
                "receipt；当前状态为 NOT_RUN，而不是失败或备选已证。",
                "needed": "先做 broker 启动/权限/death/recovery host probe，再与 R1 用相同帧负载比较 IPC "
                "latency、copy count、jank、wrong-generation、crash recovery 与像素终点。",
                "falsifier": "R1 可合法低开销访问全部宿主能力；或 R2 增加的 latency/jank、身份漂移、恢复"
                "复杂度超过冻结阈值。",
            },
            {
                "id": "R3",
                "position": "项目架构重选项；当前不具备近期开启资格",
                "mechanism": "保留 SurfaceFlinger/HWC/完整 Android graphics stack，只在 HWC/render-server "
                "边界桥到 OH compositor。",
                "for": "A 侧图形保真最高，BLAST、SurfaceTexture、SurfaceControl 多数留在原生 Android 实现；"
                "可减少逐 API 仿真。",
                "against": "把当前 raw APK/appspawn-x API bridge 扩成完整 Android 图形/系统单元，带来 namespace、"
                "display/input/security、资源和 first-class OH identity 冲突；可逆性最低。",
                "history": "Anbox/Waydroid/gfxstream 证明完整 guest graphics 可工作，也同时证明其成功依赖更大的 "
                "Android 运行闭包；这正是与当前 Project 边界不一致的证据。",
                "experiment": "未建立 R3 image、SurfaceFlinger/HWC closure 或 D600 资源/启动实验；NOT_RUN。",
                "needed": "只有项目级使命允许改变后，才值得做 image footprint、启动、内存、显示安全和 Unity "
                "差分基准；在此之前设备实验的信息收益低。",
                "falsifier": "项目继续坚持 ART/raw APK/appspawn-x first-class OH 形态，或整栈无法满足资源与安全约束。",
            },
            {
                "id": "R4",
                "position": "完整 Fn04 路线排除；仅保留具名局部实验",
                "mechanism": "在 OH UI/API 中重实现 Android window 语义，或把内容 offscreen/pbuffer 渲染后复制到宿主。",
                "for": "可以低成本验证个别 API、像素格式或 EGL 假设，也可能让极小目标暂时不崩。",
                "against": "Window/BLAST/SurfaceTexture/SurfaceControl 语义不完整，容易 app-specific；增加 copy、"
                "latency 与假上屏风险；长期维护成本高且违反透明运行目标。",
                "history": "ATL 的局部窗口实现和 pbuffer/offscreen 模式说明窄能力可做；其 subwindow/multisurface "
                "缺失恰好证明不能外推为完整兼容。",
                "experiment": "此前 graphics heuristic 的“PASS”已因没有像素 present 被 INVALIDATED；没有 R4 "
                "端到端 Unity 差分或性能证据。",
                "needed": "若某目标提出 bounded fallback，必须单独测像素差分、copy count、latency、交互和未支持 "
                "API；结果只能授予该目标/Action，不得成为 Fn04 总路线。",
                "falsifier": "任一 canonical Unity 需要未实现图形语义，或像素/交互差分、性能阈值失败。",
            },
        ],
        "route_gate": [
            ("R1a", "多谱系源码先例支持 direct projection", "5eab identity 对账证明 current r18 不走 R1a", "无 route-labelled artifact；NOT_EXERCISED", "否：证据不足，继续实验"),
            ("R1b", "specific-session 与 host projection precedent，含 ATL 负边界", "5eab parent28→child34→RS/EGL/像素；stock owner-check binary", "D1 teardown/focus 与 D2-D6 未完", "否：证据不足，继续实验"),
            ("R2", "邻域 broker precedent，缺同形实现", "无 broker artifact/permission/latency 结果", "NOT_RUN", "否：证据不足，继续实验"),
            ("R3", "完整 guest 图形有先例但产品边界不同", "无 D600 整栈 closure", "NOT_RUN", "否：证据不足，继续实验"),
            ("R4", "局部实现及负面边界有先例", "一次假阳性已作废", "端到端 NOT_RUN", "不适用：已排除为完整路线"),
        ],
        "primary": "R1b",
        "backup": "R1a",
        "recommendation": (
            "R1b 因 exact r18 device evidence 成为当前证据领先假设，但不是已选主线；R1a 是合同更简的 direct-reuse "
            "对照，却尚无 artifact。R2 仍需用同一负载做 ownership/latency/recovery 对照；R3 是项目架构重选，"
            "R4 仅允许具名局部 fallback。exact 5eab RenderService base 已证明未含 parcel-PID fallback。"
        ),
        "d600": [
            ("共同前置 G8 raw APK install", "PASS", "只证明安装链；不证明 Fn04。"),
            ("早期 Phase-9 G7 process fork", "FAIL（旧 generation）", "两板 app fork fail；该代 Fn04 为 NOT_RUN，不能外推到后续 artifact。"),
            ("AlexBridge r18 H07/H09 + click", "NARROW DEVICE FACT", "5eab 已有 MainActivity、真实 HelloWorld 像素和一次点击；不含 Window/Surface/frame route ledger。H05 PARTIAL、H06 NOT_PROVEN、H08 NOT_RUN。"),
            ("Fn04 live parent/child identity", "R1b NARROW DEVICE FACT", "Ability/MainSession=28；specific content child=34；RS node/producer/EGL/occlusion 同代。严格 R1a 未执行。"),
            ("RenderService owner-check provenance", "STOCK CHECK PROVEN", "exact loaded base hash/BuildID/disassembly 无 callingPid==0→client pid_ fallback；forged-PID negative 仍待做。"),
            ("G5 graphics heuristic", "INVALIDATED", "一次所谓 PASS 来自 RSSurfaceNode teardown，非像素 present，已判 false positive。"),
            ("Fn04 D0-D6", "PARTIAL", "R1b D0/部分 D1-D5 identity path 已有窄证据；teardown/focus/negative、BLAST、frame receipt join、SurfaceTexture 未完。"),
        ],
        "final": (
            "现在不请求人工选择路线。优先继续 R1b 的 parent/child teardown、focus 与 frame receipt join；"
            "R1a 只有在生成 direct-reuse artifact 后才做公平同负载对照。随后再比较 R2 ownership/latency/recovery，"
            "并关闭 BLAST、SurfaceTexture 与 forged-PID negative；证据门满足后再提交路线裁决。"
        ),
        "eligible": False,
        "gate": "路线裁决关闭：R1b 有窄 device lead 但 D1-D6 未闭合；R1a/R2 尚无同负载 artifact 对照。",
    },
    "Fn05": {
        "name": "Input",
        "question": "OH 输入怎样进入 Android 标准 InputChannel，并保持 target、线程和完成回执？",
        "definition": (
            "Fn05 要保留 Android InputChannel、InputEventReceiver/ViewRoot owner Looper、"
            "事件字段/时序与 FINISHED 语义。触摸由 OH hit-test target/window/transform "
            "generation 准入；key/joystick 才由 confirmed focus epoch 准入。"
        ),
        "connect": (
            "Connect 是同一事件从 OH MMI id 到 Android seq、owner-Looper View callback、"
            "Android FINISHED 的可逆事务。OH MarkProcessed 只是 host receipt，不能冒充 "
            "Android FINISHED，而且对已送入 Android 的事件必须由匹配 FINISHED 因果触发。"
            "A04 仅覆盖 IME lookup object/type、identity/descriptor 与 "
            "caller scope；任何 operational method 都在范围外。"
        ),
        "terms": [
            (
                "InputChannel",
                "Android 输入分发器与应用消费者之间的有序事件传输端点；channel pair 把 target 确定的事件"
                "交给一个消费方，并承载完成回执。",
                "不是任意 socket 或 callback；能够写入字节不等于符合 Android 输入协议。",
                "身份由 endpoint token、target window、consumer 与 generation 限定；只能有一个有效 reader，"
                "attach、drain、close 必须在 owner Looper 上闭合。",
                "以同代 send→consume→FINISHED 序列、关闭后拒绝与无重复消费判定。",
            ),
            (
                "InputEvent",
                "Android 可观察的 typed 输入值，包含事件种类、device/source、时间、action、key 或 pointer "
                "字段、坐标/pressure/axis、meta state 与 sequence。",
                "不是只有 x/y 的触摸点，也不是可无损互换的 OH PointerEvent 名称。",
                "转换层拥有 OH id↔Android seq 的暂态映射；事件进入 InputChannel 后由 Android receiver/ViewRoot "
                "消费，字段缺失必须显式报告 loss。",
                "用字段矩阵、顺序、重复/丢失、multi-pointer 和 negative conversion case 验证。",
            ),
            (
                "InputFocus",
                "决定 key、joystick 等 focus-routed 输入当前应投递到哪个 Android window 的已确认状态。",
                "不是调用 requestFocus 后的乐观布尔值，也不用于替代 pointer hit-test。",
                "宿主确认产生 focus epoch；Bridge 只接受与 window generation 匹配的 confirmed epoch，并在"
                "窗口切换/销毁时失效。",
                "key/joystick 只有在正确 epoch 下送达；旧焦点、未确认焦点和失活 window 必须被拒绝。",
            ),
            (
                "Hit-test target / transform generation",
                "OH 命中测试选中的目标窗口以及把宿主坐标变换为该 Android window 局部坐标的同代几何状态。",
                "不是 InputFocus，也不能用全局坐标直接替代。",
                "target 与 transform 继承 Fn04 WindowRecord generation；resize/rotation/insets 改变时必须换代。",
                "pointer 以命中 target 和同代变换准入；错窗、错代、越界和旋转坐标负例必须可观察。",
            ),
            (
                "owner Looper",
                "创建并拥有 InputEventReceiver/ViewRoot 的 Android 消息循环；它规定 callback 的线程亲和性和顺序。",
                "不是任意可执行 callback 的线程池或临时 Handler。",
                "receiver 从 attach 到 dispose 始终绑定同一 Looper；跨线程转交必须保持事件顺序与 teardown barrier。",
                "callback 线程 id、顺序、销毁后零回调以及阻塞/超时行为构成判据。",
            ),
            (
                "FINISHED receipt",
                "Android 消费方对特定 input sequence 的终局回执，表明事件已处理或明确未处理，并允许分发端回收状态。",
                "不是 OH MarkProcessed；两者位于不同语义边界，不能相互冒充。",
                "Bridge 持有双 receipt ledger：OH_PROCESSED 与 ANDROID_FINISHED 各自带 id/seq/generation/timeout；"
                "Android FINISHED 必须先发生，才允许触发对应 OH MarkProcessed。",
                "每个已投递事件恰有一个匹配 FINISHED；阻塞 owner 时 OH 不得提前确认；重复、丢失、错 seq 与超时必须独立判定。",
            ),
            (
                "InputMethodService（当前仅 lookup）",
                "Android 文本输入服务的 Binder 接口族；本 Concept 当前只承诺返回身份、descriptor 和 caller scope "
                "正确的 lookup object，不承诺任何输入法操作。",
                "不是“有一个非空 Binder 就等于 IME 可用”。",
                "lookup identity 由 service name、caller 与 binder generation 限定；首次 operational method 必须另建稳定 Action。",
                "仅验证 lookup、descriptor、identity、未授权 caller 和 operational call 的 typed unsupported。",
            ),
        ],
        "nouns": [
            ("Fn05.C01 InputChannel", "A02/A05", "generation-bound channel pair、consumer attach、drain/close"),
            ("Fn05.C02 InputEvent", "A01/A03/A07/A08/A09", "typed conversion、pointer/key branch、owner Looper、dual receipts"),
            ("Fn05.C03 InputFocus", "A06", "focus request 与 confirmed epoch；只 gate focus-type input"),
            ("Fn05.C04 InputMethodService", "A04", "lookup-only identity/descriptor/caller scope；无 operational method"),
        ],
        "cases": [
            ("F05-H01", "p1612 / 25a0aa4", "VERIFIED_SOURCE_MECHANISM", "OH MMI→typed InputMessage→InputChannel，并独立观察 FINISHED；diagnostic/partial 路径仍在。"),
            ("F05-H02", "Anbox / ddf4c57", "VERIFIED_CONDITIONAL_ALT", "SDL→evdev→guest Android 证明 R2 真实；边界无 FINISHED，且依赖 device/permission closure。"),
            ("F05-H03", "ATL / 1f041f5", "VERIFIED_WITH_NEGATIVE", "GDK→AInputEvent→pipe→ALooper 支持 owner-loop；multitouch 缺失且 finishEvent 为空。"),
            ("F05-H04/H05", "Wine / p1613", "ANALOGY_AND_GOVERNANCE", "前者支持 owner-thread/focus；后者只支持 Java shim→native 的治理方向。"),
            ("完整语料扫描", "62/62 sources · 6,966 raw hits · 0 errors", "SCAN_COMPLETE_NOT_EVIDENCE", "全量扫描后逐源码升级，未把关键词命中伪装成案例。"),
        ],
        "routes": [
            ("R1", "推荐实验假设", "native typed conversion→标准 InputChannel→receiver/ViewRoot owner Looper", "热路径与 Android 语义最佳；IME 仍严格 lookup-only。"),
            ("R2", "条件对照假设", "evdev/uinput→Android InputReader/InputDispatcher", "只有完整 service/device/permission closure 存在时成立。"),
            ("R3", "诊断 shim", "Java Handler/reflection broker", "仅作时间有界诊断；不能成为 Unity 高频主线。"),
            ("R4", "拒绝", "OH 重实现 Android View/InputDispatcher/IME", "重复 guest 语义，长期漂移。"),
            ("R5", "拒绝", "完整 Android container/device passthrough", "改变 Project 的 API-bridge 运行形态。"),
        ],
        "route_details": [
            {
                "id": "R1",
                "position": "当前推荐假设；未达到人工主选资格",
                "mechanism": "OH MMI 事件在 native 边界逐字段转换，经标准 Android InputChannel 到 "
                "InputEventReceiver/ViewRoot owner Looper，并分别记录 OH_PROCESSED 与 ANDROID_FINISHED。",
                "for": "最短高频路径；复用 Android View、Looper 和 FINISHED 语义；改动集中于 OS boundary；"
                "event id↔seq、focus epoch、window generation 可在有界 ledger 内验证。",
                "against": "deployed binary/source provenance 仍漂移；Enforcing system barrier 已证明当前 "
                "MarkProcessed 领先 FINISHED 约 11.5 s；target/focus generation、repaired receipt ordering "
                "和完整 T01-T09 尚无 D600 闭环，IME 只覆盖 lookup。",
                "history": "F05-H01 p1612 直接支持 MMI→InputChannel→FINISHED；ATL/Wine 支持 owner-loop/thread。"
                "这些加强机制可信度，但包含 partial attach/ACK 等负面边界。",
                "experiment": "5eab r18 低扰动单击已把 R1 功能链钉实：OH MMI session34 DOWN/UP→Android "
                "main TID8868 seq1/2；server-side ACK monitor TID8892 观察到 FINISHED，"
                "它不是 receiver worker。socketpair fd 与 parent focus28/child34 前后稳定。"
                "后续 non-main receiver 双 barrier 在 Enforcing 下通过：main 阻塞时 owner TID12709 "
                "收到 seq5101；owner 阻塞时 main 活跃且 750ms 无提前 callback，释放后才收到 seq5102；"
                "二者均返回 handled FINISHED。随后 system-main 12 s barrier 把 OH event1399/1400 "
                "与 Android seq1/2 按 actionTime join：OH ANR timer 在 barrier 内删除，Android "
                "dispatch/FINISHED 约 11.5 s 后才发生，明确命中 early-ACK 缺陷。owner affinity 与 "
                "双账本可观察性已闭合，但 completion ordering FAIL；deployed 0-worker binary 与 "
                "generation 声明的 worker/Handler source 仍漂移。",
                "needed": "恢复 deployed runtime 的准确可重建源码；再完成 channel lifecycle、two-window focus、"
                "touch/key 字段矩阵、FINISHED-gated MarkProcessed repair、receipt negatives、teardown、"
                "lookup-only IME 与 sustained Unity input。",
                "falsifier": "同 artifact 下标准 receiver fd 可稳定 publish 但不能唤醒 owner Looper，或 ABI/"
                "字段/seq/receipt 无法无损闭环且只能靠永久 Java shim。",
            },
            {
                "id": "R2",
                "position": "条件候选；当前产品 closure 已证伪",
                "mechanism": "把 OH 输入转换为 evdev/uinput，进入 Android InputReader/InputDispatcher，再走标准分发。",
                "for": "接近物理输入设备，能复用 Android policy、gesture、wait queue、focus 和完整分发状态机。",
                "against": "依赖 InputReader/InputDispatcher service、device node、SELinux/capability 和 system_server "
                "闭包；可能实质扩大成容器，且跨边界 FINISHED 仍需补。",
                "history": "F05-H02 Anbox 源码证明 SDL→evdev→guest Android 路径真实，也暴露 host boundary "
                "没有 FINISHED 和依赖完整 guest services 的限制。",
                "experiment": "source/build/device inventory 已完成：minimal AOSP build 禁用 inputflinger target，"
                "产品明确无 Android system_server；5eab 有 OH uinput_inject/multimodalinput 与设备节点，但穷举 "
                "/proc task 没有 InputReader/InputDispatcher，app 也没有 input/uinput fd。当前 R2=NOT_ELIGIBLE。",
                "needed": "只有产品决定增加 Android system-service/inputflinger closure 后，才重新核验 owner maps、"
                "event fd、权限，并与 R1 同事件集比较字段、target、latency、backpressure、FINISHED 与 teardown。",
                "falsifier": "目标 image 无所需 service/device/permission，补齐等价于完整 Android 系统，或必须绕过 SELinux。",
            },
            {
                "id": "R3",
                "position": "仅诊断对照，不得作为主选",
                "mechanism": "native conversion 后通过 Java Handler(mainLooper)/reflection 将事件送入受控入口。",
                "for": "改动小、易观察主线程假设、可快速隔离 native fd 与 callback 问题，且删除成本低。",
                "against": "多一条 Java queue；reflection/hidden API、顺序、ACK owner 和高频 Unity move 性能会漂移；"
                "违反长期 native 热路径纪律。",
                "history": "F05-H01 现有 diagnostic 形状与 p1613 shim-retirement 只支持“限时诊断并移除”，"
                "没有历史依据支持其成为永久架构。",
                "experiment": "现有代码形状已发现，但没有 hash-bound D600 latency/drop/ACK 对照；不得把代码存在记 PASS。",
                "needed": "只作为 R1 对照 artifact，量测 callback TID、post latency、drop、exception、seq 与 ACK；"
                "预先冻结删除条件。",
                "falsifier": "任何高频性能、顺序或 ACK ownership 不满足；即使窄实验通过，也只结束诊断任务，不升级主线。",
            },
            {
                "id": "R4",
                "position": "路线排除",
                "mechanism": "在 OH WMS/MMI/ArkUI 内重写 Android event/View/InputDispatcher/IME 语义。",
                "for": "可直接使用 OH 原生输入能力，表面上减少跨运行时调用。",
                "against": "必须复制 pointer/gesture/focus/InputConnection/ACK 大状态机，形成第三套语义 owner；"
                "测试与版本维护面最大，违反 AOSP 黑盒边界。",
                "history": "完整语料没有同族透明成功案例；局部 toolkit 映射的字段和 multitouch 缺口构成负证据。",
                "experiment": "无 R4 prototype 或 D600 差分数据；当前没有理由为它消耗实现型设备实验。",
                "needed": "只有 Project 边界改变后才重开；届时必须对 AOSP 全事件矩阵与 OH 原生回归做差分。",
                "falsifier": "最小目标需要未复制的 Android 输入状态，或 differential test 出现持续漂移。",
            },
            {
                "id": "R5",
                "position": "项目边界排除",
                "mechanism": "完整 Android container/device passthrough 持有输入设备和 guest input stack。",
                "for": "guest 内 Android 输入保真较高，成熟容器可复用既有服务。",
                "against": "改变 ART/raw APK/appspawn-x API bridge 使命，不能复用当前 BMS/first-class OH app 决策，回滚成本高。",
                "history": "Anbox/Waydroid 证明容器路线可行，也明确其成功条件与本项目形态不同。",
                "experiment": "未在 D600 建立 container；NOT_RUN，且当前使命下无需先做。",
                "needed": "仅在项目级重新定义运行形态后评估资源、安全、启动、输入与应用身份。",
                "falsifier": "项目继续坚持 API bridge 与 first-class OH app 身份。",
            },
        ],
        "route_gate": [
            ("R1", "直接同族源码先例较强", "5eab seq1/2 FINISHED；non-main owner PASS；system barrier join event1399/1400↔seq1/2，但 OH 提前约11.5s确认；binary/source drift", "owner affinity/双账本可观察 PASS；completion ordering FAIL；T01-T09 未完", "否：证据不足，继续实验"),
            ("R2", "Anbox 直接先例但依赖完整 guest closure", "source/build/device inventory=NOT_ELIGIBLE；无 Android InputReader/InputDispatcher", "无需注入（消费侧缺席）", "否：证据不足，继续实验"),
            ("R3", "仅 shim/诊断历史", "现有代码形状≠运行结果", "对照 NOT_RUN", "禁止主选"),
            ("R4", "无同族透明成功；有负面边界", "无 prototype", "NOT_RUN", "排除"),
            ("R5", "容器案例成熟但任务边界不同", "无 D600 container", "NOT_RUN", "项目边界排除"),
        ],
        "primary": "R1",
        "backup": "R2",
        "recommendation": (
            "历史证据只足以把 R1 排为首个实验假设；R2 必须先关闭 service/device/permission "
            "closure，再与 R1 同台比较。R3 只作有期限诊断对照，R4/R5 不进入当前路线裁决。"
            "在 T01-T09 完成前不请求人工接受 R1。"
        ),
        "d600": [
            ("早期 Phase-9 G7 process fork", "FAIL（旧 generation）", "该代没有 ViewRoot，Fn05 为 NOT_RUN；不能外推到后续 r18。"),
            ("AlexBridge r18 InputChannel click", "NARROW FUNCTIONAL PASS", "session34 DOWN/UP→Android main seq1/2→ACK monitor TID8892 FINISHED；TID8892 不是 receiver worker。该 run 为 Permissive；non-main owner affinity 由下一条 Enforcing 实验另行关闭。"),
            ("Fn05 non-main owner barrier", "FUNCTIONAL PASS", "5eab/r18/Enforcing：main-blocked seq5101 在 Fn05Owner TID12709 callback+FINISHED；owner-blocked seq5102 在 750ms 内无提前 callback，释放后 callback+FINISHED。OH MarkProcessed 未覆盖。"),
            ("Fn05 system receipt barrier", "NEGATIVE PASS / PRODUCT FAIL", "5eab/r18/Enforcing：OH event1399/1400 与 Android seq1/2 按 actionTime join；Android main 阻塞时 OH timer 已删除，约11.5s 后 main 释放才 dispatch+FINISHED。"),
            ("Fn04 live WindowRecord ledger", "NOT_PROVEN", "r18 有像素但没有 Fn04 同代 identity ledger；Fn05 路线实验仍需显式继承。"),
            ("Fn05 T01-T09", "PLANNED_NOT_RUN", "channel、focus、pointer、key、dual receipt、teardown、lookup-only IME、Unity sustained input。"),
            ("R2 source/build/device closure", "NOT_ELIGIBLE", "OH MMI/uinput 存在；Android InputReader/InputDispatcher、system_server/inputflinger 不存在，app 无 evdev/uinput fd。"),
        ],
        "final": (
            "现在不请求人工选择。R2 当前产品 closure 已在源码、构建和 5eab 设备三层证伪，不再浪费注入实验；"
            "R1 已有 basic click/FINISHED 窄 PASS，且 non-main receiver 双 barrier 已在 Enforcing 下关闭 owner affinity。"
            "system barrier 又关闭了双账本身份歧义，并实证当前 OH 提前约11.5s确认。"
            "下一步优先恢复准确实现源码，完成 FINISHED-gated MarkProcessed repair、receipt negatives 和 "
            "T01-T09 其余矩阵。只有 pointer/key 分流、"
            "双 receipt、teardown 与 sustained Unity 证据齐全，才提交路线决策。"
        ),
        "eligible": False,
        "gate": "路线裁决关闭：Fn05 缺 T01-T09 D600 证据；R2 在当前产品 closure 中 NOT_ELIGIBLE，除非人工接受拓扑扩张。",
    },
    "Fn06": {
        "name": "Intent / Task",
        "question": "谁拥有 Android Task 语义，OH 只承载什么 host projection？",
        "definition": (
            "Fn06 保留 Intent typed value、Android Task identity/ordered Activity membership、"
            "launch flags/policy、foreground/remove 与 OH→Android launch transaction。Want、"
            "Mission 和 Ability 是 host capability，不是名字相似就自动等价。"
        ),
        "connect": (
            "Connect 是 typed Intent→一个 Task semantic owner→host command→authenticated "
            "callback→LaunchActivityItem 的链。同步 Android START_* result 与异步 "
            "schedule/onCreate receipt 分开。"
        ),
        "terms": [
            (
                "Intent",
                "Android 组件间请求的 typed Parcelable 值，包含 action、data/type、categories、component、"
                "flags、ClipData 与带类型的 extras。",
                "不是字符串化参数包；字段名称相似也不保证能无损转换为 OH Want。",
                "调用方创建值，Task/Activity 路由 owner 解释其语义；跨边界转换必须记录字段、类型和 loss receipt。",
                "用 round-trip 字段矩阵、unsupported type、malformed parcel 与权限负例验证。",
            ),
            (
                "Want",
                "OpenHarmony 启动 Ability 的宿主请求值，是 Bridge 发出 host command 的载体。",
                "不是 Android Intent 的语义 owner，也不天然实现 Android flags、selector、ClipData 或 Task policy。",
                "Bridge 生成并关联 Intent transaction id；OH framework 消费 Want，callback 必须带可认证关联标识。",
                "转换成功与 Ability 启动成功分开观察；字段 loss、伪造 callback 与异步失败必须显式。",
            ),
            (
                "Task",
                "Android 用户可观察的 Activity 历史栈与导航单元，拥有稳定 taskId/user/generation、ordered "
                "Activity membership、affinity、launch flags、前后台和移除状态。",
                "不是单个 Activity、进程或 OH Mission 的同义词。",
                "必须只有一个 Android Task semantic owner 串行化 mutation 并持久化/恢复；OH 只承载 host projection。",
                "用多 Activity 顺序、CLEAR_TOP/NEW_TASK、foreground、remove、重启恢复与同 taskId 关联验证。",
            ),
            (
                "Mission / UIAbility host projection",
                "OpenHarmony 对宿主 UIAbility 实例及其任务展示的管理能力；在本路线中用于承载一个 Android "
                "Task 的可见宿主投影。",
                "不是 Android Task 本体，不能因能前后台切换就接管 Android back stack policy。",
                "OH 持有 host token/session；Task authority 持有 Android 成员与 policy，并维护一对一、可恢复的 projection ledger。",
                "host callback 必须认证并关联 task generation；孤儿 Mission、重复 host 或错 task callback 必须被检测。",
            ),
            (
                "ActivityLaunchTransaction",
                "从已解析的 Android launch 请求到 ActivityThread 执行 LaunchActivityItem/onCreate 的有身份、"
                "有阶段、可回执事务。",
                "不是 StartAbility 返回成功，也不是打印出 Activity 类名。",
                "Task authority 生成 transaction id 和 Android token；host command 与 callback 只是中间阶段，"
                "ActivityThread 才执行 Android lifecycle。",
                "同步 START_*、异步 schedule、onCreate/exception receipt 分层判定；任一阶段超时或错 token 不得算启动。",
            ),
            (
                "Task semantic owner",
                "对 Task identity、成员顺序、launch policy、journal、恢复与并发 mutation 拥有最终裁决权的唯一组件。",
                "不是散落在 Bridge、SceneBoard 与 ActivityThread 中的多份 shadow state。",
                "owner 必须具名、单写者、可恢复并有 lock/permission 边界；projection broker 只翻译，不可成为第二 owner。",
                "通过并发启动、崩溃恢复、重复 callback、journal replay 与 owner 失效时的 fail-closed 行为验证。",
            ),
        ],
        "nouns": [
            ("Fn06.C01 Intent", "A01/A02/A04", "typed fields、extras、loss receipt 与 Want conversion"),
            ("Fn06.C02 Task", "A03/A05/A06", "taskId/user/generation、ordered members、foreground/remove"),
            ("Fn06.C03 ActivityLaunchTransaction", "A07", "OH token/record→Android token→ActivityThread transaction"),
        ],
        "cases": [
            ("F06-H01/H02", "p1612 boundary + legacy Mission patch", "DIRECT_AND_NON_TARGET", "typed start/reverse transaction 是直接先例；旧 MissionListManager hook 对 current SceneBoard 不可达。"),
            ("F06-H03", "ATL", "VERIFIED_WITH_NEGATIVE", "局部 Intent/CLEAR_TOP 可行，但 moveTaskToFront 为空，不能承担完整 Task。"),
            ("F06-H04/H05", "Anbox / Waydroid", "VERIFIED_CONTAINER_BOUNDARY", "薄 host launch 有效，因为完整 guest Android 保留 Task owner；container 形态不采用。"),
            ("F06-H06/H07", "VirtualApp / DroidPlugin", "VERIFIED_ANALOGY", "前者证明单一 Task owner，后者证明 typed proxy envelope；都不是 OH projection。"),
            ("完整语料扫描", "62/62 sources · 6,136 raw hits · 0 errors", "SCAN_COMPLETE_NOT_EVIDENCE", "另读两个 registry 外的 19.53 内嵌仓；所有引用带 commit/path/line。"),
        ],
        "routes": [
            ("R1", "推荐资格实验", "privileged AndroidTaskAuthority sidecar + TaskProjectionBroker + one OH host per Task", "语义最好；先闭合 process/dependency/lock/journal/recovery/permission 与 one-host sufficiency。"),
            ("R2", "候选对照实验", "target-reachable SceneBoard/UIAbility-manager core extension", "旧 MissionListManager patch 不可作为 target evidence；需要 exact hook 与回归/迁移责任。"),
            ("R3", "其他", "adapter-owned shadow Task ledger", "可逆但再次重实现 Task policy，易漂移。"),
            ("R4", "拒绝为完整路线", "direct per-Activity StartAbility", "可做 A01/A02/A04/A07 probe，不能满足 Task identity/order。"),
        ],
        "route_details": [
            {
                "id": "R1",
                "position": "首个资格实验假设；尚非主选",
                "mechanism": "一个长期、特权 AndroidTaskAuthority sidecar 持有有界 AOSP Task policy/state；"
                "TaskProjectionBroker 把每个 Android Task 投影到一个 SceneBoard UIAbility/Mission host。",
                "for": "AOSP 仍是唯一 Task semantic owner；不在 OH core 手抄 ActivityStarter；多 Activity 保留 A 侧顺序；"
                "差分测试直接，host projection 可回滚。",
                "against": "sidecar executable/process、依赖闭包、服务发布、lock、journal/recovery 和 Mission 权限均未证明；"
                "可能膨胀成 partial system_server；one-host-per-Task 是否能承载 recents/window 也未知。",
                "history": "VirtualApp 最强地支持单一 Task owner；Anbox/Waydroid 证明薄 host projection 在完整 guest "
                "owner 存在时成立；p1612 只证明 typed start/reverse boundary。没有同形 sidecar 的 D600 先例。",
                "experiment": "source/build closure 已执行：当前树无 AndroidTaskAuthority/TaskProjectionBroker、"
                "sidecar target/发布/权限，也无 server-side ATMS/ActivityStarter/Task 闭包；R1 当前产品=NOT_ELIGIBLE。"
                "r18 只证明 explicit Activity onCreate/onResume，topology 与 Probe 0-5 未执行。",
                "needed": "先形成可编译的具名 sidecar/broker、最小 AOSP dependency graph 与 permission receipt；再做 Intent/Want 字段矩阵、"
                "A→B→C Task ladder、foreground、reverse transaction、crash recovery 和 one-host count。",
                "falsifier": "最小闭包需要 broad system_server/WMS/AMS owner、服务无法向 appspawn-x 发布、"
                "权限不可合法取得，或 one-host-per-Task 在不改 OH core 时不可成立。",
            },
            {
                "id": "R2",
                "position": "候选对照；revised hook 可做 observation-only 资格实验",
                "mechanism": "在 target-reachable SceneBoard/UIAbilityLifecycleManager 核心中实现冻结的 Android Task 子集。",
                "for": "直接复用 OH lifecycle、recents、Mission persistence；对窄双 Activity demo 的路径可能较短。",
                "against": "复制 Android policy 到快速变化的 OH core，形成第二 owner；锁、持久化、迁移与 native 回归面广；"
                "每个 launchMode/flag 分支都产生长期差分负担。",
                "history": "旧 MissionListManager patch 提供 selected-flag 算法和故障教训，但 D600 SceneBoard 路径绕过该 hook；"
                "所以是历史原型和负证据，不是 R2 target evidence。",
                "experiment": "旧 MissionListManager hook 已证明对 SceneBoard target 静态不可达。revised hook 的精确入口 "
                "UIAbilityLifecycleManager::NotifySCBToStartUIAbility 与 abilityms 构建落点已定位；"
                "observation-only patch/contract 已冻结且通过 /opt/Bridge source mirror 的 git apply --check。"
                "因项目内没有完整 OH platform build tree，abilityms build/deploy 仍 NOT_RUN。",
                "needed": "先以 semantics-neutral marker 验证 Android start 可达且 stock OH start 不受污染；通过后再冻结行为子集，"
                "对 AOSP14 做 flag/launchMode/affinity 差分，"
                "执行 OH native regression、冷启动 persistence/migration 和 D600 正负/失败用例。",
                "falsifier": "所需修改无界扩散，任一接受行为持续差分，或 OH native regression/persistence 失败。",
            },
            {
                "id": "R3",
                "position": "可逆探索路线；不能因容易写而成为默认",
                "mechanism": "adapter service 自己维护明确受限的 shadow Task ledger，只调用公开 OH Mission 能力。",
                "for": "不改 OH core；mapping、状态与回滚显式；可以快速探测 host capability，并可能成为 R1 原型。",
                "against": "这是第三套 Task 实现；policy、并发、持久化和版本差异都变成项目负担，极易偏离 AOSP oracle。",
                "history": "ATL 的局部 CLEAR_TOP 和客户端虚拟化案例说明小 ledger 可做；ATL 的 moveTaskToFront 空实现"
                "证明局部成功不能外推为完整 Task。",
                "experiment": "无冻结 subset、ledger artifact 或 D600 differential result；NOT_RUN。",
                "needed": "若作为实验，必须先冻结最小 subset，并与 AOSP14 同输入差分；scope 首次扩张或重复漂移即终止。",
                "falsifier": "最小 Unity/SDK 集超出冻结 subset，或 differential test 重复出现 policy divergence。",
            },
            {
                "id": "R4",
                "position": "仅 Intent/launch 诊断；完整 Fn06 排除",
                "mechanism": "Intent 转 Want 后直接 StartAbility，让 OH 为每个 Activity 按自身策略创建 Ability/Mission。",
                "for": "宿主 primitive 已存在，成本低；可验证 A01/A02/A04/A07 的转换、启动和反向 callback。",
                "against": "没有 Android Task semantic owner，不能保证 taskId、ordered stack、move-to-front、CLEAR_TOP/"
                "NEW_TASK；最容易产生“Activity 启动了所以 Task 通过”的假阳性。",
                "history": "p1612 与 ATL 证明直接启动 primitive 可达，同时 ATL moveTaskToFront 为空是明确负证据。",
                "experiment": "早期 G7 失败；后续 r18 explicit launcher start 已到 MainActivity onCreate/onResume，"
                "可作为 direct-launch primitive 窄证据，但所有 Task 用例仍 NOT_RUN。",
                "needed": "只可执行 Probe 1/2/5 作为 boundary 诊断；结果不得授予 Fn06 Task 路线资格。",
                "falsifier": "任何需要稳定 task identity、成员顺序或 foreground existing task 的用例。",
            },
        ],
        "route_gate": [
            ("R1", "semantic-owner 历史原则较强，缺同形 sidecar", "source/build closure=NOT_ELIGIBLE；无 target/发布/权限/server subset", "Probe 0-5 无法进入", "否：证据不足，继续实验"),
            ("R2", "旧 patch 为非 target 原型/负证据", "旧 hook PROVEN_UNREACHABLE；revised observation patch source-check PASS", "abilityms build/device NOT_RUN", "否：证据不足，继续实验"),
            ("R3", "局部 ledger/虚拟化类比，完整性弱", "无 artifact/subset", "NOT_RUN", "否：证据不足，继续实验"),
            ("R4", "直接启动 primitive 有源码与 r18 窄证据", "r18 MainActivity onCreate/onResume；无 Task owner", "Task cases NOT_RUN", "不适用：已排除为完整路线"),
        ],
        "primary": "R1",
        "backup": "R2",
        "recommendation": (
            "R1 只作为信息增益最高的首个资格实验，不是主选；先证明 sidecar/broker 拓扑有界。"
            "并行用低成本源码/build probe 查 R2 exact target hook。R3 只可做冻结 subset 的差分实验，"
            "R4 只验证 Intent boundary。完成 Probe 0-5 前不交给人类选路线。"
        ),
        "d600": [
            ("共同前置 G8 raw APK install", "PASS", "只证明 raw APK 安装，不证明 Intent/Task。"),
            ("早期 Phase-9 G7 Activity", "FAIL（旧 generation）", "该代 app fork fail，Fn06 为 NOT_RUN。"),
            ("AlexBridge r18 explicit Activity", "NARROW DEVICE FACT", "launcher 已到 MainActivity onCreate/onResume；不证明 Intent 字段或 Task 语义。"),
            ("R1 source/build topology closure", "NOT_ELIGIBLE", "无 sidecar executable/startup/service/permission 或 bounded AOSP Task server subset。"),
            ("R2 target hook eligibility", "SOURCE PATCH CHECK PASS", "锁前只读 FN06_R2_OBS_V1 patch 已冻结；完整 abilityms build tree 不在 /opt/Bridge，build/device 未执行。"),
            ("Probe 0-5", "PLANNED_NOT_RUN", "authority identity、Intent/Want matrix、explicit Activity、Task ladder、foreground、reverse launch。"),
        ],
        "final": (
            "现在只授权继续实验，不请求人工路线选择。R1 当前产品 topology 已判 NOT_ELIGIBLE；"
            "下一步在 generation-exact build closure 进入 /opt/Bridge 后构建 revised R2 observation-only hook，并执行 reachability/non-interference，"
            "再决定是否值得进入行为型 patch。共同 Probe 1-5 仍必须给出同代、可复核结果；"
            "再按相同指标提交路线建议及未解决风险。"
        ),
        "eligible": False,
        "gate": "不可 accepted：R1 当前产品不具备 topology/permission closure；R2 只到 exact hook build-probe 资格，尚无 D600 receipt。",
    },
    "Fn07": {
        "name": "Android Service",
        "question": "Android Service 生命周期与 Binder publication 怎样通过有效 OH ServiceExtension 承载？",
        "definition": (
            "Fn07 保留 Service resolve/create/start/bind/publish/fan-out/unbind/rebind/stop/"
            "stopSelf/death/restart/destroy，以及 ServiceConnection callback 与 Binder identity。"
            "它不是四个 ActivityManager 方法直接映射，也不是一个 singleton registry。"
        ),
        "connect": (
            "R1 中 bounded ServiceLifecycleAuthority 是真实 semantic owner；ActivityThread "
            "执行 Android callback；OH 拥有 ServiceExtension token/ConnectionRecord。非空 "
            "onBind 先发布 authenticated IRemoteObject envelope，再恢复 exact local Binder；"
            "null onBind 产生 onNullBinding。"
        ),
        "terms": [
            (
                "Android Service",
                "无用户界面的 Android 组件，由系统语义 owner 按 ComponentName 解析并驱动 create、start、bind、"
                "unbind/rebind、stop、death/restart 与 destroy；可同时承载 started 和 bound 状态。",
                "不是后台线程、singleton 对象或四个 ActivityManager 方法的直接映射。",
                "ServiceLifecycleAuthority 持有 service record/startId/binding 状态；ActivityThread 在组件线程"
                "执行 onCreate/onStartCommand/onBind 等 callback。",
                "以 callback 顺序、startId、stopSelf、bind 计数、重启策略和 destroy barrier 的正负/失败例验证。",
            ),
            (
                "ServiceConnection",
                "客户端对一次 bind 关系的有身份订阅，定义连接成功、null binding、断连、binding died 等 callback。",
                "不是 service 全局 singleton callback；两个 caller 或两次 bind 不能共用无身份槽位。",
                "身份由 caller、context/token、target、flags、callback binder 与 generation 构成；unbind 只终止匹配关系。",
                "以 fan-out、逐连接 unbind、callback isolation、caller death 和销毁后零回调验证。",
            ),
            (
                "Service Binder endpoint",
                "Service 的 onBind 发布给客户端的 Android IBinder 能力端点；本地同 runtime 时应恢复 exact binder "
                "identity，跨进程时才需要有类型和安全边界的 proxy。",
                "不是任意非空 IRemoteObject，也不是把 remote object 转成 null。",
                "endpoint 由 service binding generation 与 publication record 限定；death、replacement 与 revoke "
                "必须传播到所有匹配连接。",
                "以 descriptor/identity、transaction、fan-out、death recipient、伪造 envelope 和旧代 endpoint 拒绝验证。",
            ),
            (
                "ServiceExtension",
                "OpenHarmony 可被连接和托管的 ExtensionAbility 类型，在本路线中提供宿主 token、ConnectionRecord "
                "与进程/权限承载。",
                "不是 Android Service 本体，也不会自动执行 Android Service lifecycle。",
                "OH framework 拥有 extension record/token；Bridge authority 维护 Android service projection，"
                "metadata 必须在 raw APK 安装模型中真实可解析。",
                "先验证 BMS SERVICE/EXTENSION metadata、ConnectAbility resolution、token generation、授权与 teardown。",
            ),
            (
                "ServiceLifecycleAuthority",
                "唯一串行化 Android Service resolve、record、startId、binding、publication、stop/restart 和 recovery "
                "决策的有界语义 owner。",
                "不是只保存 Binder 的 registry，也不是 ActivityThread 中零散的临时 map。",
                "第一阶段与 Android runtime 同进程但具名分层，持有 lock、journal、recovery 与权限边界；"
                "ActivityThread 仅执行 callback。",
                "通过并发 start/bind、authority crash/recovery、journal replay、重复/乱序 callback 和 fail-closed 验证。",
            ),
            (
                "endpoint envelope / publication",
                "把 Android Binder endpoint 与 service token、connection token、generation、caller scope 和完整性信息"
                "封装后，经 OH IRemoteObject 边界发布并在目标侧认证恢复的协议。",
                "不是裸指针、进程全局 handle 或无认证 parcel。",
                "authority 生成 publication，宿主只转运；接收方先认证 token/generation/caller 再恢复 exact local Binder "
                "或构造 typed proxy。",
                "以合法 round-trip、篡改、重放、错 caller、旧 generation、null binding 和 endpoint death 验证。",
            ),
        ],
        "nouns": [
            ("Fn07.C01 Service", "A04/A05/A08", "service token、ComponentName、start/bind/rebind/stop/death lifecycle；A08 待重构"),
            ("Fn07.C02 ServiceConnection", "A01/A03/A06/A09", "caller/token/context/callback/target/flags/generation 与 callback isolation"),
            ("Fn07.C03 ServiceBinder", "A02/A07", "endpoint generation、publication fan-out、exact local Binder 或 typed proxy"),
        ],
        "cases": [
            ("F07-H01", "p1612 / 25a0aa4", "DIRECT_WITH_BLOCKERS", "入口映射与 connection ledger 真实；publish log-only、remote object→null、identity scope 过窄。"),
            ("F07-H02", "ATL / 1f041f5", "VERIFIED_WITH_NEGATIVE", "最小 same-runtime Service owner；固定 startId、无 fan-out/death、unbind 为空。"),
            ("F07-H03/H04", "libgbinder / Anbox", "PRIMITIVE_AND_BOUNDARY", "endpoint publication/death 与 lifecycle-owner 分层有先例；不等于跨 runtime Service bridge。"),
            ("F07-H05/H06", "VirtualApp / DroidPlugin", "VERIFIED_ANALOGY", "支持显式 Service authority/record 和 connection wrapper；plugin/stub packaging 不适用于 raw APK。"),
            ("完整语料扫描", "62/62 sources · 6,303 raw hits · 0 errors", "SCAN_COMPLETE_NOT_EVIDENCE", "AOSP/OH 仍分别是 oracle/capability，不计历史成功案例。"),
        ],
        "routes": [
            ("R1", "推荐资格实验", "bounded same-runtime ServiceLifecycleAuthority + valid ServiceExtension host + local endpoint envelope", "第一阶段同 Android runtime；remote process fail-closed。"),
            ("R2", "候选对照实验", "typed Binder↔IRemoteObject bidirectional proxy", "支持跨进程，但 parcel/identity/death/security 成本最高。"),
            ("R3", "其他", "full ActiveServices-compatible coordinator", "语义强但 trusted owner 与依赖闭包大。"),
            ("R4", "其他", "app-specific generated ServiceExtension wrapper", "raw APK/update/signature/dynamic service 复杂。"),
            ("R5", "拒绝", "full Android container", "绕过 API-bridge mission。"),
        ],
        "route_details": [
            {
                "id": "R1",
                "position": "首个资格实验假设；尚非主选",
                "mechanism": "platform-internal metadata 把 raw APK service 投影为有效 ServiceExtension；"
                "same-runtime ServiceLifecycleAuthority 持有有界 lifecycle；token-owned envelope 恢复 exact local Binder。",
                "for": "保持 raw APK 和 typed OS boundary；避免一开始解决 generic cross-process Parcel；"
                "Android callback 仍由 ActivityThread 执行；endpoint transport 未来可演进到 R2。",
                "against": "active installer 已被源码审计证实只生成 PAGE ability：虽有 service parser 和一个 "
                "ServiceExtension 转换原型，但原型未进入 apk_installer 构建，active JSON/BMS 链也没有 services；"
                "authority、lock/journal/recovery、service/caller token、endpoint protocol 都不存在。",
                "history": "p1612 证明入口/connection 形状并暴露 publish log-only、remote→null 与 identity 欠约束；"
                "ATL 证明最小 same-runtime owner 可行但 startId/undbind/death 不完整；VirtualApp/DroidPlugin 支持 record/wrapper 类比。",
                "experiment": "D00 已用专用四-Service raw APK 在 5eab 真机执行：安装与 APK hash preservation PASS，"
                "但 BMS 仅登记 PAGE Activity 且 extensionInfos=[]，因此 D00=BLOCKED_AS_BUILT。"
                "Activity/画面 PASS；START_LOCAL 又暴露五参数 nativeStartAbility JNI 缺失被吞成 no-op、"
                "ComponentName false-success。Bridge-local G6-G11 七个 Unity APK 均为 0 service/receiver/provider。",
                "needed": "route-neutral SERVICE/EXTENSION metadata projection 与 fail-closed JNI/error propagation 已完成源码/host gate；"
                "下一步做 generation-exact AArch64 installer+BMS+framework 配对构建/部署并重跑 D00；再测 create/start/bind/"
                "publish/fan-out/null/rebind/stop/death/recovery、forgery 和 authorization。",
                "falsifier": "raw APK contract 下无法注册有效 ServiceExtension；token/envelope 不可认证；"
                "bounded authority 无法保持生命周期；首批必要 APK 声明 remote service。",
            },
            {
                "id": "R2",
                "position": "跨进程候选；不得因 R1 scope 小而自动采用",
                "mechanism": "双向 Android Binder↔OH IRemoteObject typed proxy，翻译 descriptor、transaction、"
                "parcel、oneway、caller identity、death 和 lifetime。",
                "for": "能覆盖 remote-process service 和跨运行时 endpoint；可与 R1 local fast path 共存。",
                "against": "Android Parcel 与 OH MessageParcel 非普遍同构；需要 AIDL 类型、identity、oneway、"
                "death 和 hostile transaction 安全面，成本与攻击面最高。",
                "history": "libgbinder 证明 endpoint publication/death primitive；Anbox 证明 lifecycle owner 与 "
                "endpoint 分层；没有 generic Android↔OH typed proxy 的同形成功案例。",
                "experiment": "首批 Bridge-local Unity G6-G11 manifest inventory 已完成：0 service，因而没有 remote "
                "service/AIDL 需求，也没有支持立即投入 R2 的产品证据；proxy artifact、parcel differential、death/security "
                "与 D600 result 仍 NOT_RUN。",
                "needed": "保持后续 APK/SDK remote/AIDL inventory；只有出现真实跨进程需求时才选代表 transaction corpus 做 host differential 与 fuzz；"
                "再执行 D09b/D10 和 caller/death/security 测试。",
                "falsifier": "代表性 AIDL 在不改 APK/runtime、无类型元数据时不可翻译，或 caller/death 语义无法保持。",
            },
            {
                "id": "R3",
                "position": "扩展架构候选；当前证据不足",
                "mechanism": "port/rehost 更完整 ActiveServices-compatible coordinator，覆盖多进程、restart、"
                "foreground-service、cross-user 与 policy。",
                "for": "Android lifecycle 保真最高；当 R1 bounded subset 持续扩张时，单一完整 owner 可能比累积 shim 更一致。",
                "against": "trusted code 和依赖闭包巨大；与 OH state/recovery 可能双 owner；版本维护、启动和安全成本高。",
                "history": "完整 Android/容器案例证明 ActiveServices 在其原生闭包中成立，但没有本项目 OH host 的 "
                "placement/build/recovery 先例。",
                "experiment": "无 topology、build closure、recovery 或 D600 artifact；NOT_RUN。",
                "needed": "只有 R1/R2 被证伪且需求确实需要广语义时，才做 dependency/topology/resource/security gate。",
                "falsifier": "closure 无界、与 OH owner 冲突，或资源/安全/恢复成本超过产品约束。",
            },
            {
                "id": "R4",
                "position": "产品策略候选；当前不推荐",
                "mechanism": "安装时为每个 Android Service 生成 app/service-specific OH ServiceExtension wrapper。",
                "for": "OH fit 高；对少量已知 service 可生成直接 host glue，避免 generic Binder translation。",
                "against": "更新、签名、动态/隐式 service、manifest feature 和 wrapper 生命周期迅速扩张；"
                "会把平台语义散落到 app-specific code，威胁 raw APK 最小性。",
                "history": "DroidPlugin/stub packaging 说明 wrapper/proxy 可行，但其 plugin packaging 与 raw APK 目标不一致。",
                "experiment": "无 generated-wrapper case、upgrade/signature/dynamic-service 测试；NOT_RUN。",
                "needed": "若产品允许 platform-internal generation，需先选一个 probe APK 验证安装、升级、签名、metadata、"
                "lifecycle 与清理，并与 R1 generic host 比较维护面。",
                "falsifier": "wrapper 需要改 APK/signature contract，或目标服务集合/动态行为使生成面无界。",
            },
            {
                "id": "R5",
                "position": "项目边界排除",
                "mechanism": "完整 Android container/virtual AMS 持有 Service lifecycle。",
                "for": "guest 内 lifecycle 与 Binder 保真高，现有 Android services 可整体复用。",
                "against": "绕过 API bridge 和 first-class OH component/token 目标，系统 footprint 与身份集成成本最大。",
                "history": "Anbox/完整 guest 是成熟边界案例，也证明成功来自保留整个 Android service owner，而非 OH API bridge。",
                "experiment": "无 D600 container；NOT_RUN，当前使命下不进入实验队列。",
                "needed": "只有项目级运行形态被重新定义后才评估。",
                "falsifier": "项目继续坚持 raw APK 通过 typed API bridge 成为 OH first-class app。",
            },
        ],
        "route_gate": [
            ("R1", "多案例支持形状，也暴露关键缺口", "5eab 四-Service D00=BLOCKED_AS_BUILT；metadata v1 源码与真实 parser host test PASS，但 AArch64 配对构建/部署 NOT_RUN", "D01-D15 NOT_RUN", "否：证据不足，继续实验"),
            ("R2", "只有 primitive/分层 precedent，缺同形 proxy", "G6-G11 均 0 service；无当前 remote/AIDL 触发需求", "NOT_RUN", "否：证据不足，继续实验"),
            ("R3", "完整 Android owner 有历史，OH placement 无", "无 topology/build", "NOT_RUN", "否：证据不足，继续实验"),
            ("R4", "plugin wrapper 类比，raw APK 适用性弱", "无 generated-wrapper case", "NOT_RUN", "否：证据不足，继续实验"),
            ("R5", "容器成功但使命不同", "无 D600 container", "NOT_RUN", "项目边界排除"),
        ],
        "primary": "R1",
        "backup": "R2",
        "recommendation": (
            "R1 只作为首个资格实验，因为它以最小范围暴露 metadata、authority 和 endpoint 三个真实门。"
            "同时先 inventory 首批 APK 的 remote/AIDL 需求，以决定是否值得启动 R2 proxy 实验。"
            "R3/R4 只有在 R1/R2 被证伪后再投入；D00-D15 前不请求人工选择。"
        ),
        "d600": [
            ("共同前置 G8 raw APK install", "PASS", "安装成功不等于 service metadata 是 SERVICE/EXTENSION。"),
            ("早期 G13 ServiceManager smoke", "FAIL/NOT_EXERCISED", "旧 generation app 未 fork，无 ServiceManager interaction；不是 Fn07 语义失败证据。"),
            ("AlexBridge r18 Activity/first frame", "NO Fn07 EXERCISE", "后续 generation 越过 Activity/画面，但未刺激 Service；不得继承为 Fn07 进展。"),
            ("Fn07 dedicated Service D00", "DEVICE BLOCKED_AS_BUILT", "四个 manifest Service 全部缺失，extensionInfos=[]；Activity cold start/画面 PASS；START_LOCAL 因 JNI no-op 返回 false-success。"),
            ("Fn07 metadata-projection v1", "SOURCE/HOST PASS · DEVICE NOT_RUN", "真实 AXML parser 四-Service 测试 PASS；installer JSON、BMS SERVICE patch 与 fail-closed Java 边界已冻结；尚无 generation-exact AArch64 配对构建。"),
            ("Unity G6-G11 manifest inventory", "7 APK VERIFIED · Fn07 NOT_EXERCISED", "七个最终 manifest 均 0 service/receiver/provider；不阻塞 first frame，也不能证明 Fn07。"),
            ("Fn07 D01-D15", "PLANNED_NOT_RUN", "bind、fan-out、startId、stopSelf、null binding、rebind、death、forgery、authorization。"),
        ],
        "final": (
            "现在只授权继续证据实验。dedicated Service probe 已在 5eab 把 D00 判为 BLOCKED_AS_BUILT；"
            "route-neutral metadata projection 与 fail-closed JNI/error path 已完成源码/host gate，"
            "下一步用同一 generation 配对构建/部署并重跑 D00，之后才执行 D01-D15 适用用例。"
            "G6-G11 未提供 R2 remote/AIDL 需求，R2 differential 暂不消耗设备；历史论证、正负/失败和 recovery/security 证据齐全后，"
            "再提交 R1/R2/R3/R4 的正式比较。Fn07.A08 仍需先修复 Action boundary。"
        ),
        "eligible": False,
        "gate": "不可 accepted：authority placement、ServiceExtension metadata、token/envelope security 与 A08 boundary 尚未关闭。",
    },
}


STYLE = """
:root{--bg:#eef2f6;--paper:#fff;--ink:#172033;--muted:#647087;--line:#d7dee8;
--primary:#147a54;--backup:#d97706;--other:#6d5bd0;--danger:#b42318;--fact:#1d4ed8}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);
color:var(--ink);font:16px/1.72 -apple-system,BlinkMacSystemFont,"Segoe UI",
"PingFang SC","Microsoft YaHei",sans-serif}main{max-width:1120px;margin:auto;background:var(--paper);
padding:34px clamp(18px,5vw,68px) 80px;box-shadow:0 0 35px #24324a18}
h1{font-size:clamp(29px,4vw,47px);line-height:1.15;margin:.15em 0}h2{font-size:25px;
margin:48px 0 16px;padding-bottom:9px;border-bottom:2px solid var(--line)}h3{font-size:18px}
p,li{max-width:90ch}a{color:#0f5fa8}code{background:#edf1f5;padding:2px 5px;border-radius:5px}
.hero{border-left:8px solid var(--primary);padding:18px 22px;background:#effaf5}
.meta,.legend{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}.pill,.tag{border:1px solid var(--line);
border-radius:999px;padding:3px 10px;color:var(--muted);font-size:13px}.tag.fact{color:var(--fact)}
.tag.inference{color:var(--other)}.tag.recommendation{color:var(--primary)}.tag.human{color:var(--danger)}
.notice{padding:14px 16px;border-left:5px solid var(--backup);background:#fff7e9;margin:18px 0}
.blocked{border-left-color:var(--danger);background:#fff1f0}.ok{border-left-color:var(--primary);background:#eef9f3}
nav{position:sticky;top:0;z-index:5;background:#ffffffed;backdrop-filter:blur(10px);border-bottom:1px solid var(--line);
padding:9px 0;overflow:auto;white-space:nowrap}nav a{display:inline-block;margin-right:13px;text-decoration:none;font-size:13px}
table{width:100%;border-collapse:collapse;margin:15px 0;font-size:14px}th,td{padding:10px;
text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}th{background:#f2f5f8}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(225px,1fr));gap:14px}.card{padding:15px;
border:1px solid var(--line);border-top:7px solid var(--other);background:#f8fafc}.card.primary{border-top-color:var(--primary);
background:#effaf5}.card.backup{border-top-color:var(--backup);background:#fff7e9}.card h3{margin:0 0 7px}
figure{margin:22px 0}figure img{display:block;width:100%;height:auto;border:1px solid var(--line);background:#f6f7f9}
figcaption{font-size:13px;color:var(--muted);margin-top:8px}.decision{margin-top:30px;padding:20px;
border:2px solid var(--line);background:#fafbfd}.decision button{border:0;border-radius:7px;padding:10px 14px;
margin:5px;font-weight:700;cursor:pointer}.decision .primary{background:var(--primary);color:#fff}
.decision .backup{background:var(--backup);color:#fff}.decision .concern{background:#d8dee7}.decision .reject{background:#f0b3ad}
textarea{width:100%;min-height:100px;padding:10px;border:1px solid var(--line);border-radius:6px}
pre{white-space:pre-wrap;overflow:auto;background:#172033;color:#eaf0f7;padding:14px;border-radius:7px}
.small{font-size:13px;color:var(--muted)}@media(max-width:650px){main{padding:22px 14px 60px}table{display:block;overflow:auto}}
.route-detail{margin:18px 0;padding:18px;border:1px solid var(--line);border-left:7px solid var(--other);
background:#fafbfd}.route-detail h3{margin:0 0 6px}.route-detail dl{display:grid;
grid-template-columns:minmax(125px,170px) 1fr;gap:8px 14px;margin:12px 0}.route-detail dt{font-weight:700}
.route-detail dd{margin:0}.route-detail.hypothesis{border-left-color:var(--primary)}
@media(max-width:650px){.route-detail dl{display:block}.route-detail dt{margin-top:10px}}
"""


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def table(headers: list[str], rows: list[tuple[str, ...]]) -> str:
    head = "".join(f"<th>{esc(item)}</th>" for item in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{esc(cell)}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def route_cards(routes: list[tuple[str, str, str, str]]) -> str:
    cards = []
    for route_id, rank, mechanism, qualification in routes:
        css = "primary" if "推荐" in rank else "backup" if "对照" in rank else ""
        cards.append(
            f'<article class="card {css}"><h3>{esc(route_id)} · {esc(rank)}</h3>'
            f"<p>{esc(mechanism)}</p><p class=\"small\"><b>边界/待证：</b>{esc(qualification)}</p></article>"
        )
    return '<div class="cards">' + "".join(cards) + "</div>"


def route_detail_cards(routes: list[dict[str, str]]) -> str:
    cards = []
    labels = (
        ("mechanism", "机制与放置"),
        ("for", "为什么优先研究"),
        ("against", "为什么现在不能选择"),
        ("history", "历史案例论证"),
        ("experiment", "早期实验结果"),
        ("needed", "人工裁决前必须补齐"),
        ("falsifier", "证伪/淘汰条件"),
    )
    for route in routes:
        detail = "".join(
            f"<dt>{esc(label)}</dt><dd>{esc(route[key])}</dd>"
            for key, label in labels
        )
        css = "hypothesis" if route["id"] == "R1" else ""
        cards.append(
            f'<article class="route-detail {css}"><h3>{esc(route["id"])} · '
            f'{esc(route["position"])}</h3><dl>{detail}</dl></article>'
        )
    return "".join(cards)


def decision_record(directory: Path) -> dict[str, str]:
    path = directory / "STRATEGY_DECISION.md"
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        return values
    for line in text.split("\n---\n", 1)[0][4:].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


def render(fn: str, data: dict[str, object]) -> None:
    directory = ROOT / "docs" / "concepts" / fn
    decision = decision_record(directory)
    record_status = decision.get("status", "missing")
    if record_status == "accepted":
        record_class = "ok"
        record_text = (
            f"权威决策已接受：owner={decision.get('owner', 'unknown')}，"
            f"date={decision.get('date', 'unknown')}，"
            f"selected={decision.get('selected_route', 'NONE')}，"
            f"backup={decision.get('backup_route', 'NONE')}。"
        )
    elif decision.get("gate_execution_authorized") == "true":
        record_class = "blocked"
        record_text = (
            f"权威记录仍为 pending；owner={decision.get('owner', 'unknown')} 已于 "
            f"{decision.get('date', 'unknown')} 授权执行前置 gate。该授权不是路线 acceptance。"
        )
    else:
        record_class = "blocked"
        record_text = "权威记录仍为 pending；尚未获得人类裁决。"
    provenance = json.loads(
        (directory / "strategy-review-route.png.provenance.json").read_text(encoding="utf-8")
    )
    image_bytes = (directory / "strategy-review-route.png").read_bytes()
    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    mime = provenance["mime_type"]
    decision_class = "ok" if data["eligible"] else "blocked"
    decision_word = (
        "历史与 D600 证据门已满足"
        if data["eligible"]
        else "历史 + D600 证据门关闭，禁止路线裁决"
    )
    source_links = " · ".join(
        f'<a href="{name}">{name}</a>'
        for name in (
            "CONCEPT_DOMAIN.md",
            "CASE_LEDGER.md",
            "ROUTE_SPACE.md",
            "STRATEGY.md",
            "D600_VERIFICATION_PLAN.md",
            "STRATEGY_DECISION.md",
        )
    )
    workflow_rows = [
        (
            "1 · 定义 AonB 无感运行与 Connect",
            "PROJECT_BASELINE_REVIEWED",
            "继承项目级透明边界；Android 与 OpenHarmony 两个 Codex 架构视角完成 Round 1 挑刺，"
            "修订后再完成 Round 2。四份 review 均保留，不能用本 Fn 的局部成功改写项目定义。",
        ),
        (
            "2 · 搜索历史 AonB 案例",
            "FN_SCAN_COMPLETE_NOT_EVIDENCE",
            "初始任务口径为 44 个 AonB 案例；离线镜像登记扩充为 62/62 roots。"
            "本 Fn 已完成独立扫描并把可用命中升级到 CASE_LEDGER；raw hit 和案例数量本身不产生 PASS。",
        ),
        (
            "3 · 枚举技术路线全集",
            "ROUTE_SPACE_PASS",
            "ROUTE_SPACE.md 已把真正不同的机制、owner、放置、代价、可逆性和 falsifier 分开；"
            "参数变体不伪装成新路线。",
        ),
        (
            "4 · HanBing/Yue 对照并提出主选、备选、其他路线",
            "RECOMMENDATION_ONLY",
            "显式对照 16.12 HanBing adapter 与 16.13 Yue 工厂/实验代码。"
            "本页的首个/下一实验假设是 agent 建议，不是已选主线。",
        ),
        (
            "5 · 准备并执行 D600 可证伪实验",
            "AUTHORIZED_IN_PROGRESS",
            "只执行 route-labelled、generation-bound 的正例、负例、失败、恢复和 rollback 合同；"
            "第五章逐项记录已运行、失败、作废与 NOT_RUN。",
        ),
        (
            "6 · 人类确认技术路线",
            "BLOCKED_BY_EVIDENCE_GATE",
            f"STRATEGY_DECISION.md 当前 status={record_status}。实验授权不得解释为主选/备选批准；"
            "只有同负载路线比较和独立 verifier 完成后才返回人类裁决。",
        ),
        (
            "7 · 实现设计文档",
            "BLOCKED_UNTIL_ROUTE_ACCEPTED",
            "只有人类接受且 hash-bound 的 Concept 决策才能进入 Action design；"
            "研究页、按钮和 route recommendation 都不能替代设计冻结。",
        ),
        (
            "8 · Coding",
            "EXPERIMENT_SUPPORT_ONLY",
            "当前只授权为证据实验所必需、可回滚的最小实现；它不能获得正式路线实现成熟度，"
            "也不能因 build 成功自动升级。",
        ),
        (
            "9 · D600 开发版最终验证",
            "ROUTE_FINAL_NOT_RUN",
            "早期 D600 事实保留在第五章，但最终验证必须针对已接受路线、冻结设计和同代产物重新执行；"
            "不得从旧 generation 或共同上游 PASS 继承。",
        ),
    ]
    page = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(fn)} {esc(data['name'])} · Strategy Review</title><style>{STYLE}</style></head>
<body><main>
<header class="hero"><p>Bridge · Concept route review book</p>
<h1>{esc(fn)} · {esc(data['name'])}</h1><p>{esc(data['question'])}</p>
<div class="meta"><span class="pill">AOSP 14 oracle</span><span class="pill">OpenHarmony 6.1 host</span>
<span class="pill">ART + raw APK</span><span class="pill">record: {esc(record_status)}</span>
<span class="pill">decision UI: evidence_gate_closed</span>
<span class="pill">{esc(decision_word)}</span></div></header>
<div class="notice {decision_class}"><b>证据与裁决边界：</b>本页区分
<span class="tag fact">源码/运行事实</span><span class="tag inference">推论</span>
<span class="tag recommendation">agent 建议</span><span class="tag human">人类裁决</span>。
推荐实验假设不是路线裁决，插图不是运行证据，页面按钮也不会改写项目真源。权威结果只能写入
<code>STRATEGY_DECISION.md</code>。<br><b>当前 gate：</b>{esc(data['gate'])}</div>
<div class="notice {record_class}"><span class="tag human">人类裁决</span>
<b>权威记录：</b>{esc(record_text)}
<a href="STRATEGY_DECISION.md">查看 STRATEGY_DECISION.md</a>。下方按钮仍只用于生成候选回执。</div>
<nav><a href="#workflow">九步流程</a><a href="#c1">第一章</a><a href="#c2">第二章</a><a href="#c3">第三章</a>
<a href="#c4">第四章</a><a href="#c5">第五章</a><a href="#c6">第六章</a>
<a href="#c7">第七章</a><a href="#c8">第八章</a></nav>

<section id="workflow"><h2>九步证据流水线 · 当前状态</h2>
<p>每个 Fn 都独立经过同一条流水线；前一步的文档或推荐不自动授权后一步。
项目级定义与历史语料可以复用，但本 Fn 的案例适用性、路线、D600 合同和 verdict 必须独立完成。</p>
{table(["步骤", "当前状态", "本 Fn 的证据边界"], workflow_rows)}
<p class="small">项目定义挑刺：
<a href="../../aonb-seamless-definition-review-pass1.md">定义 Pass 1</a> ·
<a href="../../aonb-seamless-definition-review-pass2.md">定义 Pass 2</a> ·
<a href="../../../evidence/reviews/fn04-fn07/android-architecture-round1.md">Android Codex Round 1</a> ·
<a href="../../../evidence/reviews/fn04-fn07/openharmony-architecture-round1.md">OH Codex Round 1</a> ·
<a href="../../../evidence/reviews/fn04-fn07/android-architecture-round2.md">Android Codex Round 2</a> ·
<a href="../../../evidence/reviews/fn04-fn07/openharmony-architecture-round2.md">OH Codex Round 2</a>。
</p></section>

<section id="c1"><h2>第一章 · 概念定义</h2><p><span class="tag fact">定义</span>
{esc(data['definition'])}</p><p><b>在本 Concept 中，Connect 的含义：</b>{esc(data['connect'])}</p>
<h3>核心术语：先区分对象、过程与回执</h3>
<p>下表不是词典式同义替换。每个名词都给出语义身份、明确的非定义、唯一 owner/
生命周期以及可观察判据；只有这些边界保持一致，Android 名词投影到 OpenHarmony 后才没有偷换概念。</p>
{table(["核心名词", "专业定义", "它不是什么", "Owner 与生命周期", "可观察成功/失败"], data["terms"])}
<p class="small">定义依据：<code>CONCEPT_DOMAIN.md</code>、<code>ANDROID_MODEL.md</code>、
<code>OPENHARMONY_MODEL.md</code>、<code>BRIDGE_CONTRACT.md</code>。AOSP 是 Android 语义 oracle；
OH 源码只证明宿主 capability，名称相似不构成语义等价。</p></section>

<section id="c2"><h2>第二章 · 稳定名词与 Action 边界</h2>
<p>Concept 负责把同一名词的语义、owner 和生命周期讲完整；Action 才是可独立触发、
观察并给 verdict 的稳定边界。细分 Concept 不重编号 Action。</p>
{table(["稳定名词", "Owned Actions", "独立边界"], data["nouns"])}
<p class="small">文档存在不等于 Action 成熟；任何 PASS 必须链接可复核运行证据。</p></section>

<section id="c3"><h2>第三章 · 历史案例</h2>
<p>只列已在 <code>/opt/Bridge</code> 内可复核的案例与明确降级项；AOSP/OH 源码分别是
semantic oracle 与 host capability，不伪装成 D600 成功案例。</p>
<p><b>语料口径：</b>初始任务要求搜索 44 个 AonB 案例；完整离线登记随后扩充为
<b>62/62 roots</b>。扩充用于减少漏检，不把数量当信息量。每个 Fn 只把有 exact
commit/path/line、机制和适用性边界的命中升级为历史案例。16.12 <b>HanBing</b> adapter
与 16.13 <b>Yue</b> 工厂/实验代码是本项目的近邻基线，但仍必须与 AOSP oracle、OH
capability 和当前 D600 generation 分层。</p>
{table(["案例", "来源/机制", "证据等级", "可迁移结论与限制"], data["cases"])}
<p class="small">完整锚点、版本、适用边界与全量语料审计见
<code>CASE_LEDGER.md</code> 和 <code>var/evidence/concepts/fn04-fn07-history-corpus-audit-20260725.md</code>。</p></section>

<section id="c4"><h2>第四章 · 技术路线</h2>
<p>先展示路线全景，再逐条回答：为什么值得研究、为什么现在不能选、历史案例到底支持到哪一层、
早期实验做到了什么、还缺什么、什么结果会淘汰该路线。R1 只是当前信息增益最高的实验假设。</p>
{route_cards(data["routes"])}
<h3>逐路线证据账</h3>
{route_detail_cards(data["route_details"])}
<figure><img src="data:{esc(mime)};base64,{image_b64}" alt="{esc(fn)} 多路线等权技术示意图；原生正文是唯一判读权威">
<figcaption>Gemini model=<code>{esc(provenance['model'])}</code>；
prompt SHA-256=<code>{esc(provenance['prompt_sha256'])}</code>；
image SHA-256=<code>{esc(provenance['image_sha256'])}</code>。
示意图，不是运行证据。生成图可能包含英文标签或拼写失真，路线定义以本页原生文字为准。</figcaption></figure>
<p class="small">图像 provenance：<a href="strategy-review-route.png.provenance.json">strategy-review-route.png.provenance.json</a>。</p></section>

<section id="c5"><h2>第五章 · 早期 D600 实验</h2>
<p><span class="tag fact">运行/计划状态</span> 早期实验必须区分共同上游 wall、真正的 Fn 行为、
false positive 与尚未执行的验证合同。</p>
{table(["实验/门", "当前状态", "能证明什么"], data["d600"])}
<p class="small">跨 generation 对账与严格 claim boundary：
<a href="../../../evidence/concepts/fn04-fn07-d600-early-evidence-reconciliation-20260725.md">
Fn04–Fn07 D600 early-evidence reconciliation</a>。早期 FAIL 与后续 r18 窄 PASS 必须同时保留，
不得跨 artifact/boot 继承。</p>
<h3>逐路线成熟度门</h3>
{table(["路线", "历史论证", "早期实验事实", "路线级 D600", "人工决策资格（材料是否充分）"], data["route_gate"])}
<div class="notice"><b>结论：</b>当前没有该 Fn 的 <code>device_verified</code>。G8 安装 PASS
不能向下继承；G7 process fork 失败时，后续 Fn 行为是 NOT_RUN，不是语义 FAIL。
“否：证据不足，继续实验”表示该路线仍存活，但尚不具备提交人类裁决的材料；
只有“已排除为完整路线”才表示该路线在本 Concept 总路线层面被淘汰。</div></section>

<section id="c6"><h2>第六章 · 路线建议</h2>
<p><span class="tag recommendation">实验顺序建议，不是路线选择</span> {esc(data['recommendation'])}</p>
<ul><li><b>首个待验证假设：</b>{esc(data['primary'])}</li><li><b>下一对照假设：</b>{esc(data['backup'])}</li>
<li><b>共同规则：</b>路线必须有 falsifier、rollback、正负/失败用例和 generation-bound provenance。</li>
<li><b>NOT_PROVEN：</b>source shape、build 成功、按钮选择、插图或单条日志均不是设备结论。</li></ul>
<p class="small">Android/OH 两轮独立复核：
<a href="../../../evidence/reviews/fn04-fn07/android-architecture-round2.md">Android Round 2</a> ·
<a href="../../../evidence/reviews/fn04-fn07/openharmony-architecture-round2.md">OH Round 2</a>。</p></section>

<section id="c7"><h2>第七章 · 最终建议</h2>
<div class="notice {decision_class}"><span class="tag recommendation">当前阶段建议</span>
{esc(data['final'])}</div>
<h3>开放人工路线裁决前的强制检查</h3><ol>
<li>主选的最小、可重复证伪是什么？</li><li>切到备选是否会形成两个 semantic owner？</li>
<li>哪些结论只是 source/build，哪些是真正同代 D600 receipt？</li>
<li>接受 fallback 时，限定到哪个 Unity 目标、哪个 Action、何时移除？</li>
<li>每条仍存活路线是否都完成相同 workload、正例、负例、failure、recovery 和独立复核？</li></ol></section>

<section id="c8" class="decision"><h2>第八章 · 证据实验授权（不是路线选择）</h2>
<div class="notice blocked"><b>路线裁决尚未开放。</b>当前控件状态为
<code>evidence_gate_closed</code>。只有第五章中所有必要路线达到规定的历史论证与同代
D600 正/负/失败/恢复证据后，本章才可切换为 <code>pending_user_confirmation</code>。
在此之前不得“批准主选”、不得“改选备选”，也不得以“拒绝”代替尚可执行的证伪实验。</div>
<p><button class="primary" data-choice="批准继续证据实验" data-route="ALL_ELIGIBLE">批准继续证据实验</button>
<button class="concern" data-choice="CONCERN" data-route="NONE">CONCERN：实验合同不足</button>
<button class="reject" data-choice="拒绝实验设计" data-route="NONE">拒绝当前实验设计</button></p>
<p><button class="primary" disabled>批准主选（证据门关闭）</button>
<button class="backup" disabled>改选备选（证据门关闭）</button></p>
<label for="note"><b>需要补充的历史证据、D600 实验或证伪条件</b></label>
<textarea id="note" placeholder="说明应补哪条路线、哪个实验、正负/失败条件、独立 verifier 与终止条件"></textarea>
<p><button id="export" type="button">导出 JSON / Markdown</button></p><pre id="output">尚未选择。</pre>
<p class="small">源文档：{source_links}</p></section>
</main>
<script>
const state={{concept_id:{json.dumps(fn)},status:"evidence_gate_closed",eligible_for_acceptance:false,
experimental_hypothesis:{json.dumps(data['primary'])},comparison_hypothesis:{json.dumps(data['backup'])},
next_status_after_evidence:"pending_user_confirmation",choice:null,route:null,note:""}};
const out=document.getElementById("output"),note=document.getElementById("note");
document.querySelectorAll("[data-choice]").forEach(b=>b.addEventListener("click",()=>{{
 state.choice=b.dataset.choice;state.route=b.dataset.route;state.note=note.value.trim();
 out.textContent=JSON.stringify(state,null,2);
}}));
document.getElementById("export").addEventListener("click",()=>{{
 state.note=note.value.trim();const md=`# ${{state.concept_id}} strategy decision candidate

- status: ${{state.status}}
- eligible_for_acceptance: ${{state.eligible_for_acceptance}}
- choice: ${{state.choice}}
- route: ${{state.route}}
- note: ${{state.note}}

This export authorizes or challenges evidence work only. It is not a route decision.
STRATEGY_DECISION.md must remain pending until the history-and-D600 evidence gate passes.
`;const payload=JSON.stringify(state,null,2)+"\\n\\n--- Markdown ---\\n"+md;
 out.textContent=payload;const blob=new Blob([payload],{{type:"text/plain"}});
 const a=document.createElement("a");a.href=URL.createObjectURL(blob);
 a.download=`${{state.concept_id}}-strategy-decision-candidate.txt`;a.click();URL.revokeObjectURL(a.href);
}}));
</script></body></html>"""
    (directory / "strategy_review.html").write_text(page, encoding="utf-8")

    log = f"""# {fn} strategy_review.html · 六轮评审日志

状态：页面候选控件为 `pending_user_confirmation`；权威状态来自
`STRATEGY_DECISION.md`，本轮生成时为 `{record_status}`。页面本身不是实现批准或运行证据。
图像模型：Gemini `{provenance['model']}`；示意图，不是运行证据。

> 说明：以下六轮是页面生成器的内部结构检查，不是 Kimi 独立评审。
> 2026-07-25 请求的三次 Kimi headless review 均在生成内容前被 provider quota
> 以 HTTP 403 拒绝，状态为 `BLOCKED_BY_PROVIDER_QUOTA`；prompt 与阻塞回执见
> `../../../evidence/reviews/kimi-fn04-fn07-20260725/README.md`。

## 第一轮 · 大一新生可读性 #1

- concern：原第一章只有域目标，没有逐项解释核心名词，读者会把 Window、Surface、
  Rendering 等对象、过程和回执混为一谈。
- 修复：第一章为每个核心名词增加“专业定义 / 它不是什么 / owner 与生命周期 /
  可观察成功失败”五列表；第二章再讲稳定 Action 边界，明确文档存在不产生 PASS。
- 复检：PASS。

## 第二轮 · 大一新生可读性 #2

- concern：历史源码、AOSP oracle、OH capability 和 D600 成功容易被视为同一证据等级。
- 修复：第三章用独立 evidence-level 列，所有案例写出“能证明/不能证明”。
- 复检：PASS。

## 第三轮 · 大一新生可读性 #3

- concern：路线图含 Gemini 生成标签，读者可能只看颜色或图中文字。
- 修复：第四章提供等权原生路线卡、长 alt、prompt/image SHA 与“示意图，不是运行证据”声明；原生文字为权威。
- 复检：PASS。

## 第四轮 · IEEE 逻辑/意义 #1

- concern：页面先展示“批准主选/改选备选”，会在历史论证和 D600 对照不足时诱导人类过早决策。
- 修复：第八章固定 `evidence_gate_closed`，只允许授权或质疑证据实验；路线按钮禁用。
  只有逐路线历史与同代 D600 正/负/失败/恢复门满足后，才进入未来的
  `pending_user_confirmation`。
- 复检：PASS。

## 第五轮 · IEEE 逻辑/意义 #2

- concern：G8 安装 PASS、G7 fork FAIL、false-positive graphics 与该 Fn 的 NOT_RUN 可能被错误继承。
- 修复：第五章逐项标 PASS/FAIL/INVALIDATED/PLANNED_NOT_RUN，并声明共同前置不能向下继承。
- 复检：PASS。

## 第六轮 · IEEE 逻辑/意义 #3

- concern：仅列推荐分数不能解释为什么研究 R1、为什么暂不选择其他路线，以及每条路线的实验成熟度。
- 修复：第四章给每条路线增加机制、支持理由、反对理由、历史、早期实验、待补证据和
  falsifier；第五章增加逐路线成熟度门；第六、七章只安排实验顺序。
- 复检：PASS。Gemini provenance、八章、四种 decision marker、textarea、JSON/Markdown 导出均进入机械校验。
"""
    (directory / "STRATEGY_REVIEW_LOG.md").write_text(log, encoding="utf-8")


def main() -> int:
    for fn, data in DATA.items():
        render(fn, data)
        print(f"RENDERED {fn} strategy_review.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
