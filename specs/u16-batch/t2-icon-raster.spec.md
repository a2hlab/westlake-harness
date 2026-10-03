spec: task
name: "T2 frequent-habits: XML 自适应图标栅格化进桌面投影"
inherits: project
tags: [installer, icon, launcher]
depends: []
---

## 意图

cv2-com-frequent-habits 至今 `app_failed`:安装器给它装的桌面图标是 XML-only 占位(u16-unowned-diag:adaptive/vector 图标没栅格化,launcher 拿不到位图,定位不到图标→app 从未启动)。本任务在安装器侧把 `<adaptive-icon>`/`<vector>` XML 合成(背景层+前景层,矢量感知)成 raster icon.png 并填 iconId/iconPath,替代 XML 占位。

来源:benchmark/2026-10-03-u16-unowned-diag/results.json(cv2-com-frequent-habits,cluster=launcher-side icon projection,与 B3 相关)。

## 已定决策

- 合成在安装期完成(离线、APK 侧),不上运行时;渲染用 Mac 侧既有栅格化链(无新原生依赖)。
- 只处理 manifest 图标为 XML 的情形;已是 raster 的路径原样保留(行为不变)。
- 安装器(libapk_installer 7048c7c5)在冻结表(FZ-001):按 project 约束走『加新功能且原行为保留』——外环先批,单板重验 4 个 FZ-001 证据 app + frequent-habits,零回退后登记新版;换 installer 的 foundation 重启掉 USB 风险由外环排窗。
- 观察点:frequent-habits 进 U16 键表 movers(来源=本任务),check_fix_observers 的安装器 token/SHA 前缀命中。

## 边界

### 允许修改
- benchmark/2026-10-03-u16-t2-icon-raster/**
- 安装器图标处理路径(经外环批的 FZ-001 路径)
- tools/spec-checks/tests/u16_t2_icon.rs

### 禁止
- 不动运行时/JAR/bridge
- 不在板上直接改 launcher 数据

## 验收标准

场景: XML 图标被栅格化
  测试: u16_t2_xml_icon_rasterized
  假设 安装器对 frequent-habits 的 APK 跑图标处理(离线干跑)
  当 读取产出的 icon 记录
  那么 iconPath 指向 PNG(非 .xml)且文件存在
  并且 PNG 尺寸 ≥ 48x48 且非全透明(grep 安装器输出行验证)

场景: 图标可定位、app 可启动
  测试: u16_t2_icon_located
  假设 U16 窗口装 frequent-habits 并点桌面图标
  当 采集 processes-t5/t20 与截图
  那么 有 app 进程且有 t20 截图(图标定位成功)
  并且 t20 内容判定交外环(审核: human)

场景: 非图标 XML 或栅格化失败 → 原样保留并记失败
  测试: u16_t2_raster_failure_fallback
  假设 输入 APK 的图标 XML 解析失败或图层缺失(构造的坏样本)
  当 安装器图标处理跑完
  那么 iconPath 保持原 XML 占位不变(原行为保留)
  并且 输出含 raster-failed 行与失败原因,不中断安装

## 排除范围

- 不重做整个 B3 图标管线;只修 adaptive/vector→raster 这一步。
