#!/usr/bin/env python3
"""
Generate one self-contained HTML strategy page per Fn Concept Domain.

Each page contains:
- A human-readable summary at the top.
- Collapsible detailed sections from docs/concepts/Fnxx/.
- A link back to the main strategy review console.
- A placeholder for headless review records.

Run:
    python3 src/tools/build-fnxx-strategy-pages.py
"""

import json
import markdown
import re
import yaml
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONCEPTS_DIR = ROOT / "docs" / "concepts"
IMPROVED_DIR = ROOT / "docs" / "decisions" / "fnxx-strategies" / "improved-sources"
OUTPUT_DIR = ROOT / "docs" / "decisions" / "fnxx-strategies"
REVIEWS_DIR = ROOT / "docs" / "decisions" / "fnxx-strategies" / "reviews"
SPEC_FILE = ROOT / "spec" / "concept-graph.yaml"

ALL_FN = [f"Fn{n:02d}" for n in range(1, 13)]

CONCEPT_DETAILS = {
    "Fn01": {
        "title": "APK 安装与包元数据",
        "summary": "解析 APK 中的 AndroidManifest.xml（AXML）、签名证书、声明权限，并将结果映射为 OpenHarmony BMS 可识别的 ability 元数据。",
        "role_in_groups": "Group B 和 Group C 的前提：Activity/Service 组件解析与包身份。",
        "leading_hypothesis": "同一个 AXML 解析器为 BMS 同时输出 PAGE Activity 和 SERVICE/EXTENSION 元数据。",
        "evidence": "PAGE Activity 元数据路径已在 D600 上跑通；ServiceExtension 元数据投影 v1 仅完成 source-level 测试，尚未 build/deploy 到设备。",
        "blockers": ["BMS 当前只注册 PAGE abilities", "ServiceExtension 元数据未在设备上验证"],
        "falsifiers": ["APK 安装后签名/权限元数据与 Android 侧不一致", "Service 声明被 BMS 忽略导致 Fn07 无目标"]
    },
    "Fn02": {
        "title": "进程、Runtime、JNI 与 Native",
        "summary": "负责 appspawn-x fork 进程、加载 Android Runtime（ART）、JNI/native 库的运行时环境。",
        "role_in_groups": "所有组的运行时底座；不在当前统一决策核心范围内。",
        "leading_hypothesis": "保留 AOSP ART + libart/boot image 在 OH 进程内运行，由 Bridge 在 OS 边界翻译。",
        "evidence": "HelloWorld r18 能在 D600 上冷启动并进入 Activity 生命周期；arm32/native-library 路径仍在建设中。",
        "blockers": ["arm32 runtime 支持未证明", "native-library dlopen/boot-image 加载证据不足"],
        "falsifiers": ["同一 APK 在相同 generation 出现不同进程身份", "ART boot image 加载导致崩溃或权限错误"]
    },
    "Fn03": {
        "title": "Activity 生命周期",
        "summary": "把 OH Ability 生命周期事件（create/start/resume/pause/stop/destroy）翻译成 Android Activity 的 create/start/resume/pause/stop/destroy 回调。",
        "role_in_groups": "Group A 和 Group B 的前提：窗口 token 生成、ActivityThread 调度。",
        "leading_hypothesis": "OH UIAbilityLifecycleManager 通知通过 Bridge 边界映射为 Android ActivityThread 调度。",
        "evidence": "HelloWorld r18 在 D600 上到达 onCreate/onResume；per-Action 合同升级和独立评审仍在进行。",
        "blockers": ["生命周期 Action 合同尚未全部升级", "teardown/generation 失效未充分验证"],
        "falsifiers": ["Activity attach/resume/finish 顺序与 Android 语义不一致", "窗口 generation 在 Activity 销毁后仍然存活"]
    },
    "Fn04": {
        "title": "Window、Surface 与 Rendering",
        "summary": "把 Android 的 Window/ViewRootImpl/Surface 映射到 OH 的 Ability session/SceneBoard/RS SurfaceNode，并提供 EGL/native-window 目标。",
        "role_in_groups": "Group A 核心：决定窗口 token、surface 所有权和 present 收据。",
        "leading_hypothesis": "R1b：使用 Ability-host-parented specific content child session，复用 SceneBoard 窗口层次结构。",
        "evidence": "D600 r18 在 board 5eab... 上观察到 parent-child session 28→34、RS node/producer/EGL 路径和可见 occlusion；但尚未排除 RSSurfaceNode teardown 假阳性，也未完成 lifecycle/teardown 和 forged-PID 反面案例。",
        "blockers": ["R1a direct hostSession reuse 未验证", "source→binary provenance 未闭环", "pixel/ANR/failure 收据不足"],
        "falsifiers": ["窗口 generation 在 Activity 销毁后存活", "帧被报告为上屏但实际无像素", "伪造 PID 能绕过 owner 检查"]
    },
    "Fn05": {
        "title": "输入",
        "summary": "把 OH MMI 的触摸/按键事件转换为 Android MotionEvent/KeyEvent，通过 InputChannel 投递到 app 的 InputEventReceiver。",
        "role_in_groups": "Group A 核心：依赖 Fn04 的窗口 identity 和 geometry。",
        "leading_hypothesis": "native InputChannel + receiver-owner Looper，指针事件用 hit-test target/transform，按键事件用 focus epoch。",
        "evidence": "D600 r18 上单 generation 观察到 DOWN/UP 事件到达 Android main 并返回 FINISHED；但 FINISHED-gated OH acknowledgement（MarkProcessed）仍失败，system-path 双收据 join 未闭环。",
        "blockers": ["FINISHED-gated OH acknowledgement 未修复", "T01–T09 完整矩阵未跑完", "teardown/wrong-seq/timeout 反面案例不足"],
        "falsifiers": ["FINISHED 返回但 host 未收到 MarkProcessed", "错误窗口收到输入事件", "stale focus epoch 让按键进入错误目标"]
    },
    "Fn06": {
        "title": "Intent / Task",
        "summary": "把 Android Intent（component、action、flags、extras）转换为 OH Want，并决定 Activity 启动的 Task 复用/新建策略。",
        "role_in_groups": "Group B 核心：与 Fn07 共享 typed Intent/Want 转换。",
        "leading_hypothesis": "R2：在 OH UIAbilityLifecycleManager::NotifySCBToStartUIAbility 处做 observation-only probe，不动态 hook MissionListManager。",
        "evidence": "R1 sidecar 缺乏 privilege/closure；R2 probe patch 已 frozen 并通过 `git apply --check`，但尚未 build/deploy 到 OH。",
        "blockers": ["R1 sidecar 无 privilege 关闭方案", "R2 probe 未在设备上运行"],
        "falsifiers": ["startActivity Intent 转换与 startService 转换不一致", "Task 复用策略导致错误 Activity 上屏", "launch transaction 丢失 generation 绑定"]
    },
    "Fn07": {
        "title": "Android Service",
        "summary": "把 Android Service 的 startService/bindService/unbindService/publishService 映射到 OH ServiceExtensionAbility 或同 runtime authority，并返回可用的 Android IBinder。",
        "role_in_groups": "Group B 核心：依赖 Fn01 元数据、Fn03 调度、Fn08 授权、Fn11 Binder 端点。",
        "leading_hypothesis": "bounded same-runtime ServiceLifecycleAuthority + valid ServiceExtension host + token-owned endpoint envelope。",
        "evidence": "D00 BLOCKED_AS_BUILT：四 Service raw APK 安装后 BMS 只注册 PAGE 且 extensionInfos=[]。metadata-projection v1（AXML 解析器、installer JSON、BMS patch）source-tested，但 libapk_installer/libbms.z.so/framework JAR build 和 D00 rerun 均未完成。",
        "blockers": ["BMS 只输出 PAGE abilities", "ServiceExtension host 未在设备上验证", "Binder 端点映射未实现"],
        "falsifiers": ["startService Intent 转换与 startActivity 转换矛盾", "Service Binder 投递到错误 generation 的客户端", "bindService 返回 null 或无效 endpoint"]
    },
    "Fn08": {
        "title": "权限 / 身份 / 沙箱",
        "summary": "把 Android 的包签名、声明权限、UID、caller identity 映射到 OH AccessToken/sandbox，并在受保护 API 边界做出 allow/deny 判决。",
        "role_in_groups": "Group C 核心：Groups A/B 的 authority floor。",
        "leading_hypothesis": "按权限族混用 direct boundary credential 与最小特权 broker；保留 Android package/permission/signing 为语义所有者。",
        "evidence": "多块板子观察到 token 分配，但 signing/permission 字段为空；protected-call receipt、stale-generation denial、revoke invalidation 均未完成。早前的 4-label R1/R2 评分已被挑战评审撤回。",
        "blockers": ["签名/权限字段为空", "protected-call receipt 缺失", "sandbox 隔离 verdict 未证明"],
        "falsifiers": ["错误/stale identity 在受保护调用中成功", "权限撤销后旧 generation 仍能访问", "caller uid/pid 在桥接 IPC 中丢失"]
    },
    "Fn09": {
        "title": "Resource / ContentProvider",
        "summary": "把 Android 资源系统（assets、res、typeface）和 ContentProvider 的 query/insert/update/delete/file 操作映射到 OH。",
        "role_in_groups": "Group C 下游：依赖 Fn08 身份授权，向 Fn10 提供图形资源输入。",
        "leading_hypothesis": "在 APK 内保留 Android AssetManager，ContentProvider 按 authority/caller 做边界翻译。",
        "evidence": "当前为 hypothesis-level；无独立 D600 evidence。Unity G6–G11 第一批 APK 通过静态身份门，但设备运行未开始。",
        "blockers": ["Resource 路径与 OH 文件系统映射未验证", "Provider URI/authority 转换未实现"],
        "falsifiers": ["资源解析返回错误 density 或类型", "跨应用 ContentProvider 调用未授权成功"]
    },
    "Fn10": {
        "title": "HWUI / Skia / Graphics JNI",
        "summary": "让 Android 的 HWUI/Skia/graphics JNI 在 OH 上找到所需的 buffer、surface、字体、图片解码器和 GL/EGL 上下文。",
        "role_in_groups": "Group A 核心：消费 Fn04 的 surface 和 Fn09 的资源。",
        "leading_hypothesis": "RS SurfaceNode/EGL native window 作为 buffer target；Android graphics JNI 通过 Bridge 边界获取 OH producer surface。",
        "evidence": "hypothesis-level；无独立 Action-level evidence。",
        "blockers": ["surface/Binder 端点未闭环", "graphics JNI 注册和 buffer 队列未验证"],
        "falsifiers": ["HWUI 无法创建 EGL surface", "帧提交成功但无 present receipt", "解码资源失败导致黑屏"]
    },
    "Fn11": {
        "title": "系统服务 / Binder / Framework Native",
        "summary": "把 Android 的系统服务查找（ServiceManager）、Binder IPC、BroadcastReceiver、Property/Handler/Process 等 framework native 语义映射到 OH。",
        "role_in_groups": "Group C 核心：Fn07 ServiceBinder 端点输出；Fn08 调用者身份。",
        "leading_hypothesis": "Android Binder 在本地保留或映射为 OH remote-object proxy；系统服务按 name/descriptor 提供兼容 facade。",
        "evidence": "hypothesis-level；ServiceManager stub G13 FAIL（无 app process，无交互）。",
        "blockers": ["Binder endpoint 映射未实现", "CommonEvent/系统服务 facade 未验证"],
        "falsifiers": ["published Binder 无法被客户端使用", "caller token 在跨边界调用中丢失", "系统服务返回错误 generation 的代理"]
    },
    "Fn12": {
        "title": "Logging / Trace API / 并发",
        "summary": "把 Android 的 log/trace API 映射到 OH hilog/hitrace，并提供并发/安装隔离的诊断能力。",
        "role_in_groups": "横向支撑：所有组都需要诊断；Fn02/Fn01 需要并发隔离证据。",
        "leading_hypothesis": "Bridge 在边界把 Android log 格式映射为 OH hilog，保留 pid/tid/generation 上下文。",
        "evidence": "hypothesis-level；依赖其他 Concept 的进程/身份模型。",
        "blockers": ["进程/身份模型未定", "并发/安装隔离的 D600 证据缺失"],
        "falsifiers": ["log 中的 pid/tid 无法对应到真实进程", "并发安装导致 generation 泄漏"]
    },
}

