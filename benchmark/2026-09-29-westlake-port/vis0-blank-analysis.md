# #91-②: vis=0 透明窗定因(anki/fd-notes:r15c 存活但视觉空白)

输入:r15c(5cd)r15cfull 的 anki/fd-notes hilog 一手行;源:vm-copies/westlake-current。离线。

## 现象(一手原文)

两家 T=8000ms 的 G2.14as 可见性探针(Westlake 移植的诊断,LifecycleAdapter.java L563+)完全同型:

- anki(VIS):`mVisibleFromClient=true mVisibleFromServer=true mFinished=false mWindowAdded=true hideForNow=false lifecycleState=3(RESUMED) decorVisibility=0(VISIBLE) decorSize=1200x1920 hasDL=true`
- anki(CHD):`decor childCount=1 | child[0]=ActionBarOverlayLayout meas=1200x1920 size=1200x1920 vis=0` ← **此 vis=0 是 View.VISIBLE 常量值,不是"不可见"**——子树也是可见态
- fd-notes(VIS/CHD):同型,child[0]=LinearLayout meas=1200x1920 vis=0(VISIBLE)

**即:生命周期、窗口添加、decor/内容树、测量(1200x1920 满屏)全部正常,内容树处于 VISIBLE。** "vis=0"本身不是病——它是 `View.VISIBLE` 的值。空白另有原因。

## 定因(排序后的假设与证据)

1. **内容画了但首帧未合成/未 flush(最可能)**:VIS 里 `hasDL=true`(display list 已建),说明 draw 走过 RenderThread 管线;但 r15c 的这两家无截图可判内容(外环只到"空白"观察)。Westlake 在同链路上的关键补丁是 WindowSessionAdapter 的 **G2.14as r4 反向推帧**(L1044-1060 注释:OH 服务端不会主动调 `IWindow.resized`,AOSP WMS 会;不推帧则 ViewRootImpl 陷入 0→0→0 测量死亡螺旋)。若 route-A 侧 relayout 返回了 outFrames 但**漏了 r4 的单次反向推**,首帧可能永不合入。
2. **hwui 首帧 SurfaceControl 复用缺**:WindowSessionAdapter L1103 注释(首帧前重复创建 SC 会 abort);r15c 若 SC 创建时序不同,首帧黑/空。
3. **内容本身就是空 Activity(不能排除)**:anki(AnkiDroid 首屏在后台线程建 DB UI)与 fd-notes(列表空态)都可能合法地画"接近全白"页面;#51 时代 13 个"near-white-blank(YAVG≈254.8)"与 r15c 存活组的连续性提示这可能是**真实 UI 的空态**而非 bug。

## 给上板的判别实验(一步定案,cc-t3/r16)

对 anki/fd-notes 各拉起一次:①t+8 截图 + ffmpeg YAVG;②同刻 grep `[G2.14as-VR2] mFirst=`(relayout 稳态)与 `[OH_WSA-relayout] outFrames populated`(r3 探针——若 frame=(0,0,0,0) 或反复 0,即 r4 缺失的直接证据);③若 outFrames 正常且 YAVG≈254,**结论=空态真 UI**,不是墙——从待修清单移除,记"内容空白但技术点亮"。YAVG 单指标不能定内容(#76 教训),需外环读图终判。

## 引用(一手)

- LifecycleAdapter.java L563-660(G2.14as-VIS 探针与字段语义:decorVisibility 0=VISIBLE)
- WindowSessionAdapter.java L1044-1060(G2.14as r4 反向推帧的必要性注释)、L1103(首帧 SC 复用)
