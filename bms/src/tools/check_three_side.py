#!/usr/bin/env python3
"""三侧对照闸机械校验(three-side gate)。

规则真源:docs/guides/three-side-gate.md。
任何进度点推进前,推进者必须提交一份 three-side.yaml(schema
bridge.three-side.v1),本脚本机械校验:

  1. 三侧锚定齐全 —— android_side(安卓侧原生实现)、oh_side(OpenHarmony
     侧原生实现)、ours(我方当前进度点)各至少一条锚,仓内引用路径必须
     存在,仓外源码树引用(tree: aosp|oh)必须 path/anchor/claim 齐全
     (仓外锚的实质核对由独立 verifier 承担,本脚本只验格式,输出
     DECLARED_ONLY 提示)。
  2. 状态机逻辑闭合 —— 对声明的每台 SCXML 状态机:所有 transition target
     指向已定义状态;initial 引用合法;无不可达状态;非 final 叶子状态
     必须自身或祖先带出边(或列入 terminal_ok);id 不重复。
  3. 推进本身闭合 —— ours.current_state 与 ours.target_state 必须存在于
     advancement 状态机,且 target 从 current 沿 transition 可达。
  4. 独立核验 —— verification 块必填:verifier 不得与 implementer 相同,
     receipt 文件必须存在且非空,verdict 必须为 PASS。

Exit 0 + THREE_SIDE_GATE_PASS 全部通过。
Exit 1 + THREE_SIDE_GATE_FAIL 存在 finding(逐条打印)。
Exit 2 用法错误(文件缺失、YAML 不可解析、schema 不符)。

依赖 PyYAML(Bridge 工具链自带,与 check_versions.py 一致)。
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR PyYAML unavailable", file=sys.stderr)
    sys.exit(2)

SCHEMA = "bridge.three-side.v1"
SCXML_NS = "{http://www.w3.org/2005/07/scxml}"
EXTERNAL_TREES = {"aosp", "oh"}


def _fail_usage(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    print(f"ERROR {msg}", file=sys.stderr)
    sys.exit(2)


# ---------------------------------------------------------------- SCXML 解析


class Machine:
    """一台 SCXML 机的扁平视图:状态节点、父子关系、迁移边。"""

    def __init__(self, path: Path):
        self.path = path
        self.states: dict[str, ET.Element] = {}
        self.parent: dict[str, str | None] = {}
        self.finals: set[str] = set()
        self.parallels: set[str] = set()
        # transitions: (owner_state_id_or_None, transition_id, target_or_None)
        self.transitions: list[tuple[str | None, str | None, str | None]] = []
        self.initial_root: str | None = None
        self.initial_of: dict[str, str] = {}
        self.dup_ids: list[str] = []
        self._load()

    def _load(self) -> None:
        root = ET.parse(self.path).getroot()
        self.initial_root = root.get("initial")
        self._walk(root, None)

    def _walk(self, elem: ET.Element, parent_id: str | None) -> None:
        for child in elem:
            tag = child.tag.removeprefix(SCXML_NS)
            if tag in ("state", "parallel", "final"):
                sid = child.get("id")
                if sid:
                    if sid in self.states:
                        self.dup_ids.append(sid)
                    self.states[sid] = child
                    self.parent[sid] = parent_id
                    if tag == "final":
                        self.finals.add(sid)
                    if tag == "parallel":
                        self.parallels.add(sid)
                    init = child.get("initial")
                    if init:
                        self.initial_of[sid] = init
                self._walk(child, sid or parent_id)
            elif tag == "transition":
                self.transitions.append(
                    (parent_id, child.get("id"), child.get("target"))
                )
            else:
                self._walk(child, parent_id)

    # -- 结构辅助 --------------------------------------------------------

    def children_of(self, sid: str | None) -> list[str]:
        return [s for s, p in self.parent.items() if p == sid]

    def entry_closure(self, sid: str) -> set[str]:
        """进入 sid 时被动进入的状态集(initial 链 + parallel 全区域)。"""
        seen: set[str] = set()
        stack = [sid]
        while stack:
            cur = stack.pop()
            if cur in seen or cur not in self.states:
                continue
            seen.add(cur)
            kids = self.children_of(cur)
            if not kids:
                continue
            if cur in self.parallels:
                stack.extend(kids)
            else:
                init = self.initial_of.get(cur)
                stack.append(init if init in self.states else kids[0])
        return seen

    def outgoing(self, sid: str) -> list[str]:
        """sid 激活期间可触发的迁移目标(含祖先层定义的迁移)。"""
        chain: set[str | None] = {sid}
        cur = self.parent.get(sid)
        while cur is not None:
            chain.add(cur)
            cur = self.parent.get(cur)
        chain.add(None)
        return [t for owner, _tid, t in self.transitions if owner in chain and t]

    def reachable(self) -> set[str]:
        start = self.initial_root
        if start not in self.states:
            kids = self.children_of(None)
            if not kids:
                return set()
            start = kids[0]
        seen: set[str] = set()
        frontier = self.entry_closure(start)
        while frontier:
            sid = frontier.pop()
            if sid in seen:
                continue
            seen.add(sid)
            for target in self.outgoing(sid):
                if target in self.states:
                    frontier |= self.entry_closure(target)
        return seen

    def path_exists(self, src: str, dst: str) -> bool:
        seen: set[str] = set()
        frontier = self.entry_closure(src)
        while frontier:
            sid = frontier.pop()
            if sid in seen:
                continue
            seen.add(sid)
            if sid == dst:
                return True
            for target in self.outgoing(sid):
                if target in self.states:
                    frontier |= self.entry_closure(target)
        return dst in seen


def check_machine(m: Machine, terminal_ok: set[str], findings: list[str]) -> None:
    rel = m.path
    for sid in m.dup_ids:
        findings.append(f"SM_DUP_ID {rel}: state id '{sid}' defined more than once")
    tids: set[str] = set()
    for _owner, tid, target in m.transitions:
        if tid:
            if tid in tids:
                findings.append(f"SM_DUP_ID {rel}: transition id '{tid}' duplicated")
            tids.add(tid)
        if target and target not in m.states:
            findings.append(
                f"SM_TARGET_UNDEFINED {rel}: transition '{tid or '?'}' targets "
                f"unknown state '{target}'"
            )
    if m.initial_root and m.initial_root not in m.states:
        findings.append(f"SM_INITIAL_INVALID {rel}: root initial '{m.initial_root}'")
    for owner, init in m.initial_of.items():
        if init not in m.states:
            findings.append(f"SM_INITIAL_INVALID {rel}: '{owner}' initial '{init}'")
    if any(f.startswith(("SM_TARGET_UNDEFINED", "SM_INITIAL_INVALID")) for f in findings):
        return  # 引用已破损,可达性结论不可靠,不再叠报
    reach = m.reachable()
    for sid in m.states:
        if sid not in reach:
            findings.append(f"SM_UNREACHABLE {rel}: state '{sid}' unreachable")
    for sid in m.states:
        if sid in m.finals or sid in terminal_ok:
            continue
        if self_or_kids := m.children_of(sid):
            _ = self_or_kids  # 复合状态由子状态承接,不算叶子
            continue
        if not m.outgoing(sid):
            findings.append(
                f"SM_DEAD_END {rel}: non-final leaf '{sid}' has no outgoing "
                "transition (self or ancestor); add one or list in terminal_ok"
            )


# ---------------------------------------------------------------- 三侧校验


def check_anchor(entry: object, side: str, root: Path, findings: list[str],
                 notes: list[str]) -> None:
    if not isinstance(entry, dict):
        findings.append(f"ANCHOR_INCOMPLETE {side}: entry must be a mapping")
        return
    claim = entry.get("claim")
    tree = entry.get("tree")
    if tree is not None:
        if tree not in EXTERNAL_TREES:
            findings.append(f"ANCHOR_INCOMPLETE {side}: unknown tree '{tree}'")
        if not entry.get("path") or not entry.get("anchor") or not claim:
            findings.append(
                f"ANCHOR_INCOMPLETE {side}: tree ref needs path+anchor+claim"
            )
        else:
            notes.append(
                f"DECLARED_ONLY {side}: {tree}:{entry['path']}#{entry['anchor']} "
                "(仓外锚,实质核对归 verifier)"
            )
        return
    ref = entry.get("ref")
    if not ref or not claim:
        findings.append(f"ANCHOR_INCOMPLETE {side}: repo ref needs ref+claim")
        return
    rel = str(ref).split("#", 1)[0]
    if not (root / rel).exists():
        findings.append(f"ANCHOR_PATH_MISSING {side}: {rel}")


def run(root: Path, file: Path) -> int:
    try:
        data = yaml.safe_load(file.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        _fail_usage(f"YAML_INVALID {file}: {exc}")
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        _fail_usage(f"SCHEMA_MISMATCH {file}: expected schema: {SCHEMA}")

    findings: list[str] = []
    notes: list[str] = []

    if not str(data.get("progress_point") or "").strip():
        findings.append("SIDE_EMPTY progress_point: 必须一句话写明本次推进的进度点")

    for side in ("android_side", "oh_side"):
        entries = data.get(side)
        if not isinstance(entries, list) or not entries:
            findings.append(f"SIDE_EMPTY {side}: 至少一条锚")
            continue
        for entry in entries:
            check_anchor(entry, side, root, findings, notes)

    ours = data.get("ours")
    cur = tgt = None
    if not isinstance(ours, dict):
        findings.append("SIDE_EMPTY ours: 必须给出 progress_ref/current_state/target_state")
    else:
        pref = str(ours.get("progress_ref") or "")
        if not pref:
            findings.append("SIDE_EMPTY ours: progress_ref 缺失")
        elif not (root / pref.split("#", 1)[0]).exists():
            findings.append(f"ANCHOR_PATH_MISSING ours: {pref.split('#', 1)[0]}")
        cur = ours.get("current_state")
        tgt = ours.get("target_state")
        if not cur or not tgt:
            findings.append("SIDE_EMPTY ours: current_state/target_state 缺失")

    terminal_ok = set(data.get("terminal_ok") or [])
    sm = data.get("state_machines") or {}
    adv_path = sm.get("advancement") if isinstance(sm, dict) else None
    machines: list[tuple[str, Path]] = []
    if not adv_path:
        findings.append("SM_FILE_MISSING state_machines.advancement: 必须声明推进所依据的状态机")
    else:
        machines.append(("advancement", root / str(adv_path)))
    for extra in (sm.get("others") or []) if isinstance(sm, dict) else []:
        machines.append(("others", root / str(extra)))

    adv_machine: Machine | None = None
    for role, mpath in machines:
        if not mpath.exists():
            findings.append(f"SM_FILE_MISSING {role}: {mpath}")
            continue
        try:
            machine = Machine(mpath)
        except ET.ParseError as exc:
            findings.append(f"SM_FILE_MISSING {role}: {mpath} unparsable ({exc})")
            continue
        local: list[str] = []
        check_machine(machine, terminal_ok, local)
        findings.extend(local)
        if role == "advancement":
            adv_machine = machine

    if adv_machine and cur and tgt:
        for name, sid in (("current_state", cur), ("target_state", tgt)):
            if sid not in adv_machine.states:
                findings.append(
                    f"ADV_STATE_UNKNOWN ours.{name}: '{sid}' not in "
                    f"{adv_machine.path}"
                )
        if cur in adv_machine.states and tgt in adv_machine.states:
            if not adv_machine.path_exists(cur, tgt):
                findings.append(
                    f"ADV_NO_PATH ours: no transition path '{cur}' -> '{tgt}'"
                )

    ver = data.get("verification")
    if not isinstance(ver, dict):
        findings.append("VERIFY_MISSING verification: 独立核验块必填")
    else:
        impl = str(ver.get("implementer") or "").strip()
        verf = str(ver.get("verifier") or "").strip()
        if not impl or not verf:
            findings.append("VERIFY_MISSING verification: implementer/verifier 必填")
        elif impl == verf:
            findings.append(
                f"VERIFY_SELF verification: implementer 与 verifier 同为 '{impl}',"
                "实施者不得自签(harness 判断四)"
            )
        receipt = ver.get("receipt")
        rpath = root / str(receipt) if receipt else None
        if not receipt or not rpath.exists() or rpath.stat().st_size == 0:
            findings.append(f"VERIFY_RECEIPT_MISSING verification: {receipt}")
        if ver.get("verdict") != "PASS":
            findings.append(
                f"VERIFY_NOT_PASS verification: verdict={ver.get('verdict')!r}"
            )

    for note in notes:
        print(note)
    for finding in findings:
        print(finding)
    if findings:
        print(f"THREE_SIDE_GATE_FAIL findings={len(findings)}")
        return 1
    print("THREE_SIDE_GATE_PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="三侧对照闸机械校验")
    ap.add_argument("--root", default=".", help="仓库根(默认当前目录)")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="three-side.yaml 路径")
    group.add_argument("--feature", help="特性/概念目录,取其下 three-side.yaml")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        _fail_usage(f"root not a directory: {root}")
    file = (
        Path(args.file) if args.file else Path(args.feature) / "three-side.yaml"
    )
    if not file.is_absolute():
        file = root / file
    if not file.exists():
        print(f"FILE_MISSING {file}")
        print("THREE_SIDE_GATE_FAIL findings=1")
        return 1
    return run(root, file)


if __name__ == "__main__":
    sys.exit(main())
