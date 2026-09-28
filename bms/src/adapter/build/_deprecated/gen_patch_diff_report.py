#!/usr/bin/env python3
"""Generate HTML diff report for OH patches applied by the adapter project."""
import subprocess, html, os

OH = "/home/HanBingChen/oh"
OUT = "/home/HanBingChen/adapter/ohos_patches/patch_diff_report.html"

files = [
    ("ability_rt", "services/abilitymgr/include/mission/mission.h",
     "foundation/ability/ability_runtime/services/abilitymgr/include/mission/mission.h",
     "Mission 类头文件 — 添加多 Ability 栈支持"),
    ("ability_rt", "services/abilitymgr/src/mission/mission.cpp",
     "foundation/ability/ability_runtime/services/abilitymgr/src/mission/mission.cpp",
     "Mission 类实现 — 多 Ability 栈操作方法"),
    ("ability_rt", "interfaces/.../ability_manager_interface.h",
     "foundation/ability/ability_runtime/interfaces/inner_api/ability_manager/include/ability_manager_interface.h",
     "IAbilityManager 接口 — 添加 StartAbilityInMission()"),
    ("ability_rt", "interfaces/.../ability_manager_ipc_interface_code.h",
     "foundation/ability/ability_runtime/interfaces/inner_api/ability_manager/include/ability_manager_ipc_interface_code.h",
     "IPC 接口编码 — 添加 START_ABILITY_IN_MISSION = 6200"),
    ("ability_rt", "services/appmgr/include/remote_client_manager.h",
     "foundation/ability/ability_runtime/services/appmgr/include/remote_client_manager.h",
     "RemoteClientManager 头文件 — 添加 GetAndroidSpawnClient()"),
    ("ability_rt", "services/appmgr/src/remote_client_manager.cpp",
     "foundation/ability/ability_runtime/services/appmgr/src/remote_client_manager.cpp",
     "RemoteClientManager 实现 — appspawn-x 客户端"),
    ("ability_rt", "services/appmgr/src/app_mgr_service_inner.cpp",
     "foundation/ability/ability_runtime/services/appmgr/src/app_mgr_service_inner.cpp",
     "AppMgrServiceInner — APP_ANDROID 路由到 appspawn-x"),
    ("bundle_framework", "interfaces/.../application_info.h",
     "foundation/bundlemanager/bundle_framework/interfaces/inner_api/appexecfwk_base/include/application_info.h",
     "BundleType 枚举 — 添加 APP_ANDROID = 10"),
    ("bundle_framework", "services/bundlemgr/include/ipc/installd_interface.h",
     "foundation/bundlemanager/bundle_framework/services/bundlemgr/include/ipc/installd_interface.h",
     "IInstalld 接口 — 添加 5 个 Android 安装 IPC 方法"),
    ("bundle_framework", "services/bundlemgr/src/bundle_installer.cpp",
     "foundation/bundlemanager/bundle_framework/services/bundlemgr/src/bundle_installer.cpp",
     "BundleInstaller — APK 检测逻辑 (#ifdef OH_ADAPTER_ANDROID)"),
]

new_files = [
    ("ability_rt", "services/abilitymgr/src/mission/mission_list_manager_patch.cpp",
     "foundation/ability/ability_runtime/services/abilitymgr/src/mission/mission_list_manager_patch.cpp",
     "MissionListManager 扩展 — StartAbilityInMission 实现"),
    ("bundle_framework", "services/bundlemgr/src/installd/installd_host_impl_android.cpp",
     "foundation/bundlemanager/bundle_framework/services/bundlemgr/src/installd/installd_host_impl_android.cpp",
     "Installd Android 实现 — 5 个 IPC 方法实现"),
]

def get_diff(full_path):
    bak = full_path + ".bak"
    if not os.path.exists(bak):
        return ""
    r = subprocess.run(["diff", "-u", bak, full_path], capture_output=True, text=True)
    return r.stdout

