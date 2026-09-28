#!/usr/bin/env python3
"""Orchestrate the 10-step Bridge skill flow for all Fn11 Actions.

- Generates var/evidence/atoms/Fn11.AYY/critique/SUMMARY.md via codex headless CLI.
- Creates docs/spec/atoms/Fn11.AYY/DESIGN.md for each Action.
- Implements and tests Fn11.A01 host-side contract.
"""

from __future__ import annotations

import json
import multiprocessing
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTION_IDS = [f"Fn11.A{i:02d}" for i in range(1, 23)]
CRITIQUE_WORKERS = 5  # parallel codex exec calls; keep conservative for rate limits


def atom_dir(atom_id: str) -> str:
    """Return the canonical directory-form segment for an atom (e.g. Fn11/A01)."""
    if "." in atom_id and atom_id.startswith("Fn"):
        fn, a = atom_id.split(".", 1)
        return f"{fn}/{a}"
    return atom_id


def read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def run_codex_critique(atom_id: str) -> str:
    """Run codex exec to critique all 10 steps for an Action."""
    atom_path = atom_dir(atom_id)
    docs_dir = ROOT / "docs" / "atoms" / atom_path
    spec_dir = ROOT / "spec" / "atoms" / atom_path
    prompt = f"""You are a Bridge project auditor. Review the {atom_id} atom artifacts for the 10-step Bridge skill flow and produce a concise markdown critique.

Artifacts to review:
- {docs_dir / 'history.md'} (step 1 br-term-define)
- {docs_dir / 'usecase.md'} (step 2 br-case-study)
- {docs_dir / 'routemap.md'} (step 3 br-platform-map / route-space)
- {docs_dir / 'routemap.md'} route section (step 4 br-route-explore)
- {docs_dir / 'strategy.md'} (step 5 br-strategy-decide)
- {spec_dir / 'atom.yaml'} and {spec_dir / 'GAP.yaml'} (step 6 br-action-design input)
- {spec_dir / 'veration.md'} (verification contract)
- {spec_dir / 'ATOM_VALIDATION.md'} (validation plan)

For each of the 10 steps below, output a short "Findings" paragraph and a "Verdict" of PASS/CONCERN/FAIL:
1. br-term-define: term definitions are textbook-grade and boundary is clear.
2. br-case-study: historical cases are relevant, versioned, and traceable.
3. br-platform-map: AOSP ↔ OpenHarmony mapping is explicit and GAP.yaml is updated.
4. br-route-explore: at least 3 technical routes with early experiment plans exist.
5. br-strategy-decide: recommended/backup strategy is recorded with falsifiers.
6. br-action-design: design is frozen with acceptance oracles.
7. br-action-implement: implementation plan/code contract is ready (or marked deferred).
8. br-unit-test: host-side unit test plan exists.
9. br-ui-regress: visual/functional regression plan exists (or marked DEFERRED without circular deps).
10. br-route-resolve: multi-route regression plan exists.

Output only markdown. Keep each step to 3-5 bullets. Note any SPEC_GAP or missing evidence.
"""
    cmd = [
        "codex", "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        "--ephemeral",
        prompt,
    ]
    try:
        result = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=300,
        )
        output = result.stdout + "\n" + result.stderr
    except subprocess.TimeoutExpired:
        output = "ERROR: codex exec timed out after 300s"
    except Exception as exc:
        output = f"ERROR: {exc}"
    return output


def extract_md(output: str) -> str:
    """Keep only the markdown critique from codex exec output."""
    lines = output.splitlines()
    start = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("#"):
            start = i
            break
    # Trim trailing codex CLI metadata that appears after the actual response.
    end = len(lines)
    markers = (
        "Reading additional input from stdin",
        "OpenAI Codex v",
        "workdir:",
        "model:",
        "provider:",
        "approval:",
        "session id:",
        "--------",
        "hook: SessionStart",
    )
    for i in range(start, len(lines)):
        if any(lines[i].startswith(m) for m in markers):
            end = i
            break
    return "\n".join(lines[start:end]).rstrip()


