#!/usr/bin/env python3
"""
Build a self-contained HTML strategy review console.

Reads docs/spec/concept-graph.yaml and docs/concepts/Fnxx/ to generate
 docs/decisions/strategy-review-console.html.

Run:
    python3 src/tools/build-strategy-review-html.py
"""

import json
import re
import yaml
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC_FILE = ROOT / "spec" / "concept-graph.yaml"
CONCEPTS_DIR = ROOT / "docs" / "concepts"
OUTPUT_FILE = ROOT / "docs" / "decisions" / "strategy-review-console.html"

ALL_FN = [f"Fn{n:02d}" for n in range(1, 13)]

GROUPS = {
    "A": {
        "name": "可见表面组 / Window · Input · Graphics",
        "concepts": ["Fn03", "Fn04", "Fn05", "Fn10"],
        "core_object": "generation-bound window/session/surface and callback thread",
        "questions": [
            "窗口生成单元是什么：Ability session、WindowRecord 还是 SceneBoard node？",
            "InputChannel 如何绑定到 window generation 和 owner Looper？",
            "HWUI/Skia buffer 和 RS transaction 在哪里终止，什么 receipt 证明帧已上屏？",
            "Activity attach/resume/finish 如何创建和失效 window generation？",
        ],
    },
    "B": {
        "name": "组件调度组 / Intent · Task · Service",
        "concepts": ["Fn01", "Fn03", "Fn06", "Fn07", "Fn08", "Fn11"],
        "core_object": "typed Intent/Want, task/service authority, caller identity and Binder endpoint",
        "questions": [
            "同一个 AXML 解析器和 BMS projection 是否同时输出 PAGE Activity 和 SERVICE extension 元数据？",
            "Service host 是什么：ServiceExtensionAbility、共享 runtime agent 还是 ServiceLifecycleAuthority？",
            "ActivityThread 调度模型如何同时覆盖 Activity 和 Service 生命周期回调？",
            "caller token 格式是什么，如何在 startService/bindService/Binder 事务中保持？",
            "Android Binder 是本地保留、OH remote proxy 还是二者兼有？",
        ],
    },
    "C": {
        "name": "身份授权基板 / Package · Permission · Binder",
        "concepts": ["Fn01", "Fn08", "Fn11"],
        "core_object": "package/signing identity, AccessToken/sandbox generation, caller token and verdict",
        "questions": [
            "包解析如何输出 signing、declared permissions 和 install generation？",
            "spawn 与受保护 API 边界的 caller identity 如何与 OH AccessToken 关联？",
            "权限撤销后旧 generation 的访问是否立即失效？",
            "Binder/system-service lookup 的 caller token 由谁生成和校验？",
        ],
    },
}

CHOICES = {
    "e": "继续做实验 / Evidence building",
    "h": "历史成功实践优先 / Historical precedent",
    "m": "维持历史决策 / Maintain historical decision",
    "p": "选择主导建议 / Select primary recommendation",
    "b": "选择备选路线 / Select backup route",
    "r": "看参考文档 / View reference documents",
    "s": "跳过，保持当前状态 / Skip",
}

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
        "summary": "负责 appspawn-x  fork 进程、加载 Android Runtime（ART）、JNI/native 库的运行时环境。",
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

