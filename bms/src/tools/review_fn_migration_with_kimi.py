#!/usr/bin/env python3
"""Run one read-only Kimi migration critique per Fn atom.

Each atom is a separate headless Kimi invocation.  Results use the historical
``veration-reviews`` directory and are resumable: an existing non-empty result
is skipped unless ``--force`` is given.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import subprocess
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "kimi-code/k3"
REVIEW_NAME = "kimi-fn-migration-review.md"


def atom_ids() -> list[str]:
    return sorted(
        f"{path.parent.name}.{path.name}"
        for path in (ROOT / "docs/spec/atoms").glob("Fn*/A*")
        if path.is_dir()
    )


def review_path(atom_id: str) -> Path:
    fn_id, ayy = atom_id.split(".", 1)
    return ROOT / "docs/atoms" / fn_id / ayy / "veration-reviews" / REVIEW_NAME


def build_prompt(atom_id: str) -> str:
    fn_id, ayy = atom_id.split(".", 1)
    metadata = yaml.safe_load(
        (ROOT / "docs/spec/atoms" / fn_id / ayy / "atom.yaml").read_text(encoding="utf-8")
    )
    legacy_id = metadata["legacy_ids"][0]
    fn_id, ayy = atom_id.split(".", 1)
    return f"""你是 Bridge 原子迁移的独立反方审查员。只审查一个原子：{atom_id}，
旧坐标 {legacy_id}。当前工作目录是 /opt/Bridge。

只读审查，禁止修改、创建或删除任何文件。请读取并交叉核对：
- docs/atoms/{fn_id}/{ayy}/
- docs/spec/atoms/{fn_id}/{ayy}/
- var/evidence/atoms/{fn_id}/{ayy}/
- src/atoms/{fn_id}/{ayy}/
- docs/archive/legacy-lxx/MIGRATION_MAP.md 中 {legacy_id} 的映射
- docs/spec/atoms/{fn_id}/{ayy}/atom.yaml 中列出的两个历史来源目录

审查目标仅是“迁移是否无语义误解”，不是给 CM/DM/VM 晋级。逐项检查：
1. {legacy_id} → {atom_id} 是否严格遵守 L02→Fn01 ... L13→Fn12，A 编号不变。
2. 条目是否真的是可独立开发、验收的功能，而不是原则、铁律、验证要求、
   Journey、流程或治理。
3. 新标题、边界和依赖是否忠实于旧 canonical atom.yaml；旧依赖映射是否丢失、
   错指或被错误提升为 Fn。
4. 历史研究文件、规格、证据、图片和子目录是否完整，四域归位是否改变含义。
5. 两份历史 atom.yaml 或其他文档是否存在实质冲突；必须指出冲突，不能替作者裁决。
6. 是否把旧文档、旧 receipt、host/build 结果或占位文件误当成实现或 PASS。
7. 文内旧 Lxx.Ayy 是可追溯历史引用，还是会让读者误认为仍是当前 ID。

输出简洁 Markdown，必须使用以下结构：
# {atom_id} migration critique
## Verdict
只能写 `ACCEPT` 或 `NEEDS_CORRECTION`，这是迁移审查结论，不是成熟度 PASS。
## Findings
每条写 `[P0|P1|P2]`、问题、精确文件路径与可定位标题/字段、为何构成语义风险。
没有问题写 `- None.`
## Preserved facts
列出确认保持一致的旧标题、旧 ID、新 ID 和依赖关系。
## Required corrections
只列最小更正；没有则写 `- None.`

不得写泛泛建议。不得因为材料“存在”而认定功能实现、设备验证或任何成熟度通过。
最终只输出审查 Markdown，不要输出操作过程。
"""


def run_one(atom_id: str, model: str, force: bool, timeout: int) -> tuple[str, str]:
    output = review_path(atom_id)
    if output.is_file() and output.stat().st_size > 100 and not force:
        return atom_id, "SKIP"

    output.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            "kimi",
            "--model",
            model,
            "--prompt",
            build_prompt(atom_id),
            "--output-format",
            "text",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        return atom_id, f"ERROR exit={result.returncode}: {detail[-500:]}"

    content = result.stdout.strip()
    if len(content) < 100:
        return atom_id, "ERROR empty or too-short review"

    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=output.parent,
        prefix=f".{REVIEW_NAME}.",
        delete=False,
    ) as stream:
        stream.write(content.rstrip() + "\n")
        temporary = Path(stream.name)
    temporary.replace(output)
    return atom_id, "DONE"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selected = atom_ids()
    if args.only:
        requested = set(args.only)
        unknown = requested - set(selected)
        if unknown:
            raise SystemExit(f"unknown atom IDs: {', '.join(sorted(unknown))}")
        selected = [atom_id for atom_id in selected if atom_id in requested]
    if args.limit is not None:
        selected = selected[: args.limit]
    if args.jobs < 1 or args.jobs > 4:
        raise SystemExit("--jobs must be between 1 and 4")

    failures = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = {
            executor.submit(
                run_one, atom_id, args.model, args.force, args.timeout
            ): atom_id
            for atom_id in selected
        }
        for future in concurrent.futures.as_completed(futures):
            atom_id, status = future.result()
            print(f"{atom_id} {status}", flush=True)
            if status.startswith("ERROR"):
                failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
