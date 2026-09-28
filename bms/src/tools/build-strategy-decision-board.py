#!/usr/bin/env python3
"""
Build a strategy decision board in the style of L_APP_MATURITY_BOARD.html.

References:
- file:///opt/21.Game/80.kanban/coordination/m206-absorption/L_APP_MATURITY_BOARD.html
- docs/decisions/strategy-review-console.html
- docs/decisions/fnxx-strategies/Fnxx.html

Run:
    python3 src/tools/build-strategy-decision-board.py
"""

import json
import re
import yaml
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC_FILE = ROOT / "spec" / "concept-graph.yaml"
IMPROVED_DIR = ROOT / "docs" / "decisions" / "fnxx-strategies" / "improved-sources"
OUTPUT_FILE = ROOT / "docs" / "decisions" / "strategy-decision-board.html"

ALL_FN = [f"Fn{n:02d}" for n in range(1, 13)]

GROUPS = {
    "A": {
        "name": "可见表面组 / Window · Input · Graphics",
        "concepts": ["Fn03", "Fn04", "Fn05", "Fn10"],
        "core_object": "generation-bound window/session/surface and callback thread",
    },
    "B": {
        "name": "组件调度组 / Intent · Task · Service",
        "concepts": ["Fn01", "Fn03", "Fn06", "Fn07", "Fn08", "Fn11"],
        "core_object": "typed Intent/Want, task/service authority, caller identity and Binder endpoint",
    },
    "C": {
        "name": "身份授权基板 / Package · Permission · Binder",
        "concepts": ["Fn01", "Fn08", "Fn11"],
        "core_object": "package/signing identity, AccessToken/sandbox generation, caller token and verdict",
    },
}

CHOICES = {
    "p": "选择主导建议 / Select primary",
    "b": "选择备选路线 / Select backup",
    "e": "继续做实验 / Evidence building",
    "h": "历史成功实践优先 / Historical precedent",
    "m": "维持历史决策 / Maintain historical decision",
    "r": "看参考文档 / View reference",
    "s": "跳过，保持当前状态 / Skip",
}

CHOICE_DETAILS = {
    "p": {
        "label": "选择主导建议",
        "hint": "当前证据足以支持主要推荐路线；记录选择理由和回滚条件。",
        "risk": "若 falsifier 未关闭，可能过早锁定路线。",
    },
    "b": {
        "label": "选择备选路线",
        "hint": "主导假设被部分证伪或证据不足，启用备选方案。",
        "risk": "备选路线可能同样缺少运行时证据。",
    },
    "e": {
        "label": "继续做实验",
        "hint": "证据尚未充分；继续运行 D600/source 实验以关闭 falsifier。",
        "risk": "实验可能无限期拖延决策；需设定明确的停止条件。",
    },
    "h": {
        "label": "历史成功实践优先",
        "hint": "参考已验证的历史案例（Anbox/Waydroid/HanBing 等）作为主导依据。",
        "risk": "历史案例的上下文可能与当前 OH/AOSP 基线不匹配。",
    },
    "m": {
        "label": "维持历史决策",
        "hint": "保持此前已记录的选择，除非有新证据推翻。",
        "risk": "历史决策可能基于过时的证据或假设。",
    },
    "r": {
        "label": "看参考文档",
        "hint": "不立即决策；要求先阅读指定参考文档或源码。",
        "risk": "仅阅读而不形成决策会阻塞下游工作。",
    },
    "s": {
        "label": "跳过，保持当前状态",
        "hint": "本轮不处理；保留当前状态，稍后重新 review。",
        "risk": "关键决策被无限期推迟。",
    },
}

