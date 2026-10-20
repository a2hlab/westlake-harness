spec: task
name: "T25 trusted window geometry adapter preserving T23"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t23-egl-import]
tags: [geometry, native-window, source-reuse, candidate]
---
## 意图
在独立单元补齐 geometry 的可信 wrapper 到 OH window 转换，候选异常是本次121次 setBuffersGeometry 返回40001000；它尚非已证明的视频首因。仅生产保留T23行为的可审候选，实际geometry provider winner和动态视频通过分别验收。
## 已定决策
- 只新增 `ANativeWindow_setBuffersGeometry` 入口，复用T20已验证可信owner unwrap与同实例provider校验；不更改T23原77个导出及其实现单元。
- 调用者须持有合法ANativeWindow引用；只接纳既有T20接受的player/bridge wrapper域。调用owner_acquire成功后才unwrap，两opcode结束统一owner_release；无任意指针安全分类承诺，不以magic猜原生OH指针，原生OH透传暂不支持。
- `opcode0` 接收原始width/height，成功后且format>0才调用 `opcode3`；分别记录geometry_rc和format_rc，返回第一个实际失败，不吞错或用成功覆盖失败。
- 格式采用明确现有映射，Android 1/2/3/4/YV12分别为OH 12/11/13/3/11；其他正format沿既有exact765行为原样传递，非正format不发opcode3。不新增尺寸推测、0x0恢复或格式支持承诺。
- 调用生产dispatch时先核exact player路径与ELF可读槽0x472490/0x472760/0x472048分别绑定同候选lock/unlock/geometry；任一不符则零owner/OH调用，禁止mixed765路径冒充支持。槽来源钉现有player完整SHA与readelf relocation原件。
- `actual_winner` 必须在实际调用链归属：geometry入口与下游HandleOpt指针、所属映射和精确文件身份一起记录；CPU pair绑定或同名/同SHA多映射不能替代geometry绑定。绑定未知或外来对象拒绝，禁止猜布局或新dlopen跨namespace。
- 实现只复用T20可信owner能力及本次surface8f机制；旧donor中无条件return0、私自重开provider和猜指针行为不继承。持久记录原始构建argv/stdout/stderr/rc、源快照与工具链/依赖哈希。
## 约束
- 本轮外环已授权仅本树离线实现、host测试和本地基线/候选构建；本任务仍禁止设备、部署、重启、清数据或推送。
- 冻结项、T20/T23源文件和旧签认只读；构建前check_frozen，失败拒绝产物准入。旧CPU pair、EGL生命周期、网络和音频不变。
- null、foreign、解包失败或provider不一致在任何OH调用前拒绝；不解引用未知对象，不伪造原生错误状态。
## 边界
### 允许修改
- benchmark/2026-10-20-t25-geometry/**
- specs/toutiao-video-playback/t25-geometry-unwrapping.spec.md
- tools/spec-checks/tests/toutiao_t25_geometry.rs
### 禁止
- benchmark/2026-10-20-t23-egl-import/**
- benchmark/2026-10-20-t20-provider-link-slice/**
- knowledge/frozen/**
- 不改其他源码、ABI、播放器分支、getter、damage、随机崩溃或安全逻辑。
## 完成条件
场景: 可信geometry和format按顺序转调
  测试: ttvideo_t25_geometry
  假设 实际C单元获得可信owner unwrap和同实例HandleOpt seam
  当 以1080x1920或576x1024及1/2/3/4/YV12/未知正format调用
  那么 opcode0的width/height原样传递且对象为解包所得OH window
  并且 opcode0成功后opcode3仅调用一次，映射为12/11/13/3/11或未知原值，返回真实结果
场景: 调用期间持有wrapper引用
  测试: ttvideo_t25_geometry
  假设 调用者持有合法ANativeWindow引用且owner_acquire成功
  当 unwrap和两个opcode成功或中途失败
  那么 额外引用贯穿整个调用且owner_release恰好一次，acquire失败则不unwrap不调用OH
  并且 不尝试魔数读取或原生OH分类，保留调用者引用前提
场景: 空对象与外来provider拒绝
  测试: ttvideo_t25_geometry
  假设 null、已由可信seam拒绝的foreign、unwrap失败或provider实例不一致
  当 请求ANativeWindow_setBuffersGeometry
  那么 在任何OH调用前返回明确非零错误，无猜指针和新dlopen
场景: geometry失败不执行format
  测试: ttvideo_t25_geometry
  假设 opcode0分别返回40001000和负错误码
  当 调用geometry并提供正format
  那么 返回geometry_rc原值，format_calls为0且format_rc标not-called
场景: format失败与不设置format
  测试: ttvideo_t25_geometry
  假设 geometry成功且opcode3失败或format为0或负数
  当 请求geometry
  那么 正format返回format_rc原值，非正format不调用opcode3并返回geometry_rc
  并且 width和height包括0或负值均不被改写，OH返回保持原值
场景: 保留T23行为与新增ABI
  测试: ttvideo_t25_build_receipt
  假设 钉住T23 a9abaf09候选、原77导出和原始构建输入
  当 将新增独立TU链接进同一DSO并运行旧T23及T20检查
  那么 旧源/对象哈希不变，旧77导出与符号版本保留，仅新增geometry导出，NEEDED和TEXTREL状态不变
  并且 ABI consumer检查无移除/漂移/断链，所有旧检查通过
场景: 证据不全或冻结不符拒绝候选
  测试: ttvideo_t25_build_receipt
  假设 缺源码快照、工具链SHA、依赖SHA、原始构建日志或check_frozen失败
  当 校验候选receipt
  那么 标记拒绝且不能以事后清单代替rc0原始构建argv/stdout/stderr
场景: actual winner与视频结果分开审核
  测试: ttvideo_t25_geometry
  审核: human
  假设 外环另有单板受锁短窗与回滚方案
  当 核对actual_winner、HandleOpt映射与精确文件、两个opcode结果及连续视频帧
  那么 缺geometry实际绑定时保持unknown且拒绝将CPU绑定替代
  并且 几何错误消失仅证明该墙移走，视频仍按project两个完整周期验收，静态/host通过不算视频通过
## 排除范围
- 设备操作与部署授权；原生OH透传与混合旧765锁路径；其他窗口API；宽高修正；新增format支持；全量APK封板；承诺视频成功。