LINKABLE_FILES = {
    "ACTION_MAP.md", "BRIDGE_CONTRACT.md", "CONCEPT_DESIGN.md", "CONCEPT_DOMAIN.md",
    "ROUTE_SPACE.md", "STRATEGY.md", "STRATEGY_DECISION.md", "ANDROID_MODEL.md",
    "OPENHARMONY_MODEL.md", "CASE_LEDGER.md", "PATTERN_CATALOG.md", "RESEARCH_QUESTIONS.md",
    "REVIEW_LOG.md", "CONTEXT_MAP.md", "SUBCONCEPT_MAP.md", "D600_TEST_PLAN.md",
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


def concept_files(fn):
    d = CONCEPTS_DIR / fn
    if not d.exists():
        return []
    return sorted(p.name for p in d.iterdir() if p.name in LINKABLE_FILES)


def escape_js_string(s):
    return (s.replace("\\", "\\\\")
            .replace("'", "\\'")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r"))


def build_data():
    graph = load_graph()
    concepts = {}
    for fn in ALL_FN:
        concepts[fn] = {
            "status": concept_status(graph, fn),
            "files": concept_files(fn),
            "details": CONCEPT_DETAILS.get(fn, {}),
        }
    return concepts


def render_html(concepts):
    concepts_json = json.dumps(concepts, ensure_ascii=False)
    choices_json = json.dumps(CHOICES, ensure_ascii=False)
    groups_json = json.dumps(GROUPS, ensure_ascii=False)
    details_json = json.dumps(CONCEPT_DETAILS, ensure_ascii=False)
    generated_at = datetime.now().isoformat()

    concept_rows = "\n".join(
        f"<tr><td><strong>{fn}</strong></td><td><span class='status {concepts[fn]['status'].lower()}'>{concepts[fn]['status']}</span></td><td>{', '.join(concepts[fn]['files']) or '(none)'}</td></tr>"
        for fn in ALL_FN
    )

    def concept_decision_card(fn, instance_prefix="all"):
        instance_id = f"{instance_prefix}-{fn}"
        status = concepts[fn]['status']
        files = concepts[fn]['files']
        d = CONCEPT_DETAILS.get(fn, {})
        file_links = " · ".join(
            f"<a href='../concepts/{fn}/{f}' target='_blank'>{f}</a>" for f in files
        ) or "no docs"
        choice_buttons = "\n".join(
            f"<button class='choice-btn' data-choice='{k}' onclick=\"selectChoice('{instance_id}', '{k}')\">{k}<span>{v}</span></button>"
            for k, v in CHOICES.items()
        )

        def list_items(items):
            if not items:
                return "<p class='detail-empty'>暂无</p>"
            return "\n".join(f"<li>{x}</li>" for x in items)

        title = d.get("title", "")
        summary = d.get("summary", "")
        role = d.get("role_in_groups", "")
        hypothesis = d.get("leading_hypothesis", "")
        evidence = d.get("evidence", "")
        blockers = d.get("blockers", [])
        falsifiers = d.get("falsifiers", [])

        return f"""
        <div class="decision-box" id="decision-box-{instance_id}">
          <div class="decision-header">
            <div>
              <span class="concept-id">{fn}{' — ' + title if title else ''}</span>
              <span class="status {status.lower()}">{status}</span>
            </div>
            <a class="detail-link" href="fnxx-strategies/{fn}.html" target="_blank">查看完整 Strategy 页面 →</a>
          </div>

          <div class="concept-detail-section">
            <h4>职责</h4>
            <p>{summary or '(no summary)'}</p>
            {'<p class="detail-role"><strong>在统一分组中的角色：</strong>' + role + '</p>' if role else ''}
          </div>

          <div class="concept-detail-section">
            <h4>当前主导假设</h4>
            <p>{hypothesis or '(no hypothesis yet)'}</p>
          </div>

          <div class="concept-detail-section">
            <h4>证据状态</h4>
            <p>{evidence or '(no evidence summary)'}</p>
          </div>

          <div class="concept-detail-section two-col">
            <div>
              <h4>阻塞项</h4>
              <ul>{list_items(blockers)}</ul>
            </div>
            <div>
              <h4>待证伪项</h4>
              <ul>{list_items(falsifiers)}</ul>
            </div>
          </div>

          <div class="concept-detail-section">
            <h4>参考文档</h4>
            <div class="concept-files">{file_links}</div>
          </div>

          <div class="choice-grid">{choice_buttons}</div>
          <div class="form-row">
            <label>负责人</label>
            <input type="text" id="owner-{instance_id}" placeholder="human-required" value="human-required">
          </div>
          <div class="form-row">
            <label>理由 / 备注</label>
            <textarea id="reason-{instance_id}" rows="3" placeholder="必须填写理由..."></textarea>
          </div>
          <button class="primary" onclick="saveRecord('{instance_id}', '{fn}')">保存 {fn} 的 review 记录</button>
          <div class="save-feedback" id="feedback-{instance_id}"></div>
        </div>
        """

    group_sections = ""
    for gid, g in GROUPS.items():
        question_list = "\n".join(f"<li>{q}</li>" for q in g["questions"])
        concept_cards = "\n".join(concept_decision_card(fn, f"group-{gid}") for fn in g["concepts"])
        group_sections += f"""
        <section id="group-{gid}" class="group-section hidden">
          <h2>Group {gid}: {g['name']}</h2>
          <p class="core-object"><strong>核心共享对象：</strong>{g['core_object']}</p>
          <h3>关键问题（本组共同）</h3>
          <ol class="questions">{question_list}</ol>
          <h3>逐个 Concept 决策</h3>
          {concept_cards}
        </section>
        """

    all_concept_cards = "\n".join(concept_decision_card(fn) for fn in ALL_FN)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Bridge Strategy Review Console</title>
  <style>
    :root {{
      --bg: #0f172a;
      --surface: #1e293b;
      --surface-2: #334155;
      --text: #f8fafc;
      --text-dim: #94a3b8;
      --accent: #38bdf8;
      --accent-2: #818cf8;
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
      padding: 1.5rem 2rem;
      position: sticky;
      top: 0;
      z-index: 10;
    }}
    header h1 {{ margin: 0; font-size: 1.5rem; }}
    header p {{ margin: 0.25rem 0 0; color: var(--text-dim); font-size: 0.9rem; }}
    nav {{
      display: flex;
      gap: 0.5rem;
      padding: 1rem 2rem;
      background: var(--surface);
      border-bottom: 1px solid var(--surface-2);
      flex-wrap: wrap;
    }}
    nav button {{
      background: var(--surface-2);
      border: none;
      color: var(--text);
      padding: 0.6rem 1rem;
      border-radius: 0.4rem;
      cursor: pointer;
      font-size: 0.9rem;
      transition: background 0.15s;
    }}
    nav button:hover {{ background: #475569; }}
    nav button.active {{ background: var(--accent); color: #0f172a; font-weight: 600; }}
    main {{ padding: 2rem; max-width: 1200px; margin: 0 auto; }}
    .hidden {{ display: none !important; }}
    h2 {{ margin-top: 0; color: var(--accent); }}
    h3 {{ color: var(--text); border-bottom: 1px solid var(--surface-2); padding-bottom: 0.5rem; }}
    .core-object {{ color: var(--text-dim); font-size: 1.05rem; }}
    .concept-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 1rem;
      margin: 1.5rem 0;
    }}
    .concept-card {{
      background: var(--surface);
      border: 1px solid var(--surface-2);
      border-radius: 0.5rem;
      padding: 1rem;
    }}
    .concept-id {{ font-size: 1.1rem; font-weight: 700; margin-bottom: 0.25rem; }}
    .concept-files {{ font-size: 0.8rem; color: var(--text-dim); margin-top: 0.5rem; word-break: break-word; }}
    .decision-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; flex-wrap: wrap; gap: 0.5rem; }}
    .decision-header .concept-id {{ margin-bottom: 0; margin-right: 0.75rem; }}
    .decision-box a {{ color: var(--accent); text-decoration: none; }}
    .decision-box a:hover {{ text-decoration: underline; }}
    .detail-link {{
      display: inline-block;
      border: 1px solid var(--accent);
      padding: 0.35rem 0.7rem;
      border-radius: 0.4rem;
      font-size: 0.85rem;
      white-space: nowrap;
    }}
    .detail-link:hover {{ background: rgba(56, 189, 248, 0.1); }}
    .concept-detail-section {{ margin: 1rem 0; }}
    .concept-detail-section h4 {{
      margin: 0 0 0.4rem 0;
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--accent);
      border-bottom: none;
      padding-bottom: 0;
    }}
    .concept-detail-section p {{ margin: 0.25rem 0; color: #e2e8f0; }}
    .concept-detail-section ul {{ margin: 0.25rem 0; padding-left: 1.2rem; color: #e2e8f0; }}
    .concept-detail-section li {{ margin-bottom: 0.35rem; }}
    .detail-role {{ color: var(--text-dim); font-size: 0.9rem; margin-top: 0.5rem; }}
    .detail-empty {{ color: var(--text-dim); font-style: italic; }}
    .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }}
    @media (max-width: 700px) {{
      .two-col {{ grid-template-columns: 1fr; }}
    }}
    .status {{
      display: inline-block;
      padding: 0.2rem 0.6rem;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }}
    .status.evidenced {{ background: rgba(34, 197, 94, 0.2); color: var(--ok); }}
    .status.partial {{ background: rgba(234, 179, 8, 0.2); color: var(--warn); }}
    .status.blocked {{ background: rgba(239, 68, 68, 0.2); color: var(--danger); }}
    .status.unassessed {{ background: rgba(100, 116, 139, 0.2); color: var(--neutral); }}
    .questions {{ padding-left: 1.2rem; }}
    .questions li {{ margin-bottom: 0.5rem; color: #e2e8f0; }}
    .decision-box {{
      background: var(--surface);
      border: 1px solid var(--surface-2);
      border-radius: 0.5rem;
      padding: 1.5rem;
      margin-top: 2rem;
    }}
    .choice-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 0.75rem;
      margin-bottom: 1.5rem;
    }}
    .choice-btn {{
      background: var(--surface-2);
      border: 2px solid transparent;
      color: var(--text);
      padding: 0.75rem;
      border-radius: 0.4rem;
      cursor: pointer;
      text-align: left;
      transition: all 0.15s;
    }}
    .choice-btn:hover {{ border-color: var(--accent); }}
    .choice-btn.selected {{ border-color: var(--accent); background: rgba(56, 189, 248, 0.15); }}
    .choice-btn span {{
      display: block;
      font-size: 0.8rem;
      color: var(--text-dim);
      margin-top: 0.25rem;
    }}
    .form-row {{ margin-bottom: 1rem; }}
    .form-row label {{ display: block; margin-bottom: 0.3rem; font-weight: 600; }}
    input[type="text"], textarea {{
      width: 100%;
      background: var(--bg);
      border: 1px solid var(--surface-2);
      color: var(--text);
      padding: 0.6rem 0.8rem;
      border-radius: 0.4rem;
      font-family: inherit;
      font-size: 0.95rem;
    }}
    textarea {{ resize: vertical; }}
    button.primary {{
      background: var(--accent);
      color: #0f172a;
      border: none;
      padding: 0.75rem 1.5rem;
      border-radius: 0.4rem;
      font-weight: 600;
      cursor: pointer;
    }}
    button.primary:hover {{ background: #7dd3fc; }}
    .save-feedback {{
      margin-top: 0.75rem;
      font-size: 0.9rem;
      min-height: 1.4rem;
    }}
    .save-feedback.ok {{ color: var(--ok); }}
    .save-feedback.err {{ color: var(--danger); }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 1rem 0;
      background: var(--surface);
      border-radius: 0.5rem;
      overflow: hidden;
    }}
    th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid var(--surface-2); }}
    th {{ background: var(--surface-2); font-weight: 600; }}
    .record-card {{
      background: var(--surface);
      border: 1px solid var(--surface-2);
      border-radius: 0.5rem;
      padding: 1rem;
      margin-bottom: 1rem;
    }}
    .record-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.5rem;
    }}
    .record-time {{ color: var(--text-dim); font-size: 0.85rem; }}
    .record-choice {{ font-weight: 700; color: var(--accent); }}
    .record-meta {{ color: var(--text-dim); font-size: 0.9rem; }}
    .toolbar {{
      display: flex;
      gap: 0.75rem;
      margin: 1rem 0;
      flex-wrap: wrap;
    }}
    .toolbar button {{
      background: var(--surface-2);
      border: none;
      color: var(--text);
      padding: 0.6rem 1rem;
      border-radius: 0.4rem;
      cursor: pointer;
    }}
    .toolbar button:hover {{ background: #475569; }}
    pre {{
      background: var(--surface);
      border: 1px solid var(--surface-2);
      padding: 1rem;
      border-radius: 0.4rem;
      overflow-x: auto;
      white-space: pre-wrap;
    }}
    .hint {{
      background: rgba(56, 189, 248, 0.1);
      border-left: 3px solid var(--accent);
      padding: 1rem;
      border-radius: 0 0.4rem 0.4rem 0;
      margin-bottom: 1.5rem;
    }}
    .footer {{
      margin-top: 3rem;
      padding-top: 1rem;
      border-top: 1px solid var(--surface-2);
      color: var(--text-dim);
      font-size: 0.85rem;
    }}
  </style>
</head>
<body>
  <header>
    <h1>Bridge Strategy Review Console</h1>
    <p>完成全部 Fn Concept Domain 的技术 strategy review · 按相关组统一决策</p>
  </header>

  <nav>
    <button class="active" onclick="showTab('overview')">状态总览</button>
    <button onclick="showTab('group-A')">Group A · 可见表面</button>
    <button onclick="showTab('group-B')">Group B · 组件调度</button>
    <button onclick="showTab('group-C')">Group C · 身份授权</button>
    <button onclick="showTab('all-concepts')">全部 Concept</button>
    <button onclick="showTab('records')">Review 记录</button>
    <button onclick="showTab('report')">生成报告</button>
  </nav>

  <main>
    <section id="overview">
      <h2>Concept Domain 当前状态</h2>
      <table>
        <thead>
          <tr><th>Concept</th><th>Status</th><th>Strategy files</th></tr>
        </thead>
        <tbody>
          {concept_rows}
        </tbody>
      </table>
      <div class="hint">
        <strong>使用建议：</strong>优先进入 Group B（组件调度）开始 review，因为 Fn07 目前 BLOCKED，
        且依赖 Fn01 / Fn03 / Fn08 / Fn11。相关 Concept 的决策必须一起做，避免后续合同冲突。
      </div>
    </section>

    {group_sections}

    <section id="all-concepts" class="hidden">
      <h2>全部 Concept Domain</h2>
      <p class="core-object">逐个 Concept 完成一次决策。相关 Concept 已在 Group A/B/C 中组织。</p>
      {all_concept_cards}
    </section>

    <section id="records" class="hidden">
      <h2>已保存的 Review 记录</h2>
      <div class="toolbar">
        <button onclick="loadRecords()">刷新</button>
        <button onclick="exportRecords('json')">导出 JSON</button>
        <button onclick="exportRecords('yaml')">导出 YAML</button>
        <button onclick="clearAllRecords()" style="color: var(--danger);">清空全部记录</button>
      </div>
      <div id="records-list"></div>
    </section>

    <section id="report" class="hidden">
      <h2>生成 Strategy Review 报告</h2>
      <div class="toolbar">
        <button onclick="generateReport()">生成 Markdown 报告</button>
        <button onclick="downloadReport()">下载 report.md</button>
      </div>
      <pre id="report-output">点击「生成 Markdown 报告」预览。</pre>
    </section>

    <div class="footer">
      Generated at {generated_at} from docs/spec/concept-graph.yaml and docs/concepts/Fnxx/.<br>
      Records are stored in browser localStorage under key <code>bridge-strategy-review-records</code>.
    </div>
  </main>

  <script>
    const CONCEPTS = {concepts_json};
    const CHOICES = {choices_json};
    const GROUPS = {groups_json};
    const DETAILS = {details_json};
    const STORAGE_KEY = 'bridge-strategy-review-records';
    let currentReport = '';

    function showTab(id) {{
      document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
      const activeBtn = Array.from(document.querySelectorAll('nav button')).find(b => b.getAttribute('onclick').includes("'" + id + "'"));
      if (activeBtn) activeBtn.classList.add('active');

      document.querySelectorAll('main > section, main > .group-section').forEach(s => s.classList.add('hidden'));
      const target = document.getElementById(id);
      if (target) target.classList.remove('hidden');
      else document.querySelectorAll('.group-section').forEach(s => s.classList.add('hidden'));

      if (id === 'records') loadRecords();
    }}

    function selectChoice(instanceId, key) {{
      const box = document.getElementById('decision-box-' + instanceId);
      box.querySelectorAll('.choice-btn').forEach(btn => btn.classList.remove('selected'));
      box.querySelector(`[data-choice="${{key}}"]`).classList.add('selected');
      box.dataset.selected = key;
    }}

    function saveRecord(instanceId, targetFn) {{
      const box = document.getElementById('decision-box-' + instanceId);
      const key = box.dataset.selected;
      const feedback = document.getElementById('feedback-' + instanceId);
      if (!key) {{
        feedback.textContent = '请先选择一个 review 选项。';
        feedback.className = 'save-feedback err';
        return;
      }}
      const owner = document.getElementById('owner-' + instanceId).value.trim() || 'human-required';
      const reason = document.getElementById('reason-' + instanceId).value.trim();
      if (!reason) {{
        feedback.textContent = '请填写理由 / 备注。';
        feedback.className = 'save-feedback err';
        return;
      }}
      const records = loadStoredRecords();
      records.unshift({{
        timestamp: new Date().toISOString(),
        target: targetFn,
        choice_key: key,
        choice: CHOICES[key],
        owner: owner,
        reason: reason
      }});
      localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
      feedback.textContent = '已保存到 localStorage。';
      feedback.className = 'save-feedback ok';
      document.getElementById('reason-' + instanceId).value = '';
      box.querySelectorAll('.choice-btn').forEach(btn => btn.classList.remove('selected'));
      delete box.dataset.selected;
    }}

    function loadStoredRecords() {{
      try {{
        return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      }} catch (e) {{
        return [];
      }}
    }}

    function loadRecords() {{
      const records = loadStoredRecords();
      const container = document.getElementById('records-list');
      if (records.length === 0) {{
        container.innerHTML = '<p style="color: var(--text-dim);">暂无记录。</p>';
        return;
      }}
      container.innerHTML = records.map((r, i) => `
        <div class="record-card">
          <div class="record-header">
            <span class="record-choice">[${{r.target}}] ${{r.choice}}</span>
            <span class="record-time">${{new Date(r.timestamp).toLocaleString()}}</span>
          </div>
          <div class="record-meta">负责人: ${{r.owner || '—'}}</div>
          <p>${{escapeHtml(r.reason)}}</p>
          <button onclick="deleteRecord(${{i}})" style="margin-top:0.5rem;background:transparent;border:1px solid var(--danger);color:var(--danger);padding:0.3rem 0.6rem;border-radius:0.3rem;cursor:pointer;">删除</button>
        </div>
      `).join('');
    }}

    function deleteRecord(index) {{
      const records = loadStoredRecords();
      records.splice(index, 1);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
      loadRecords();
    }}

    function clearAllRecords() {{
      if (!confirm('确定清空全部 review 记录？此操作不可恢复。')) return;
      localStorage.removeItem(STORAGE_KEY);
      loadRecords();
    }}

    function exportRecords(format) {{
      const records = loadStoredRecords();
      let content, mime, ext;
      if (format === 'json') {{
        content = JSON.stringify(records, null, 2);
        mime = 'application/json';
        ext = 'json';
      }} else {{
        content = records.map(r => `
timestamp: '${{r.timestamp}}'
target: ${{r.target}}
choice: ${{r.choice}}
choice_key: ${{r.choice_key}}
owner: ${{r.owner}}
reason: |
  ${{r.reason.replace(/\\n/g, '\\n  ')}}
`.trim()).join('\\n---\\n');
        mime = 'text/yaml';
        ext = 'yaml';
      }}
      const blob = new Blob([content], {{ type: mime }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `bridge-strategy-review-records-${{new Date().toISOString().slice(0,10)}}.${{ext}}`;
      a.click();
      URL.revokeObjectURL(url);
    }}

    function generateReport() {{
      const records = loadStoredRecords();
      const lines = [
        '# Strategy Review Report',
        '',
        `生成时间: ${{new Date().toISOString()}}`,
        `记录数量: ${{records.length}}`,
        '',
        '## Concept Domain 状态摘要',
        '',
        '| Concept | Status | Strategy files |',
        '|---|---|---|',
      ];
      for (const fn of Object.keys(CONCEPTS)) {{
        const c = CONCEPTS[fn];
        lines.push(`| ${{fn}} | ${{c.status}} | ${{c.files.join(', ') || '(none)'}} |`);
      }}
      lines.push('', '## 统一决策分组', '');
      for (const [gid, g] of Object.entries(GROUPS)) {{
        lines.push(`### Group ${{gid}}: ${{g.name}}`);
        lines.push(`- Concepts: ${{g.concepts.join(', ')}}`);
        lines.push(`- 核心对象: ${{g.core_object}}`);
        lines.push('- 关键问题:');
        for (const q of g.questions) lines.push(`  - ${{q}}`);
        lines.push('');
      }}
      lines.push('## Review 记录', '');
      if (records.length === 0) {{
        lines.push('(无记录)');
      }} else {{
        const byTarget = {{}};
        for (const r of records) {{
          byTarget[r.target] = byTarget[r.target] || [];
          byTarget[r.target].push(r);
        }}
        for (const target of Object.keys(byTarget).sort()) {{
          lines.push(`### ${{target}}`);
          for (const r of byTarget[target]) {{
            lines.push(`- **${{r.choice}}** (${{r.timestamp}}) — ${{r.owner}}`);
            lines.push(`  - ${{r.reason}}`);
          }}
          lines.push('');
        }}
      }}
      currentReport = lines.join('\\n');
      document.getElementById('report-output').textContent = currentReport;
    }}

    function downloadReport() {{
      if (!currentReport) generateReport();
      const blob = new Blob([currentReport], {{ type: 'text/markdown' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `strategy-review-report-${{new Date().toISOString().slice(0,10)}}.md`;
      a.click();
      URL.revokeObjectURL(url);
    }}

    function escapeHtml(text) {{
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }}
  </script>
</body>
</html>
"""


def main():
    concepts = build_data()
    html = render_html(concepts)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"Generated: {OUTPUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