CONCEPT_DETAILS = {
    "Fn01": {
        "title": "APK 安装与包元数据",
        "summary": "解析 APK 中的 AndroidManifest.xml（AXML）、签名证书、声明权限，并将结果映射为 OpenHarmony BMS 可识别的 ability 元数据。",
        "role_in_groups": "Group B 和 Group C 的前提：Activity/Service 组件解析与包身份。",
        "leading_hypothesis": "同一个 AXML 解析器为 BMS 同时输出 PAGE Activity 和 SERVICE/EXTENSION 元数据。",
        "evidence": "PAGE Activity 元数据路径已在 D600 上跑通；ServiceExtension 元数据投影 v1 仅完成 source-level 测试，尚未 build/deploy 到设备。",
        "blockers": ["BMS 当前只注册 PAGE abilities", "ServiceExtension 元数据未在设备上验证"],
        "falsifiers": ["APK 安装后签名/权限元数据与 Android 侧不一致", "Service 声明被 BMS 忽略导致 Fn07 无目标"],
    },
    "Fn02": {
        "title": "进程、Runtime、JNI 与 Native",
        "summary": "负责 appspawn-x fork 进程、加载 Android Runtime（ART）、JNI/native 库的运行时环境。",
        "role_in_groups": "所有组的运行时底座；不在当前统一决策核心范围内。",
        "leading_hypothesis": "保留 AOSP ART + libart/boot image 在 OH 进程内运行，由 Bridge 在 OS 边界翻译。",
        "evidence": "HelloWorld r18 能在 D600 上冷启动并进入 Activity 生命周期；arm32/native-library 路径仍在建设中。",
        "blockers": ["arm32 runtime 支持未证明", "native-library dlopen/boot-image 加载证据不足"],
        "falsifiers": ["同一 APK 在相同 generation 出现不同进程身份", "ART boot image 加载导致崩溃或权限错误"],
    },
    "Fn03": {
        "title": "Activity 生命周期",
        "summary": "把 OH Ability 生命周期事件（create/start/resume/pause/stop/destroy）翻译成 Android Activity 的 create/start/resume/pause/stop/destroy 回调。",
        "role_in_groups": "Group A 和 Group B 的前提：窗口 token 生成、ActivityThread 调度。",
        "leading_hypothesis": "OH UIAbilityLifecycleManager 通知通过 Bridge 边界映射为 Android ActivityThread 调度。",
        "evidence": "HelloWorld r18 在 D600 上到达 onCreate/onResume；per-Action 合同升级和独立评审仍在进行。",
        "blockers": ["生命周期 Action 合同尚未全部升级", "teardown/generation 失效未充分验证"],
        "falsifiers": ["Activity attach/resume/finish 顺序与 Android 语义不一致", "窗口 generation 在 Activity 销毁后仍然存活"],
    },
    "Fn04": {
        "title": "Window、Surface 与 Rendering",
        "summary": "把 Android 的 Window/ViewRootImpl/Surface 映射到 OH 的 Ability session/SceneBoard/RS SurfaceNode，并提供 EGL/native-window 目标。",
        "role_in_groups": "Group A 核心：决定窗口 token、surface 所有权和 present 收据。",
        "leading_hypothesis": "R1b：使用 Ability-host-parented specific content child session，复用 SceneBoard 窗口层次结构。",
        "evidence": "D600 r18 在 board 5eab... 上观察到 parent-child session 28→34、RS node/producer/EGL 路径和可见 occlusion；但尚未排除 RSSurfaceNode teardown 假阳性，也未完成 lifecycle/teardown 和 forged-PID 反面案例。",
        "blockers": ["R1a direct hostSession reuse 未验证", "source→binary provenance 未闭环", "pixel/ANR/failure 收据不足"],
        "falsifiers": ["窗口 generation 在 Activity 销毁后存活", "帧被报告为上屏但实际无像素", "伪造 PID 能绕过 owner 检查"],
    },
    "Fn05": {
        "title": "输入",
        "summary": "把 OH MMI 的触摸/按键事件转换为 Android MotionEvent/KeyEvent，通过 InputChannel 投递到 app 的 InputEventReceiver。",
        "role_in_groups": "Group A 核心：依赖 Fn04 的窗口 identity 和 geometry。",
        "leading_hypothesis": "native InputChannel + receiver-owner Looper，指针事件用 hit-test target/transform，按键事件用 focus epoch。",
        "evidence": "D600 r18 上单 generation 观察到 DOWN/UP 事件到达 Android main 并返回 FINISHED；但 FINISHED-gated OH acknowledgement（MarkProcessed）仍失败，system-path 双收据 join 未闭环。",
        "blockers": ["FINISHED-gated OH acknowledgement 未修复", "T01–T09 完整矩阵未跑完", "teardown/wrong-seq/timeout 反面案例不足"],
        "falsifiers": ["FINISHED 返回但 host 未收到 MarkProcessed", "错误窗口收到输入事件", "stale focus epoch 让按键进入错误目标"],
    },
    "Fn06": {
        "title": "Intent / Task",
        "summary": "把 Android Intent（component、action、flags、extras）转换为 OH Want，并决定 Activity 启动的 Task 复用/新建策略。",
        "role_in_groups": "Group B 核心：与 Fn07 共享 typed Intent/Want 转换。",
        "leading_hypothesis": "R2：在 OH UIAbilityLifecycleManager::NotifySCBToStartUIAbility 处做 observation-only probe，不动态 hook MissionListManager。",
        "evidence": "R1 sidecar 缺乏 privilege/closure；R2 probe patch 已 frozen 并通过 `git apply --check`，但尚未 build/deploy 到 OH。",
        "blockers": ["R1 sidecar 无 privilege 关闭方案", "R2 probe 未在设备上运行"],
        "falsifiers": ["startActivity Intent 转换与 startService 转换不一致", "Task 复用策略导致错误 Activity 上屏", "launch transaction 丢失 generation 绑定"],
    },
    "Fn07": {
        "title": "Android Service",
        "summary": "把 Android Service 的 startService/bindService/unbindService/publishService 映射到 OH ServiceExtensionAbility 或同 runtime authority，并返回可用的 Android IBinder。",
        "role_in_groups": "Group B 核心：依赖 Fn01 元数据、Fn03 调度、Fn08 授权、Fn11 Binder 端点。",
        "leading_hypothesis": "bounded same-runtime ServiceLifecycleAuthority + valid ServiceExtension host + token-owned endpoint envelope。",
        "evidence": "D00 BLOCKED_AS_BUILT：四 Service raw APK 安装后 BMS 只注册 PAGE 且 extensionInfos=[]。metadata-projection v1（AXML 解析器、installer JSON、BMS patch）source-tested，但 libapk_installer/libbms.z.so/framework JAR build 和 D00 rerun 均未完成。",
        "blockers": ["BMS 只输出 PAGE abilities", "ServiceExtension host 未在设备上验证", "Binder 端点映射未实现"],
        "falsifiers": ["startService Intent 转换与 startActivity 转换矛盾", "Service Binder 投递到错误 generation 的客户端", "bindService 返回 null 或无效 endpoint"],
    },
    "Fn08": {
        "title": "权限 / 身份 / 沙箱",
        "summary": "把 Android 的包签名、声明权限、UID、caller identity 映射到 OH AccessToken/sandbox，并在受保护 API 边界做出 allow/deny 判决。",
        "role_in_groups": "Group C 核心：Groups A/B 的 authority floor。",
        "leading_hypothesis": "按权限族混用 direct boundary credential 与最小特权 broker；保留 Android package/permission/signing 为语义所有者。",
        "evidence": "多块板子观察到 token 分配，但 signing/permission 字段为空；protected-call receipt、stale-generation denial、revoke invalidation 均未完成。早前的 4-label R1/R2 评分已被挑战评审撤回。",
        "blockers": ["签名/权限字段为空", "protected-call receipt 缺失", "sandbox 隔离 verdict 未证明"],
        "falsifiers": ["错误/stale identity 在受保护调用中成功", "权限撤销后旧 generation 仍能访问", "caller uid/pid 在桥接 IPC 中丢失"],
    },
    "Fn09": {
        "title": "Resource / ContentProvider",
        "summary": "把 Android 资源系统（assets、res、typeface）和 ContentProvider 的 query/insert/update/delete/file 操作映射到 OH。",
        "role_in_groups": "Group C 下游：依赖 Fn08 身份授权，向 Fn10 提供图形资源输入。",
        "leading_hypothesis": "在 APK 内保留 Android AssetManager，ContentProvider 按 authority/caller 做边界翻译。",
        "evidence": "当前为 hypothesis-level；无独立 D600 evidence。Unity G6–G11 第一批 APK 通过静态身份门，但设备运行未开始。",
        "blockers": ["Resource 路径与 OH 文件系统映射未验证", "Provider URI/authority 转换未实现"],
        "falsifiers": ["资源解析返回错误 density 或类型", "跨应用 ContentProvider 调用未授权成功"],
    },
    "Fn10": {
        "title": "HWUI / Skia / Graphics JNI",
        "summary": "让 Android 的 HWUI/Skia/graphics JNI 在 OH 上找到所需的 buffer、surface、字体、图片解码器和 GL/EGL 上下文。",
        "role_in_groups": "Group A 核心：消费 Fn04 的 surface 和 Fn09 的资源。",
        "leading_hypothesis": "RS SurfaceNode/EGL native window 作为 buffer target；Android graphics JNI 通过 Bridge 边界获取 OH producer surface。",
        "evidence": "hypothesis-level；无独立 Action-level evidence。",
        "blockers": ["surface/Binder 端点未闭环", "graphics JNI 注册和 buffer 队列未验证"],
        "falsifiers": ["HWUI 无法创建 EGL surface", "帧提交成功但无 present receipt", "解码资源失败导致黑屏"],
    },
    "Fn11": {
        "title": "系统服务 / Binder / Framework Native",
        "summary": "把 Android 的系统服务查找（ServiceManager）、Binder IPC、BroadcastReceiver、Property/Handler/Process 等 framework native 语义映射到 OH。",
        "role_in_groups": "Group C 核心：Fn07 ServiceBinder 端点输出；Fn08 调用者身份。",
        "leading_hypothesis": "Android Binder 在本地保留或映射为 OH remote-object proxy；系统服务按 name/descriptor 提供兼容 facade。",
        "evidence": "hypothesis-level；ServiceManager stub G13 FAIL（无 app process，无交互）。",
        "blockers": ["Binder endpoint 映射未实现", "CommonEvent/系统服务 facade 未验证"],
        "falsifiers": ["published Binder 无法被客户端使用", "caller token 在跨边界调用中丢失", "系统服务返回错误 generation 的代理"],
    },
    "Fn12": {
        "title": "Logging / Trace API / 并发",
        "summary": "把 Android 的 log/trace API 映射到 OH hilog/hitrace，并提供并发/安装隔离的诊断能力。",
        "role_in_groups": "横向支撑：所有组都需要诊断；Fn02/Fn01 需要并发隔离证据。",
        "leading_hypothesis": "Bridge 在边界把 Android log 格式映射为 OH hilog，保留 pid/tid/generation 上下文。",
        "evidence": "hypothesis-level；依赖其他 Concept 的进程/身份模型。",
        "blockers": ["进程/身份模型未定", "并发/安装隔离的 D600 证据缺失"],
        "falsifiers": ["log 中的 pid/tid 无法对应到真实进程", "并发安装导致 generation 泄漏"],
    },
}


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