DOC_FILES = [
    ("CONCEPT_DOMAIN.md", "Concept Domain 定义"),
    ("BRIDGE_CONTRACT.md", "Bridge Contract"),
    ("ANDROID_MODEL.md", "Android 侧模型"),
    ("OPENHARMONY_MODEL.md", "OpenHarmony 侧模型"),
    ("ROUTE_SPACE.md", "路线空间"),
    ("STRATEGY.md", "Strategy"),
    ("STRATEGY_DECISION.md", "Strategy Decision"),
    ("ACTION_MAP.md", "Action 映射"),
    ("RESEARCH_QUESTIONS.md", "研究问题"),
    ("CASE_LEDGER.md", "历史案例"),
    ("PATTERN_CATALOG.md", "模式目录"),
    ("SUBCONCEPT_MAP.md", "Subconcept 映射"),
    ("REVIEW_LOG.md", "Review Log"),
    ("D600_TEST_PLAN.md", "D600 测试计划"),
    ("CURRENT_BRIDGE_AUDIT.md", "Current Bridge Audit"),
]


def load_graph():
    with open(SPEC_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def concept_status(graph, fn):
    assessments = graph.get("direction_assessments", {})
    if fn not in assessments:
        return "UNASSESSED"
    dirs = assessments[fn]
    statuses = {d.get("status", "UNASSESSED") for d in dirs.values()}
    if "BLOCKED" in statuses:
        return "BLOCKED"
    if statuses == {"EVIDENCED"}:
        return "EVIDENCED"
    if "HYPOTHESIS" in statuses or "UNASSESSED" in statuses:
        return "PARTIAL"
    return "PARTIAL"


def read_doc(fn, name):
    # Prefer improved-sources (post-review, human-friendly) over raw concepts.
    improved_path = IMPROVED_DIR / fn / name
    if improved_path.exists():
        return improved_path.read_text(encoding="utf-8")
    legacy_path = CONCEPTS_DIR / fn / name
    if legacy_path.exists():
        return legacy_path.read_text(encoding="utf-8")
    return None


def clean_blockquote(text):
    return " ".join(line.lstrip(">").strip() for line in text.splitlines() if line.strip())


def is_spec_gap(text):
    return not text or text.upper().startswith("SPEC_GAP")


def extract_in_plain_words(fn):
    """Extract the first human-friendly paragraph from CONCEPT_DOMAIN.md."""
    text = read_doc(fn, "CONCEPT_DOMAIN.md")
    if not text:
        return ""

    patterns = [
        (r"#+\s*In plain words[:：]?\s*\n+([^#\n][^\n]*(?:\n[^#\n][^\n]*)*)", 1, False),
        (r">\s*\*\*What this Concept covers:\*\*\s*([^\n]+)\n>\s*\n>\s*\*\*Why it matters:\*\*\s*([^\n]+)", 2, True),
        (r">\s*用大白话说[:：]\s*([^\n]+(?:\n>[^\n]+)*)", 1, True),
        (r">\s*\*\*Freshman-friendly overview:\*\*\s*([^\n]+(?:\n>[^\n]+)*)", 1, True),
        (r">\s*\*\*Plain language\*\*[:：]?\s*([^\n]+(?:\n>[^\n]+)*)", 1, True),
        (r">\s*\*\*freshman 导读\*\*[:：]?\s*([^\n]+(?:\n>[^\n]+)*)", 1, True),
        (r">\s*\*\*In plain words[:：]?\*\*\s*([^\n]+(?:\n>[^\n]+)*)", 1, True),
    ]

    for pattern, group_count, is_bq in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            if group_count == 2:
                raw = " ".join(m.group(i).strip() for i in range(1, group_count + 1))
            else:
                raw = m.group(1).strip()
            cleaned = clean_blockquote(raw) if is_bq else raw
            if not is_spec_gap(cleaned):
                return cleaned

    # Last fallback: first substantial blockquote or paragraph after title
    lines = text.splitlines()
    para = []
    for line in lines[1:]:
        l = line.strip()
        if not l:
            continue
        if l.startswith("#"):
            if para:
                break
            continue
        para.append(l.lstrip(">").strip())
        if len(para) >= 4:
            break
    joined = " ".join(para).strip()
    return joined if not is_spec_gap(joined) else ""


def review_links(fn):
    """Return available review report filenames for a Concept."""
    links = []
    for role, label in [("freshman", "大一学生"), ("ieee", "IEEE 编辑")]:
        for rnd in [1, 2]:
            name = f"{fn}-round{rnd}-{role}.md"
            if (REVIEWS_DIR / name).exists():
                links.append((f"reviews/{name}", f"Round {rnd} · {label}"))
    return links


def md_to_html(text):
    if not text:
        return "<p class='empty'>(此文档当前为空或不存在)</p>"
    return markdown.markdown(text, extensions=["tables", "fenced_code"])


def render_summary_card(fn, details, status):
    blockers = "\n".join(f"<li>{b}</li>" for b in details.get("blockers", []))
    falsifiers = "\n".join(f"<li>{f}</li>" for f in details.get("falsifiers", []))
    plain_words = extract_in_plain_words(fn)
    plain_html = f'<div class="summary-block wide plain-words"><h4>给人类看的摘要</h4><p>{plain_words}</p></div>' if plain_words else ""
    reviews = review_links(fn)
    if reviews:
        review_html = '<div class="summary-block wide"><h4>独立评审报告</h4><p>' + " · ".join(f'<a href="{href}" style="color:var(--accent)">{label}</a>' for href, label in reviews) + '</p></div>'
    else:
        review_html = ""
    return f"""
    <div class="summary-card">
      <div class="summary-header">
        <h2>{fn} — {details.get('title', '')}</h2>
        <span class="status {status.lower()}">{status}</span>
      </div>
      <p class="summary-lead">{details.get('summary', '')}</p>
      <div class="summary-grid">
        {plain_html}
        <div class="summary-block">
          <h4>在统一分组中的角色</h4>
          <p>{details.get('role_in_groups', '')}</p>
        </div>
        <div class="summary-block">
          <h4>当前主导假设</h4>
          <p>{details.get('leading_hypothesis', '')}</p>
        </div>
        <div class="summary-block wide">
          <h4>证据状态</h4>
          <p>{details.get('evidence', '')}</p>
        </div>
        <div class="summary-block">
          <h4>阻塞项</h4>
          <ul>{blockers}</ul>
        </div>
        <div class="summary-block">
          <h4>待证伪项</h4>
          <ul>{falsifiers}</ul>
        </div>
        {review_html}
      </div>
    </div>
    """


def render_detail_sections(fn):
    sections = []
    for filename, title in DOC_FILES:
        content = read_doc(fn, filename)
        if not content:
            continue
        section_id = "sec-" + filename.replace(".", "-")
        html_content = md_to_html(content)
        sections.append(f"""
        <section class="detail-section" id="{section_id}">
          <button class="section-toggle" onclick="toggleSection('{section_id}')">
            <span>{title}</span>
            <span class="toggle-icon">+</span>
          </button>
          <div class="section-content hidden">
            {html_content}
          </div>
        </section>
        """)
    if not sections:
        return "<p class='empty'>暂无详细文档。</p>"
    return "\n".join(sections)


def build_page(fn, details, status):
    summary = render_summary_card(fn, details, status)
    detail_sections = render_detail_sections(fn)
    generated_at = datetime.now().isoformat()

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{fn} Strategy — {details.get('title', '')}</title>
  <style>
    :root {{
      --bg: #0f172a;
      --surface: #1e293b;
      --surface-2: #334155;
      --text: #f8fafc;
      --text-dim: #94a3b8;
      --accent: #38bdf8;
      --ok: #22c55e;
      --warn: #eab308;
      --danger: #ef4444;
      --neutral: #64748b;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
    }}
    header {{
      background: var(--surface);
      border-bottom: 1px solid var(--surface-2);
      padding: 1rem 2rem;
      position: sticky;
      top: 0;
      z-index: 10;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 0.75rem;
    }}
    header h1 {{ margin: 0; font-size: 1.25rem; }}
    header a {{
      color: var(--accent);
      text-decoration: none;
      border: 1px solid var(--accent);
      padding: 0.4rem 0.8rem;
      border-radius: 0.4rem;
      font-size: 0.9rem;
    }}
    header a:hover {{ background: rgba(56, 189, 248, 0.1); }}
    main {{ padding: 2rem; max-width: 1000px; margin: 0 auto; }}
    .summary-card {{
      background: var(--surface);
      border: 1px solid var(--surface-2);
      border-radius: 0.75rem;
      padding: 1.5rem;
      margin-bottom: 2rem;
    }}
    .summary-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
      flex-wrap: wrap;
      gap: 0.5rem;
    }}
    .summary-header h2 {{ margin: 0; color: var(--accent); }}
    .summary-lead {{ font-size: 1.1rem; color: #e2e8f0; margin-bottom: 1.5rem; }}
    .summary-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }}
    .summary-block {{
      background: var(--bg);
      border: 1px solid var(--surface-2);
      border-radius: 0.5rem;
      padding: 1rem;
    }}
    .summary-block.wide {{ grid-column: 1 / -1; }}
    .summary-block.plain-words {{
      border-left: 3px solid var(--accent);
      background: rgba(56, 189, 248, 0.08);
    }}
    .summary-block.plain-words h4 {{ color: var(--accent); }}
    .summary-block a {{ color: var(--accent); }}
    .summary-block h4 {{
      margin: 0 0 0.5rem 0;
      color: var(--accent);
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .summary-block p {{ margin: 0; color: #e2e8f0; }}
    .summary-block ul {{ margin: 0.25rem 0 0 0; padding-left: 1.2rem; color: #e2e8f0; }}
    .summary-block li {{ margin-bottom: 0.3rem; }}
    .status {{
      display: inline-block;
      padding: 0.25rem 0.75rem;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
    }}
    .status.evidenced {{ background: rgba(34, 197, 94, 0.2); color: var(--ok); }}
    .status.partial {{ background: rgba(234, 179, 8, 0.2); color: var(--warn); }}
    .status.blocked {{ background: rgba(239, 68, 68, 0.2); color: var(--danger); }}
    .status.unassessed {{ background: rgba(100, 116, 139, 0.2); color: var(--neutral); }}
    h3 {{ color: var(--text); border-bottom: 1px solid var(--surface-2); padding-bottom: 0.5rem; }}
    .detail-section {{ margin-bottom: 1rem; }}
    .section-toggle {{
      width: 100%;
      background: var(--surface);
      border: 1px solid var(--surface-2);
      color: var(--text);
      padding: 0.9rem 1rem;
      border-radius: 0.5rem;
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 1rem;
      text-align: left;
    }}
    .section-toggle:hover {{ border-color: var(--accent); }}
    .toggle-icon {{ font-size: 1.2rem; color: var(--accent); }}
    .section-content {{
      background: var(--surface);
      border: 1px solid var(--surface-2);
      border-top: none;
      border-radius: 0 0 0.5rem 0.5rem;
      padding: 1.25rem;
    }}
    .section-content.hidden {{ display: none; }}
    .section-content h1, .section-content h2, .section-content h3 {{
      margin-top: 1.5rem;
      color: var(--accent);
    }}
    .section-content p {{ color: #e2e8f0; }}
    .section-content ul, .section-content ol {{ padding-left: 1.5rem; }}
    .section-content li {{ margin-bottom: 0.4rem; }}
    .section-content table {{
      width: 100%;
      border-collapse: collapse;
      margin: 1rem 0;
    }}
    .section-content th, .section-content td {{
      border: 1px solid var(--surface-2);
      padding: 0.6rem;
      text-align: left;
    }}
    .section-content th {{ background: var(--surface-2); }}
    .section-content code {{
      background: var(--bg);
      padding: 0.15rem 0.35rem;
      border-radius: 0.25rem;
      font-family: "SF Mono", Monaco, monospace;
      font-size: 0.9em;
    }}
    .section-content pre {{
      background: var(--bg);
      padding: 1rem;
      border-radius: 0.5rem;
      overflow-x: auto;
    }}
    .empty {{ color: var(--text-dim); font-style: italic; }}
    .review-section {{
      margin-top: 2rem;
      background: var(--surface);
      border: 1px solid var(--surface-2);
      border-radius: 0.75rem;
      padding: 1.5rem;
    }}
    .footer {{
      margin-top: 3rem;
      padding-top: 1rem;
      border-top: 1px solid var(--surface-2);
      color: var(--text-dim);
      font-size: 0.85rem;
    }}
    @media (max-width: 700px) {{
      .summary-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>{fn} Strategy</h1>
    <a href="../strategy-review-console.html">← 返回 Strategy Review Console</a>
  </header>

  <main>
    {summary}

    <h3>详细内容</h3>
    <p style="color: var(--text-dim); margin-bottom: 1rem;">点击每个标题展开对应文档。</p>
    {detail_sections}

    <div class="review-section">
      <h3>Headless 评审记录</h3>
      <p style="color: var(--text-dim);">此区域供独立 headless reviewer 填写。当前评审报告见
        <a href="../reviews/" style="color: var(--accent);">reviews/</a> 目录。</p>
    </div>

    <div class="footer">
      Generated at {generated_at} from docs/decisions/fnxx-strategies/improved-sources/{fn}/ (with fallback to docs/concepts/{fn}/).
    </div>
  </main>

  <script>
    function toggleSection(id) {{
      const content = document.querySelector('#' + id + ' .section-content');
      const icon = document.querySelector('#' + id + ' .toggle-icon');
      if (content.classList.contains('hidden')) {{
        content.classList.remove('hidden');
        icon.textContent = '−';
      }} else {{
        content.classList.add('hidden');
        icon.textContent = '+';
      }}
    }}
  </script>
</body>
</html>
"""


def main():
    graph = load_graph()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for fn in ALL_FN:
        details = CONCEPT_DETAILS.get(fn, {})
        status = concept_status(graph, fn)
        html = build_page(fn, details, status)
        out_path = OUTPUT_DIR / f"{fn}.html"
        out_path.write_text(html, encoding="utf-8")
        print(f"Generated: {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