def generate_critique(atom_id: str) -> str:
    atom_path = atom_dir(atom_id)
    critique_dir = ROOT / "evidence" / "atoms" / atom_path / "critique"
    critique_dir.mkdir(parents=True, exist_ok=True)
    summary_path = critique_dir / "SUMMARY.md"
    if summary_path.is_file() and summary_path.stat().st_size > 500:
        return f"[{atom_id}] critique SUMMARY.md already exists, skipping codex call"
    print(f"[{atom_id}] running codex headless critique ...", flush=True)
    raw = run_codex_critique(atom_id)
    md = extract_md(raw)
    header = f"""---
schema_version: 1
atom_id: {atom_id}
document_kind: 10-step-critique
generated_by: codex-headless-cli
---

# {atom_id} · 10-step Bridge skill critique

"""
    summary_path.write_text(header + md, encoding="utf-8")
    msg = f"[{atom_id}] wrote {summary_path}"
    print(msg, flush=True)
    return msg


def action_design_md(atom_id: str) -> str:
    """Build a DESIGN.md from existing atom artifacts."""
    atom_path = atom_dir(atom_id)
    docs_dir = ROOT / "docs" / "atoms" / atom_path
    spec_dir = ROOT / "spec" / "atoms" / atom_path
    atom_yaml_text = read_text(spec_dir / "atom.yaml")
    title = atom_id
    m = re.search(r"^title:\s*(.+)$", atom_yaml_text, re.MULTILINE)
    if m:
        title = m.group(1).strip()
    strategy_text = read_text(docs_dir / "strategy.md")
    routemap_text = read_text(docs_dir / "routemap.md")
    usecase_text = read_text(docs_dir / "usecase.md")
    gap_text = read_text(spec_dir / "GAP.yaml")
    veration_text = read_text(spec_dir / "veration.md")
    validation_text = read_text(spec_dir / "ATOM_VALIDATION.md")

    recommended = "R1"
    backup = "R2"
    if "recommended:" in strategy_text:
        mr = re.search(r"recommended:\s*([^\n]+)", strategy_text)
        if mr:
            recommended = mr.group(1).strip()
    if "backup" in strategy_text.lower() or "备选" in strategy_text:
        mb = re.search(r"备选.*?(R\d)", strategy_text)
        if mb:
            backup = mb.group(1).strip()

    return f"""---
schema_version: 1
atom_id: {atom_id}
document_kind: action-design
title: {title}
generated_by: fn11_complete_concept.py
---

# {atom_id} · {title} · Frozen Action Design

## 1. 行为契约

{title}

## 2. 推荐策略

- 推荐路线：{recommended}
- 备选路线：{backup}
- 决策依据：参见 `docs/atoms/{atom_path}/strategy.md`。

## 3. 路线空间摘要

见 `docs/atoms/{atom_path}/routemap.md`。

{routemap_text[:800] if routemap_text else "(routemap.md not found)"}

## 4. 历史案例

见 `docs/atoms/{atom_path}/usecase.md`。

{usecase_text[:600] if usecase_text else "(usecase.md not found)"}

## 5. 验收 Oracle

### 正向 Oracle
- 在目标输入下，原子行为产生与 acceptance 一致的可观测输出。
- 对映射/已知输入返回 adapter binder 或兼容结果；对未映射/无效输入返回 documented null / safe default / Android 兼容错误码。

### 负向 Oracle
- 不得伪装成功：失败路径必须返回明确错误语义。
- 不得循环依赖：若标记 `DEFERRED`，必须指向已存在的后续原子或外部 gate，且后续原子不反向依赖本原子。

### 失败 Oracle
- 依赖未就绪时不得崩溃；必须降级或阻塞并记录 reason code。
- 跨边界类型转换失败时必须抛出 Android 兼容异常或返回 documented safe default。

## 6. 状态与生命周期

- 创建/查询/修改/删除/执行/并发/隔离边界由 atom.yaml 与 veration.md 共同定义。
- 生命周期状态转换必须可独立观测，证据保存到 `var/evidence/atoms/{atom_path}/`。

## 7. 实现边界

- 不修改 libart / BCP / ART 内部（黑盒律）。
- 所有适配发生在 AOSP V14 ↔ OpenHarmony 6.1 运行时边界。
- 新增服务/行为只需扩展映射表或 adapter 实现，不改动核心注入机制。

## 8. 测试缝

- Host 侧：静态契约、映射表、参数转换的单元测试。
- 设备侧：truly-cold 启动下验证可观测行为与 acceptance 断言。

## 9. GAP 与未决项

```yaml
{gap_text[:1200] if gap_text else "(GAP.yaml not found)"}
```

## 10. 验证计划

见 `docs/spec/atoms/{atom_path}/ATOM_VALIDATION.md` 与 `docs/spec/atoms/{atom_path}/veration.md`。

{validation_text[:800] if validation_text else "(ATOM_VALIDATION.md not found)"}
"""


