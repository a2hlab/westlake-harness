# r16「进程活着但白/黑屏」5 个 —— 逐 app 定因(25 分钟限时)

证据:r16 全量 hilog 一手(5cd:A 片;61b:B 片),G2.14as 可见性探针(Westlake LifecycleAdapter L563+ 移植)为共同判据。**共性发现:5 个里 4 个不是渲染问题,是 Splash 重定向失败——首 Activity 自己 finish 了(mFinished=true、lifecycleState=1 CREATED、mWindowAdded=false),而重定向目标从未收到第二次 LaunchActivity(scheduled=1 只有 Splash 自己)。**

## fd-binaryeye@5cd(白)— 类别:**Splash 重定向失败**

- 探针铁证(T=3000):`mVisibleFromClient=true mVisibleFromServer=false mFinished=true mWindowAdded=false lifecycleState=1`
- 唯一 LaunchActivity = `SplashActivity`(00:30:52.128);之后 Splash 调 startActivity 重定向,但**全 hilog 无第二次 LaunchActivityItem**;00:30:57 出现第二子进程 28617(PIB 重新投影)——app 试图自重启
- 首个异常:`[IFACE-IF] $Proxy13 iface=IActivityManager ifaceMethod=addInstrumentationResults…` 紧跟 `[B8-AMB] IActivityManager bindService proxy installed` ——**代理方法面在 Splash finish 时刚装完,重定向的 startActivity 调用走了代理但无下文**
- camera(196 行)只是 androidx.camera.view.PreviewView 类链接的噪声——**与扫码相机无关,屏都没 add**
- Westlake 对应:它的 startActivity 走 `OH_ATMAdapter: startActivity: creating new Mission`(#76 Westlake 成功跑原文);route-A 的代理 startActivity 路径需查 r16 runtime JAR 的 ActivityManagerAdapter startActivity 分支(疑返回值/线程问题)

## fd-filemanager@5cd(白)、fd-gallery@5cd(白)、fd-tusky@61b(白)— 同类:**Splash 重定向失败**

- 三家探针完全同型:`mFinished=true mVisibleFromServer=false mWindowAdded=false lifecycleState=1`
- LaunchActivity scheduled 均只有 1 次(tusky=MainActivity 自己,filemanager/gallery 同 binaryeye 模式)
- filemanager 另有后台线程栈(e5.i.c→ThreadPoolExecutor)——非主因,存活着
- **一段修复救 4 个**:修 startActivity 代理的 Splash→目标重定向(目标 Activity 的 LaunchActivityItem 必须被调度)

## fd-mobile@5cd(黑)— 类别:**首帧未合成(内容已建)**

- 探针(T=500):`mVisibleFromClient=true mVisibleFromServer=true mFinished=false mWindowAdded=true lifecycleState=3(RESUMED)` + VRN `decor hasDL=true, lvl1=LinearLayout hasDL=true` —— **与 anki/notes 的 vis=0 空白同族**(#91-② 已定因的假设 1:首帧未合成/反向推帧缺失)
- BufferQueue 只有 nativeCreate/GetFromBlast 的 RegHook 注册行,**无 dequeue/queue 流量** —— 首帧从未真正提交
- 黑(非白):Jellyfin 首屏深色主题,画不出时呈现黑底
- Westlake 对应:WindowSessionAdapter **L1044-1060 G2.14as r4 反向推帧**(OH 服务端不调 IWindow.resized;不推则 ViewRootImpl 0→0→0 测量死亡螺旋)——r16 runtime 是否带 r4 需 cx-t3 核;判别实验照 #91-② 的三步(t+8 截图+YAVG+grep `outFrames populated`,frame=(0,0,0,0) 即证)

## 汇总(修复归属)

| app | 类别 | 修复段 |
|---|---|---|
| binaryeye/filemanager/gallery/tusky(白) | **Splash 重定向失败**(startActivity 代理无下文,4 个一段) | route-A ActivityManagerAdapter startActivity 分支修(新墙,cc-t3/r17) |
| fd-mobile(黑) | 首帧未合成(=anki/notes vis=0 族) | G2.14as r4 反向推帧(#91-② 判别实验先行) |