def clean_blockquote(text):
    """Collapse blockquote lines into a single paragraph."""
    return " ".join(line.lstrip(">").strip() for line in text.splitlines() if line.strip())


def is_spec_gap(text):
    return not text or text.upper().startswith("SPEC_GAP")


def extract_in_plain_words(fn, fallback_summary=""):
    """Extract the first human-friendly paragraph from CONCEPT_DOMAIN.md.

    Different Concepts use different freshman-friendly markers; we try the
    common ones and fall back to the summary from CONCEPT_DETAILS if the file
    has not been humanized yet.
    """
    path = IMPROVED_DIR / fn / "CONCEPT_DOMAIN.md"
    if not path.exists():
        return fallback_summary
    text = path.read_text(encoding="utf-8")

    patterns = [
        # Fn04 / Fn07 style: section header
        (r"#+\s*In plain words[:：]?\s*\n+([^#\n][^\n]*(?:\n[^#\n][^\n]*)*)", 1, False),
        # Fn01 style: covers + matters
        (r">\s*\*\*What this Concept covers:\*\*\s*([^\n]+)\n>\s*\n>\s*\*\*Why it matters:\*\*\s*([^\n]+)", 2, True),
        # Fn03 style
        (r">\s*用大白话说[:：]\s*([^\n]+(?:\n>[^\n]+)*)", 1, True),
        # Fn05 style
        (r">\s*\*\*Freshman-friendly overview:\*\*\s*([^\n]+(?:\n>[^\n]+)*)", 1, True),
        # Fn08 style
        (r">\s*\*\*Plain language\*\*[:：]?\s*([^\n]+(?:\n>[^\n]+)*)", 1, True),
        # Fn10 style
        (r">\s*\*\*freshman 导读\*\*[:：]?\s*([^\n]+(?:\n>[^\n]+)*)", 1, True),
        # Generic blockquote
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

    # Last fallback: first substantial blockquote after title
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
    return joined if not is_spec_gap(joined) else fallback_summary


def extract_route_options(fn):
    """Try to extract a simple list of route hypotheses from CONCEPT_DESIGN.md."""
    path = IMPROVED_DIR / fn / "CONCEPT_DESIGN.md"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    options = []
    # Match | H1 ... | description | support | opposition | missing | in verdict tables
    # Allow bold or plain H1/H1: prefix
    for m in re.finditer(
        r"\|\s*\*?\*?(H\d+)[:：]?\s*\*?\*?[^|]*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|",
        text,
    ):
        hid, desc, support, oppose, missing = m.groups()
        options.append({
            "id": hid.strip(),
            "description": desc.strip(),
            "support": support.strip(),
            "opposition": oppose.strip(),
            "missing": missing.strip(),
        })
    return options


def build_data():
    graph = load_graph()
    concepts = {}
    for fn in ALL_FN:
        details = CONCEPT_DETAILS.get(fn, {})
        concepts[fn] = {
            "status": concept_status(graph, fn),
            "title": details.get("title", ""),
            "summary": details.get("summary", ""),
            "role": details.get("role_in_groups", ""),
            "leading_hypothesis": details.get("leading_hypothesis", ""),
            "evidence": details.get("evidence", ""),
            "blockers": details.get("blockers", []),
            "falsifiers": details.get("falsifiers", []),
            "in_plain_words": extract_in_plain_words(fn, details.get("summary", "")),
            "route_options": extract_route_options(fn),
        }
    return concepts


def render_html(concepts):
    concepts_json = json.dumps(concepts, ensure_ascii=False)
    choices_json = json.dumps(CHOICES, ensure_ascii=False)
    choice_details_json = json.dumps(CHOICE_DETAILS, ensure_ascii=False)
    groups_json = json.dumps(GROUPS, ensure_ascii=False)
    generated_at = datetime.now().isoformat()

    rows = []
    for fn in ALL_FN:
        c = concepts[fn]
        status_class = c["status"].lower()
        rows.append(f"""
        <tr>
          <th scope="row">
            <button class="layer-toggle" type="button" onclick="openConcept('{fn}')">
              <span class="layer-id">{fn}</span>
              <span class="layer-name">{c['title']}</span>
            </button>
          </th>
          <td><button class="cell-button" onclick="openConcept('{fn}')"><span class="state-token {status_class}">{c['status'][:1]}</span><span class="cell-label">{c['status']}</span></button></td>
          <td><button class="cell-button" onclick="openConcept('{fn}')"><span class="current-choice" id="choice-display-{fn}">—</span></button></td>
          <td><button class="cell-button" onclick="openConcept('{fn}')"><span class="hypothesis-short">{escape_html(c['leading_hypothesis'][:50])}{'…' if len(c['leading_hypothesis']) > 50 else ''}</span></button></td>
          <td><button class="cell-button" onclick="openConcept('{fn}')"><span class="evidence-short">{escape_html(c['evidence'][:60])}{'…' if len(c['evidence']) > 60 else ''}</span></button></td>
          <td><button class="cell-button" onclick="openConcept('{fn}')"><span class="blocker-count">{len(c['blockers'])} 阻塞 / {len(c['falsifiers'])} 待证伪</span></button></td>
        </tr>
        """)
    tbody = "\n".join(rows)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bridge Strategy Decision Board</title>
<style>
  :root {{
    color-scheme: dark;
    --bg: #0b1017;
    --panel: #111923;
    --panel-2: #172230;
    --panel-3: #1d2a39;
    --line: #2a394a;
    --line-strong: #405269;
    --text: #edf3f8;
    --muted: #91a0b2;
    --muted-2: #66768a;
    --cyan: #72d2e6;
    --cyan-soft: rgba(114, 210, 230, .12);
    --red: #ff7373;
    --red-soft: rgba(255, 93, 93, .16);
    --orange: #ffae57;
    --orange-soft: rgba(255, 162, 61, .16);
    --yellow: #e8d463;
    --yellow-soft: rgba(232, 212, 99, .16);
    --green: #64d38b;
    --green-soft: rgba(68, 204, 116, .16);
    --blue: #77a8ff;
    --blue-soft: rgba(87, 142, 245, .15);
    --purple: #c394ff;
    --purple-soft: rgba(167, 104, 255, .15);
    --shadow: 0 18px 50px rgba(0, 0, 0, .24);
  }}
  * {{ box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; }}
  body {{
    margin: 0;
    min-width: 320px;
    background:
      radial-gradient(circle at 12% 0%, rgba(47, 113, 140, .18), transparent 34rem),
      radial-gradient(circle at 90% 8%, rgba(75, 67, 143, .12), transparent 30rem),
      var(--bg);
    color: var(--text);
    font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    line-height: 1.5;
  }}
  button, dialog {{ font: inherit; }}
  button {{ color: inherit; }}
  .page {{
    width: min(100%, 1600px);
    margin: 0 auto;
    padding: 28px 28px 44px;
  }}
  .hero {{
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 18px;
    align-items: start;
    margin-bottom: 18px;
  }}
  .eyebrow {{
    display: flex;
    gap: 8px;
    align-items: center;
    margin-bottom: 10px;
    color: var(--cyan);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: .12em;
    text-transform: uppercase;
  }}
  .eyebrow::before {{
    width: 24px;
    height: 1px;
    content: "";
    background: currentColor;
  }}
  h1 {{ margin: 0; max-width: 880px; font-size: clamp(28px, 4vw, 42px); line-height: 1.1; letter-spacing: -.04em; }}
  .subtitle {{ max-width: 940px; margin: 13px 0 0; color: var(--muted); font-size: 14px; overflow-wrap: anywhere; }}
  .notice {{
    display: flex;
    align-items: flex-start;
    gap: 11px;
    margin-bottom: 18px;
    padding: 12px 14px;
    border: 1px solid rgba(114, 210, 230, .25);
    border-radius: 10px;
    background: rgba(114, 210, 230, .07);
    color: #b9ccd8;
    font-size: 13px;
  }}
  .notice strong {{ color: var(--text); }}
  .notice-mark {{
    display: grid;
    width: 20px;
    height: 20px;
    flex: 0 0 auto;
    place-items: center;
    border-radius: 50%;
    background: var(--cyan-soft);
    color: var(--cyan);
    font-weight: 800;
  }}
  .board-toolbar {{
    display: flex;
    gap: 10px;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
    flex-wrap: wrap;
  }}
  .stats {{
    display: flex;
    flex: 0 0 auto;
    flex-wrap: nowrap;
    gap: 6px;
    align-items: center;
    margin-left: auto;
  }}
  .stat {{
    display: inline-flex;
    min-height: 30px;
    align-items: center;
    gap: 7px;
    padding: 5px 8px;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: rgba(17, 25, 35, .72);
    color: var(--muted);
    font-size: 11px;
  }}
  .stat strong {{ color: var(--text); font-size: 12px; }}
  .board-shell {{
    position: relative;
    border: 1px solid var(--line);
    border-radius: 14px;
    background: var(--panel);
    box-shadow: var(--shadow);
    overflow: hidden;
  }}
  .table-scroll {{
    max-width: 100%;
    overflow: auto;
    overscroll-behavior-inline: contain;
    scrollbar-color: var(--line-strong) var(--panel);
  }}
  table {{
    width: max-content;
    min-width: 100%;
    border-spacing: 0;
    border-collapse: separate;
    table-layout: fixed;
  }}
  th, td {{
    padding: 0;
    border-right: 1px solid var(--line);
    border-bottom: 1px solid var(--line);
  }}
  tr > :last-child {{ border-right: 0; }}
  tbody tr:last-child > * {{ border-bottom: 0; }}
  thead th {{
    position: sticky;
    top: 0;
    z-index: 5;
    background: #182432;
    color: #b7c4d2;
    text-align: center;
    height: 48px;
    font-size: 12px;
    font-weight: 700;
  }}
  tbody th {{
    position: sticky;
    left: 0;
    z-index: 4;
    width: 260px;
    min-width: 260px;
    background: #15212e;
    box-shadow: 1px 0 0 var(--line-strong);
    color: var(--text);
    font-family: "SFMono-Regular", Consolas, monospace;
    font-size: 14px;
    font-weight: 800;
    letter-spacing: .06em;
    text-align: left;
  }}
  .layer-toggle {{
    display: flex;
    width: 100%;
    min-height: 56px;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border: 0;
    background: transparent;
    cursor: pointer;
    color: var(--text);
    text-align: left;
  }}
  .layer-toggle:hover {{ background: var(--cyan-soft); }}
  .layer-toggle .layer-id {{ min-width: 40px; font-size: 16px; font-weight: 800; color: var(--cyan); }}
  .layer-toggle .layer-name {{ min-width: 0; overflow: hidden; color: #b8c5d2; font-family: Inter, ui-sans-serif, sans-serif; font-size: 13px; font-weight: 650; text-overflow: ellipsis; white-space: nowrap; }}
  .matrix-cell {{
    width: 180px;
    min-width: 180px;
    height: 56px;
    background: #101821;
  }}
  .cell-button {{
    display: flex;
    width: 100%;
    height: 100%;
    min-height: 56px;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 3px;
    padding: 8px;
    border: 0;
    border-radius: 0;
    background: transparent;
    cursor: pointer;
    text-align: center;
    transition: background .15s ease;
  }}
  .cell-button:hover {{ background: rgba(114, 210, 230, .08); box-shadow: inset 0 0 0 1px rgba(114, 210, 230, .46); }}
  .cell-button:focus-visible {{ outline: 2px solid var(--cyan); outline-offset: -3px; }}
  .state-token {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 22px;
    height: 22px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
  }}
  .state-token.evidenced {{ background: var(--green-soft); color: var(--green); }}
  .state-token.partial {{ background: var(--yellow-soft); color: var(--yellow); }}
  .state-token.blocked {{ background: var(--red-soft); color: var(--red); }}
  .state-token.unassessed {{ background: rgba(100,116,139,.2); color: var(--muted-2); }}
  .cell-label {{ font-size: 11px; color: var(--muted); }}
  .current-choice {{ font-size: 13px; font-weight: 700; color: var(--cyan); }}
  .hypothesis-short, .evidence-short, .blocker-count {{ font-size: 11px; color: var(--muted); }}
  dialog {{
    width: min(760px, calc(100% - 28px));
    max-height: min(90vh, 900px);
    padding: 0;
    border: 1px solid var(--line-strong);
    border-radius: 14px;
    background: var(--panel);
    color: var(--text);
    box-shadow: 0 28px 90px rgba(0, 0, 0, .56);
    overflow: hidden;
  }}
  dialog::backdrop {{ background: rgba(2, 6, 10, .76); backdrop-filter: blur(5px); }}
  .dialog-head {{
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    padding: 18px 20px 15px;
    border-bottom: 1px solid var(--line);
    background: #172331;
  }}
  .dialog-kicker {{ margin-bottom: 3px; color: var(--cyan); font-family: "SFMono-Regular", Consolas, monospace; font-size: 11px; font-weight: 800; letter-spacing: .08em; }}
  .dialog-head h2 {{ margin: 0; font-size: 21px; letter-spacing: -.02em; }}
  .dialog-close {{
    display: grid;
    width: 34px;
    height: 34px;
    flex: 0 0 auto;
    place-items: center;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--panel-2);
    cursor: pointer;
    font-size: 18px;
  }}
  .dialog-close:hover {{ border-color: var(--cyan); color: var(--cyan); }}
  .dialog-body {{
    max-height: calc(90vh - 72px);
    padding: 18px 20px 22px;
    overflow-y: auto;
  }}
  .detail-section {{ margin-bottom: 18px; }}
  .detail-section h3 {{
    margin: 0 0 9px;
    color: var(--muted);
    font-size: 11px;
    letter-spacing: .08em;
    text-transform: uppercase;
  }}
  .detail-section p {{ margin: .35rem 0; color: #e2e8f0; font-size: 13px; }}
  .detail-section ul {{ margin: .35rem 0; padding-left: 1.2rem; color: #e2e8f0; font-size: 13px; }}
  .detail-section li {{ margin-bottom: .4rem; }}
  .plain-words {{
    padding: 11px 12px;
    border-left: 3px solid var(--cyan);
    border-radius: 0 8px 8px 0;
    background: var(--cyan-soft);
    color: #c8e6ed;
    font-size: 13px;
  }}
  .choice-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 10px;
  }}
  .choice-btn {{
    background: var(--panel-2);
    border: 2px solid transparent;
    color: var(--text);
    padding: 12px;
    border-radius: 8px;
    cursor: pointer;
    text-align: left;
    transition: all .15s;
  }}
  .choice-btn:hover {{ border-color: var(--cyan); }}
  .choice-btn.selected {{ border-color: var(--cyan); background: var(--cyan-soft); }}
  .choice-btn strong {{ display: block; font-size: 13px; margin-bottom: 4px; }}
  .choice-btn span {{ display: block; font-size: 11px; color: var(--muted); }}
  .history-list {{ display: grid; gap: 8px; }}
  .history-item {{
    background: var(--panel-2);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 10px 12px;
  }}
  .history-empty {{ color: var(--muted); font-style: italic; font-size: 13px; }}
  .route-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    background: var(--panel-2);
    border-radius: 8px;
    overflow: hidden;
  }}
  .route-table th, .route-table td {{ padding: 8px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
  .route-table th {{ background: var(--panel-3); color: var(--muted); }}
  .toolbar {{
    display: flex;
    gap: 8px;
    margin-top: 12px;
    flex-wrap: wrap;
  }}
  .toolbar button {{
    background: var(--panel-2);
    border: 1px solid var(--line);
    color: var(--text);
    padding: 8px 12px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
  }}
  .toolbar button:hover {{ border-color: var(--cyan); }}
  .toolbar button.primary {{ background: var(--cyan); color: #0b1017; border-color: var(--cyan); font-weight: 700; }}
  .save-feedback {{ margin-top: 8px; font-size: 13px; min-height: 20px; }}
  .save-feedback.ok {{ color: var(--green); }}
  .save-feedback.err {{ color: var(--red); }}
  textarea {{
    width: 100%;
    background: var(--bg);
    border: 1px solid var(--line);
    color: var(--text);
    padding: 10px;
    border-radius: 8px;
    font-family: inherit;
    font-size: 13px;
    resize: vertical;
  }}
  .footnote {{
    margin: 18px 0 0;
    color: var(--muted-2);
    font-size: 11px;
  }}
  @media (max-width: 900px) {{
    .hero {{ grid-template-columns: 1fr; }}
    .matrix-cell {{ width: 140px; min-width: 140px; }}
    .layer-toggle .layer-name {{ max-width: 140px; }}
  }}
</style>
</head>
<body>
<main class="page">
  <section class="hero" aria-labelledby="pageTitle">
    <div>
      <div class="eyebrow">Strategy Decision Board</div>
      <h1 id="pageTitle">Bridge 技术路线决策看板</h1>
      <p class="subtitle">
        参考 <code>L_APP_MATURITY_BOARD.html</code> 布局，按 Concept Domain（Fn01–Fn12）统一进行 strategy review。
        点击任意 Concept 单元格即可查看人类亲和的决策信息、修订选择并记录历史。
      </p>
    </div>
  </section>

  <section class="notice" aria-label="使用说明">
    <span class="notice-mark" aria-hidden="true">i</span>
    <span>
      <strong>决策单位是 Concept，不是单个 Action。</strong>
      相关 Concept 已在 Group A/B/C 中组织；请在查看证据状态、阻塞项和待证伪项后，再选择主导/备选/继续实验等选项。
      所有选择会保存到浏览器 localStorage，可导出为 Markdown/YAML/JSON。
    </span>
  </section>

  <section aria-label="决策矩阵">
    <div class="board-toolbar">
      <div class="stats">
        <span class="stat">Concept <strong id="conceptCount">12</strong></span>
        <span class="stat">已选择 <strong id="chosenCount">0</strong></span>
        <span class="stat">待决策 <strong id="pendingCount">12</strong></span>
      </div>
      <div class="toolbar">
        <button onclick="exportRecords('json')">导出 JSON</button>
        <button onclick="exportRecords('yaml')">导出 YAML</button>
        <button onclick="generateReport()">生成报告</button>
        <button onclick="clearAllRecords()" style="color:var(--red)">清空记录</button>
      </div>
    </div>

    <div class="board-shell">
      <div class="table-scroll" id="tableScroll" aria-label="Fnxx 技术路线决策矩阵">
        <table>
          <caption style="position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0;">Fn01 至 Fn12 技术路线决策矩阵</caption>
          <thead>
            <tr>
              <th class="corner" scope="col">Fn × DECISION</th>
              <th scope="col">当前状态</th>
              <th scope="col">当前选择</th>
              <th scope="col">主导假设</th>
              <th scope="col">关键证据</th>
              <th scope="col">阻塞 / 证伪</th>
            </tr>
          </thead>
          <tbody>
            {tbody}
          </tbody>
        </table>
      </div>
    </div>
  </section>

  <p class="footnote">
    生成时间：{generated_at} · 数据来源：docs/spec/concept-graph.yaml、docs/decisions/fnxx-strategies/improved-sources/、src/tools/build-strategy-decision-board.py。
    选择记录保存在浏览器 localStorage（key: bridge-strategy-decisions）。
  </p>
</main>

<dialog id="conceptDialog" aria-labelledby="dialogTitle">
  <div class="dialog-head">
    <div>
      <div class="dialog-kicker" id="dialogKicker"></div>
      <h2 id="dialogTitle"></h2>
    </div>
    <button class="dialog-close" id="dialogClose" type="button" aria-label="关闭">×</button>
  </div>
  <div class="dialog-body" id="dialogBody"></div>
</dialog>

<script>
(() => {{
  "use strict";

  const CONCEPTS = {concepts_json};
  const CHOICES = {choices_json};
  const CHOICE_DETAILS = {choice_details_json};
  const GROUPS = {groups_json};
  const STORAGE_KEY = "bridge-strategy-decisions";

  const dialog = document.getElementById("conceptDialog");
  const dialogKicker = document.getElementById("dialogKicker");
  const dialogTitle = document.getElementById("dialogTitle");
  const dialogBody = document.getElementById("dialogBody");
  let currentFn = null;
  let currentSelectedChoice = null;

  function escapeHtml(text) {{
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }}

  function loadStoredRecords() {{
    try {{ return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"); }}
    catch (e) {{ return []; }}
  }}

  function saveRecords(records) {{
    localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
  }}

  function getLatestChoice(fn) {{
    const records = loadStoredRecords().filter(r => r.target === fn);
    return records.length ? records[records.length - 1].choice_key : null;
  }}

  function updateSummary() {{
    const records = loadStoredRecords();
    const latest = {{}};
    records.forEach(r => {{ latest[r.target] = r.choice_key; }});
    let chosen = 0;
    Object.keys(CONCEPTS).forEach(fn => {{
      const el = document.getElementById("choice-display-" + fn);
      const key = latest[fn];
      if (el) el.textContent = key ? CHOICES[key].split(" / ")[0] : "—";
      if (key && key !== "s") chosen++;
    }});
    document.getElementById("chosenCount").textContent = chosen;
    document.getElementById("pendingCount").textContent = Object.keys(CONCEPTS).length - chosen;
  }}

  function groupMembership(fn) {{
    const list = [];
    Object.entries(GROUPS).forEach(([gid, g]) => {{
      if (g.concepts.includes(fn)) list.push(gid);
    }});
    return list;
  }}

  function renderRouteOptions(fn, c) {{
    const opts = c.route_options || [];
    if (!opts.length) {{
      return `<p class="history-empty">暂无结构化路线选项；主导假设见下方。</p>`;
    }}
    const rows = opts.map(o => `
      <tr>
        <td><strong>${{escapeHtml(o.id)}}</strong></td>
        <td>${{escapeHtml(o.description)}}</td>
        <td>${{escapeHtml(o.support)}}</td>
        <td>${{escapeHtml(o.missing)}}</td>
      </tr>
    `).join("");
    return `
      <table class="route-table">
        <thead><tr><th>路线</th><th>描述</th><th>当前支持</th><th>缺失证据</th></tr></thead>
        <tbody>${{rows}}</tbody>
      </table>
    `;
  }}

  function renderHistory(fn) {{
    const records = loadStoredRecords().filter(r => r.target === fn);
    if (!records.length) return `<p class="history-empty">暂无历史选择。</p>`;
    return `
      <div class="history-list">
        ${{records.slice().reverse().map((r, i) => `
          <div class="history-item">
            <div style="display:flex;justify-content:space-between;gap:8px;">
              <strong style="color:var(--cyan)">${{CHOICES[r.choice_key].split(" / ")[0]}}</strong>
              <span style="color:var(--muted);font-size:11px">${{new Date(r.timestamp).toLocaleString()}}</span>
            </div>
            <div style="color:var(--muted);font-size:12px;margin-top:4px">负责人: ${{escapeHtml(r.owner || "—")}}</div>
            <p style="margin:6px 0 0;font-size:12px">${{escapeHtml(r.reason || "")}}</p>
          </div>
        `).join("")}}
      </div>
    `;
  }}

  function openConcept(fn) {{
    currentFn = fn;
    const c = CONCEPTS[fn];
    const groups = groupMembership(fn);
    dialogKicker.textContent = `${{fn}} · ${{groups.map(g => "Group " + g).join(", ") || "未分组"}}`;
    dialogTitle.textContent = `${{fn}} — ${{c.title}}`;
    currentSelectedChoice = getLatestChoice(fn);

    const choiceButtons = Object.entries(CHOICES).map(([k, label]) => {{
      const d = CHOICE_DETAILS[k];
      const selected = currentSelectedChoice === k ? "selected" : "";
      return `
        <button class="choice-btn ${{selected}}" data-choice="${{k}}" onclick="window.__selectChoice('${{k}}')">
          <strong>${{label.split(" / ")[0]}}</strong>
          <span>${{d.hint}}</span>
          <span style="color:var(--red);margin-top:2px">风险：${{d.risk}}</span>
        </button>
      `;
    }}).join("");

    dialogBody.innerHTML = `
      <div class="detail-section">
        <h3>给人类看的摘要</h3>
        <div class="plain-words">${{escapeHtml(c.in_plain_words || c.summary)}}</div>
      </div>

      <div class="detail-section two-col" style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
        <div>
          <h3>当前状态</h3>
          <p><span class="state-token ${{c.status.toLowerCase()}}">${{c.status}}</span></p>
          <p><strong>在统一分组中的角色：</strong>${{escapeHtml(c.role)}}</p>
        </div>
        <div>
          <h3>主导假设</h3>
          <p>${{escapeHtml(c.leading_hypothesis)}}</p>
        </div>
      </div>

      <div class="detail-section">
        <h3>关键证据</h3>
        <p>${{escapeHtml(c.evidence)}}</p>
      </div>

      <div class="detail-section" style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
        <div>
          <h3>阻塞项</h3>
          <ul>${{(c.blockers || []).map(b => `<li>${{escapeHtml(b)}}</li>`).join("") || "<li>暂无</li>"}}</ul>
        </div>
        <div>
          <h3>待证伪项</h3>
          <ul>${{(c.falsifiers || []).map(f => `<li>${{escapeHtml(f)}}</li>`).join("") || "<li>暂无</li>"}}</ul>
        </div>
      </div>

      <div class="detail-section">
        <h3>候选路线</h3>
        ${{renderRouteOptions(fn, c)}}
      </div>

      <div class="detail-section">
        <h3>选择操作</h3>
        <div class="choice-grid">${{choiceButtons}}</div>
        <div style="margin-top:12px;">
          <label style="display:block;margin-bottom:6px;color:var(--muted);font-size:12px;">决策理由 / 备注</label>
          <textarea id="decision-reason" rows="3" placeholder="必须填写理由..."></textarea>
        </div>
        <div style="margin-top:8px;">
          <label style="display:block;margin-bottom:6px;color:var(--muted);font-size:12px;">负责人</label>
          <input type="text" id="decision-owner" value="human-required" style="width:100%;background:var(--bg);border:1px solid var(--line);color:var(--text);padding:8px;border-radius:6px;">
        </div>
        <div class="toolbar">
          <button class="primary" onclick="window.__saveDecision()">保存 ${{fn}} 决策</button>
          <button onclick="window.__openFullPage('${{fn}}')">查看完整 Strategy 页面</button>
          <button onclick="window.__openSources('${{fn}}')">查看改进源文档</button>
        </div>
        <div class="save-feedback" id="decision-feedback"></div>
      </div>

      <div class="detail-section">
        <h3>历史选择</h3>
        ${{renderHistory(fn)}}
      </div>
    `;

    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
  }}

  window.__selectChoice = function(key) {{
    currentSelectedChoice = key;
    dialogBody.querySelectorAll(".choice-btn").forEach(btn => btn.classList.remove("selected"));
    const btn = dialogBody.querySelector(`[data-choice="${{key}}"]`);
    if (btn) btn.classList.add("selected");
  }};

  window.__saveDecision = function() {{
    const feedback = document.getElementById("decision-feedback");
    if (!currentSelectedChoice) {{
      feedback.textContent = "请先选择一个选项。";
      feedback.className = "save-feedback err";
      return;
    }}
    const reason = document.getElementById("decision-reason").value.trim();
    if (!reason) {{
      feedback.textContent = "请填写决策理由。";
      feedback.className = "save-feedback err";
      return;
    }}
    const owner = document.getElementById("decision-owner").value.trim() || "human-required";
    const records = loadStoredRecords();
    records.push({{
      timestamp: new Date().toISOString(),
      target: currentFn,
      choice_key: currentSelectedChoice,
      choice: CHOICES[currentSelectedChoice],
      owner: owner,
      reason: reason,
    }});
    saveRecords(records);
    feedback.textContent = `已保存 ${{currentFn}} 的选择：${{CHOICES[currentSelectedChoice].split(" / ")[0]}}`;
    feedback.className = "save-feedback ok";
    updateSummary();
    // refresh history
    const histSection = dialogBody.querySelector(".detail-section:last-child");
    if (histSection) histSection.innerHTML = `<h3>历史选择</h3>${{renderHistory(currentFn)}}`;
  }};

  window.__openFullPage = function(fn) {{
    window.open(`fnxx-strategies/${{fn}}.html`, "_blank");
  }};

  window.__openSources = function(fn) {{
    window.open(`fnxx-strategies/improved-sources/${{fn}}/`, "_blank");
  }};

  function closeDialog() {{
    if (typeof dialog.close === "function") dialog.close();
    else dialog.removeAttribute("open");
  }}

  document.getElementById("dialogClose").addEventListener("click", closeDialog);
  dialog.addEventListener("click", event => {{
    if (event.target === dialog) {{
      const rect = dialog.getBoundingClientRect();
      const inside = event.clientX >= rect.left && event.clientX <= rect.right && event.clientY >= rect.top && event.clientY <= rect.bottom;
      if (!inside) closeDialog();
    }}
  }});

  window.exportRecords = function(format) {{
    const records = loadStoredRecords();
    let content, mime, ext;
    if (format === "json") {{
      content = JSON.stringify(records, null, 2);
      mime = "application/json";
      ext = "json";
    }} else {{
      content = records.map(r => `
timestamp: '${{r.timestamp}}'
target: ${{r.target}}
choice: ${{r.choice}}
choice_key: ${{r.choice_key}}
owner: ${{r.owner}}
reason: |
  ${{r.reason.replace(/\\n/g, "\\n  ")}}
      `.trim()).join("\\n---\\n");
      mime = "text/yaml";
      ext = "yaml";
    }}
    const blob = new Blob([content], {{ type: mime }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `bridge-strategy-decisions-${{new Date().toISOString().slice(0,10)}}.${{ext}}`;
    a.click();
    URL.revokeObjectURL(url);
  }};

  window.generateReport = function() {{
    const records = loadStoredRecords();
    const latest = {{}};
    records.forEach(r => {{ latest[r.target] = r; }});
    const lines = [
      "# Bridge Strategy Decision Report",
      "",
      `生成时间: ${{new Date().toISOString()}}`,
      `记录数量: ${{records.length}}`,
      "",
      "## 分组决策状态",
      "",
    ];
    Object.entries(GROUPS).forEach(([gid, g]) => {{
      lines.push(`### Group ${{gid}}: ${{g.name}}`);
      lines.push(`- 核心对象: ${{g.core_object}}`);
      lines.push("- Concept 状态:");
      g.concepts.forEach(fn => {{
        const c = CONCEPTS[fn];
        const r = latest[fn];
        const choice = r ? r.choice.split(" / ")[0] : "未选择";
        lines.push(`  - ${{fn}} (${{c.status}}) → ${{choice}}`);
      }});
      lines.push("");
    }});
    lines.push("## 全部记录", "");
    if (!records.length) lines.push("(无记录)");
    Object.keys(CONCEPTS).forEach(fn => {{
      const rs = records.filter(r => r.target === fn).reverse();
      if (!rs.length) return;
      lines.push(`### ${{fn}}`);
      rs.forEach(r => lines.push(`- ${{new Date(r.timestamp).toLocaleString()}} · ${{r.choice.split(" / ")[0]}} · ${{r.owner}}\\n  - ${{r.reason.replace(/\\n/g, "\\n    ")}}`));
      lines.push("");
    }});
    const blob = new Blob([lines.join("\\n")], {{ type: "text/markdown" }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `strategy-decision-report-${{new Date().toISOString().slice(0,10)}}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }};

  window.clearAllRecords = function() {{
    if (!confirm("确定清空全部决策记录？此操作不可恢复。")) return;
    localStorage.removeItem(STORAGE_KEY);
    updateSummary();
  }};

  window.openConcept = openConcept;
  updateSummary();
}})();
</script>
</body>
</html>
"""


def escape_html(s):
    return (s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def main():
    concepts = build_data()
    html = render_html(concepts)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"Generated: {OUTPUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