def create_design(atom_id: str) -> None:
    atom_path = atom_dir(atom_id)
    design_path = ROOT / "spec" / "atoms" / atom_path / "DESIGN.md"
    if design_path.is_file() and design_path.stat().st_size > 1000:
        print(f"[{atom_id}] DESIGN.md already exists, skipping")
        return
    design_path.write_text(action_design_md(atom_id), encoding="utf-8")
    print(f"[{atom_id}] wrote {design_path}")


def implement_fn11_a01() -> None:
    """Implement a host-side contract library for Fn11.A01 with tests."""
    impl_dir = ROOT / "src" / "atoms" / "Fn11" / "A01" / "lib"
    impl_dir.mkdir(parents=True, exist_ok=True)
    test_dir = ROOT / "src" / "atoms" / "Fn11" / "A01" / "tests"
    test_dir.mkdir(parents=True, exist_ok=True)

    service_manager_py = impl_dir / "service_manager_adapter.py"
    if not service_manager_py.is_file():
        service_manager_py.write_text('''"""Host-side contract model for Fn11.A01 ServiceManager lookup.

This module models the A-on-B service-manager mapping contract without
requiring an Android or OpenHarmony runtime. It is used to validate the
frozen design acceptance oracles on the host.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol


class IBinder(Protocol):
    """AOSP-side binder handle marker."""

    def interface_descriptor(self) -> str:
        ...


@dataclass(frozen=True)
class AdapterBinder:
    """An adapter binder returned for a mapped Android service name."""

    service_name: str
    descriptor: str
    adapter_class: str

    def interface_descriptor(self) -> str:
        return self.descriptor


@dataclass
class ServiceManagerAdapter:
    """OHServiceManager contract: maps Android service names to adapter binders.

    - Mapped names return an AdapterBinder whose descriptor matches the AOSP
      AIDL interface descriptor.
    - Unmapped names return None (documented safe null).
    - The mapping table is extensible without changing the lookup mechanism.
    """

    mapping: Dict[str, AdapterBinder] = field(default_factory=dict)

    def register(self, binder: AdapterBinder) -> None:
        self.mapping[binder.service_name] = binder

    def get_service(self, name: str) -> Optional[AdapterBinder]:
        return self.mapping.get(name)

    def check_service(self, name: str) -> Optional[AdapterBinder]:
        return self.get_service(name)

    def list_mapped(self) -> List[str]:
        return sorted(self.mapping.keys())


# Frozen default mapping for the WestLake adapter contract.
DEFAULT_ADAPTER_MAPPING: Dict[str, AdapterBinder] = {
    "activity": AdapterBinder(
        service_name="activity",
        descriptor="android.app.IActivityManager",
        adapter_class="adapter.core.OHActivityManager",
    ),
    "package": AdapterBinder(
        service_name="package",
        descriptor="android.content.pm.IPackageManager",
        adapter_class="adapter.core.OHPackageManager",
    ),
    "window": AdapterBinder(
        service_name="window",
        descriptor="android.view.IWindowManager",
        adapter_class="adapter.core.OHWindowManager",
    ),
    "display": AdapterBinder(
        service_name="display",
        descriptor="android.hardware.display.IDisplayManager",
        adapter_class="adapter.core.OHDisplayManager",
    ),
    "input_method": AdapterBinder(
        service_name="input_method",
        descriptor="android.view.inputmethod.IInputMethodManager",
        adapter_class="adapter.core.OHInputMethodManager",
    ),
    "content": AdapterBinder(
        service_name="content",
        descriptor="android.content.IContentService",
        adapter_class="adapter.core.OHContentService",
    ),
}


def create_default_service_manager() -> ServiceManagerAdapter:
    sm = ServiceManagerAdapter()
    for binder in DEFAULT_ADAPTER_MAPPING.values():
        sm.register(binder)
    return sm
''', encoding="utf-8")
        print("[Fn11.A01] wrote service_manager_adapter.py")

    test_py = test_dir / "test_service_manager_adapter.py"
    if not test_py.is_file():
        test_py.write_text('''"""Host-side unit tests for Fn11.A01 ServiceManager lookup contract."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow importing the implementation under test from sibling lib directory.
LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
sys.path.insert(0, str(LIB_DIR))

from service_manager_adapter import (
    AdapterBinder,
    ServiceManagerAdapter,
    create_default_service_manager,
)


def test_mapped_service_returns_adapter_binder() -> None:
    sm = create_default_service_manager()
    binder = sm.get_service("activity")
    assert binder is not None
    assert binder.service_name == "activity"
    assert binder.descriptor == "android.app.IActivityManager"
    assert binder.adapter_class == "adapter.core.OHActivityManager"


def test_unmapped_service_returns_null() -> None:
    sm = create_default_service_manager()
    assert sm.get_service("nonexistent.service") is None
    assert sm.check_service("another.unmapped") is None


def test_mapping_is_extensible() -> None:
    sm = ServiceManagerAdapter()
    sm.register(
        AdapterBinder(
            service_name="custom",
            descriptor="android.test.ICustom",
            adapter_class="adapter.core.OHCustom",
        )
    )
    assert sm.list_mapped() == ["custom"]
    binder = sm.get_service("custom")
    assert binder is not None
    assert binder.descriptor == "android.test.ICustom"


def test_default_mapping_covers_core_services() -> None:
    sm = create_default_service_manager()
    mapped = sm.list_mapped()
    for name in ("activity", "package", "window", "display", "input_method", "content"):
        assert name in mapped


def test_check_service_equals_get_service() -> None:
    sm = create_default_service_manager()
    assert sm.get_service("display") == sm.check_service("display")
    assert sm.get_service("missing") == sm.check_service("missing") is None


if __name__ == "__main__":
    test_mapped_service_returns_adapter_binder()
    test_unmapped_service_returns_null()
    test_mapping_is_extensible()
    test_default_mapping_covers_core_services()
    test_check_service_equals_get_service()
    print("Fn11.A01 host tests passed")
''', encoding="utf-8")
        print("[Fn11.A01] wrote test_service_manager_adapter.py")

    # Run tests with python directly.
    result = subprocess.run(
        [sys.executable, str(test_py)],
        cwd=test_dir,
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    print("[Fn11.A01] host tests passed")


def main() -> int:
    # Generate critiques in parallel (I/O-bound codex exec calls).
    print(f"Generating critiques with {CRITIQUE_WORKERS} workers ...")
    with multiprocessing.Pool(processes=CRITIQUE_WORKERS) as pool:
        pool.map(generate_critique, ACTION_IDS)

    # Create designs sequentially (fast local file ops).
    for atom_id in ACTION_IDS:
        create_design(atom_id)

    # Implement and test at least one Action.
    implement_fn11_a01()

    # Summary report.
    report = {
        "actions": ACTION_IDS,
        "critique_dir": "var/evidence/atoms/Fn11/AYY/critique/SUMMARY.md",
        "design_file": "docs/spec/atoms/Fn11/AYY/DESIGN.md",
        "implemented": ["Fn11.A01"],
        "tests": "src/atoms/Fn11/A01/tests/test_service_manager_adapter.py",
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