def diff_to_html_lines(diff_text):
    lines = []
    for line in diff_text.split("\n"):
        if line.startswith("+++") or line.startswith("---"):
            cls = "diff-header"
        elif line.startswith("@@"):
            cls = "diff-hunk"
        elif line.startswith("+"):
            cls = "diff-add"
        elif line.startswith("-"):
            cls = "diff-del"
        else:
            cls = "diff-ctx"
        lines.append('<span class="%s">%s</span>' % (cls, html.escape(line)))
    return "\n".join(lines)

def count_changes(diff_text):
    add = sum(1 for l in diff_text.split("\n") if l.startswith("+") and not l.startswith("+++"))
    rem = sum(1 for l in diff_text.split("\n") if l.startswith("-") and not l.startswith("---"))
    return add, rem

def file_lines(path):
    with open(path, "r") as f:
        return sum(1 for _ in f)

# Build HTML
h = []
h.append("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>OH 补丁差异报告 — Android-OH Adapter</title>
<style>
body { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; margin: 20px 40px; background: #fafafa; color: #333; }
h1 { background: linear-gradient(135deg, #1a5276, #2980b9); color: #fff; padding: 16px 24px; border-radius: 6px; }
h2 { background: linear-gradient(135deg, #1e8449, #27ae60); color: #fff; padding: 10px 18px; border-radius: 4px; margin-top: 30px; }
h3 { background: #ecf0f1; padding: 8px 14px; border-left: 4px solid #2980b9; margin-top: 20px; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; }
th { background: #2c3e50; color: #fff; padding: 8px 12px; text-align: left; }
td { border: 1px solid #ddd; padding: 6px 12px; }
tr:nth-child(even) { background: #f2f2f2; }
.add { color: #27ae60; font-weight: bold; }
.del { color: #c0392b; font-weight: bold; }
.new-tag { background: #27ae60; color: #fff; padding: 2px 8px; border-radius: 3px; font-size: 0.85em; }
pre.diff { background: #1e1e1e; color: #d4d4d4; padding: 12px; border-radius: 4px; overflow-x: auto; font-size: 13px; line-height: 1.4; max-height: 600px; overflow-y: auto; }
.diff-add { color: #6a9955; }
.diff-del { color: #f44747; }
.diff-hunk { color: #569cd6; font-weight: bold; }
.diff-header { color: #dcdcaa; }
.diff-ctx { color: #d4d4d4; }
a { color: #2980b9; text-decoration: none; }
a:hover { text-decoration: underline; }
.toc { background: #fff; border: 1px solid #ddd; padding: 16px 24px; border-radius: 6px; margin: 16px 0; }
.toc ul { list-style: none; padding-left: 0; }
.toc li { padding: 3px 0; }
.toc li::before { content: "\\25B6"; color: #2980b9; margin-right: 8px; font-size: 0.8em; }
.summary { background: #eaf2f8; border: 1px solid #aed6f1; padding: 12px 18px; border-radius: 4px; margin: 12px 0; }
</style>
</head>
<body>
<h1>OH 补丁差异报告</h1>
<p><strong>基线版本：</strong>OH V7.0.0.18-strict (sdk 26.0.0.18)<br>
<strong>目标产品：</strong>rk3568 (arm32)<br>
<strong>补丁来源：</strong>adapter/ohos_patches/ (ability_rt + bundle_framework)<br>
<strong>生成日期：</strong>2026-04-07<br>
<strong>编译验证：</strong>5 个关键目标全部通过 (libabilityms, libappms, libscene_session_manager, libscene_session, libbms)</p>

<div class="toc">
<strong>目录</strong>
<ul>
<li><a href="#ch1">1. 变更总览</a></li>
<li><a href="#ch2">2. ability_rt 补丁详情</a></li>
<li><a href="#ch3">3. bundle_framework 补丁详情</a></li>
<li><a href="#ch4">4. 新增文件</a></li>
<li><a href="#ch5">5. 未应用的补丁</a></li>
</ul>
</div>
""")

# Chapter 1: Summary table
h.append('<h2 id="ch1">1. 变更总览</h2>')
h.append('<table><tr><th>#</th><th>模块</th><th>文件</th><th>说明</th><th>增</th><th>删</th></tr>')
idx = 1
total_add = total_del = 0
for mod, short, full, desc in files:
    diff_text = get_diff(os.path.join(OH, full))
    a, d = count_changes(diff_text)
    total_add += a
    total_del += d
    h.append('<tr><td>%d</td><td>%s</td><td><a href="#file%d">%s</a></td><td>%s</td><td class="add">+%d</td><td class="del">-%d</td></tr>' % (idx, mod, idx, short, desc, a, d))
    idx += 1
for mod, short, full, desc in new_files:
    fpath = os.path.join(OH, full)
    lines = file_lines(fpath)
    total_add += lines
    h.append('<tr><td>%d</td><td>%s</td><td><a href="#file%d">%s</a> <span class="new-tag">NEW</span></td><td>%s</td><td class="add">+%d</td><td class="del">-0</td></tr>' % (idx, mod, idx, short, desc, lines))
    idx += 1
h.append('<tr style="font-weight:bold"><td colspan="4">合计</td><td class="add">+%d</td><td class="del">-%d</td></tr>' % (total_add, total_del))
h.append('</table>')
h.append('<div class="summary">共修改 <strong>10</strong> 个文件，新增 <strong>2</strong> 个文件。补丁范围覆盖 Mission 多 Ability 栈、Android 进程启动路由、APK 安装框架。</div>')

# Chapter 2: ability_rt diffs
h.append('<h2 id="ch2">2. ability_rt 补丁详情</h2>')
idx = 1
for mod, short, full, desc in files:
    if mod == "ability_rt":
        diff_text = get_diff(os.path.join(OH, full))
        if diff_text:
            h.append('<h3 id="file%d">%s</h3>' % (idx, short))
            h.append('<p>%s</p>' % desc)
            h.append('<pre class="diff">%s</pre>' % diff_to_html_lines(diff_text))
    idx += 1

# Chapter 3: bundle_framework diffs
h.append('<h2 id="ch3">3. bundle_framework 补丁详情</h2>')
idx = 1
for mod, short, full, desc in files:
    if mod == "bundle_framework":
        diff_text = get_diff(os.path.join(OH, full))
        if diff_text:
            h.append('<h3 id="file%d">%s</h3>' % (idx, short))
            h.append('<p>%s</p>' % desc)
            h.append('<pre class="diff">%s</pre>' % diff_to_html_lines(diff_text))
    idx += 1

# Chapter 4: New files
h.append('<h2 id="ch4">4. 新增文件</h2>')
nidx = len(files) + 1
for mod, short, full, desc in new_files:
    fpath = os.path.join(OH, full)
    lines = file_lines(fpath)
    h.append('<h3 id="file%d">%s <span class="new-tag">NEW</span></h3>' % (nidx, short))
    h.append('<p>%s（%d 行）</p>' % (desc, lines))
    with open(fpath, "r") as f:
        content = f.read()
    h.append('<pre class="diff"><span class="diff-add">%s</span></pre>' % html.escape(content))
    nidx += 1

# Chapter 5: Skipped patches
h.append('<h2 id="ch5">5. 未应用的补丁</h2>')
h.append("""<p>以下补丁因目标平台不匹配而未应用：</p>
<table>
<tr><th>补丁目录</th><th>原因</th></tr>
<tr><td>ohos_patches/build/</td><td>针对 DAYU600 (aarch64) 的 GN 构建补丁，不适用于当前 DAYU200 (rk3568, arm32)</td></tr>
<tr><td>ohos_patches/third_party/musl/</td><td>针对 aarch64 的 musl syscall 修复，arm32 无此问题</td></tr>
<tr><td>ohos_patches/graphic_2d/</td><td>rs_buffer_reclaim 补丁，与 arm32 编译无关</td></tr>
</table>
""")

h.append('</body></html>')

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(h))
print("Report generated: %s" % OUT)
print("Total: +%d -%d" % (total_add, total_del))
