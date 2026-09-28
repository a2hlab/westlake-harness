#!/usr/bin/env python3
"""Prepare and rate-limit publication of the local Pro lifecycle board to Vercel.

The board remains a read-only projection of var/state/pro-board.  Vercel receives
only a generated HTML snapshot.  Publishing is skipped when the source
fragments are unchanged or when the minimum interval has not elapsed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path("/Volumes/Bridge")
FRAGMENT_DIR = ROOT / ".state" / "pro-board"
RENDERER = ROOT / "tools" / "pro_board_render.py"
SOURCE_HTML = ROOT / "worker" / "01.kanban" / "pro-lifecycle-board.html"
DEPLOY_DIR = ROOT / ".work" / "bridge-pro-lifecycle-board"
STATE_FILE = ROOT / ".state" / "pro-board-vercel" / "publish-state.json"
DEFAULT_MIN_INTERVAL_SECONDS = 20 * 60


def source_digest() -> str:
    digest = hashlib.sha256()
    inputs = sorted(FRAGMENT_DIR.glob("*.json"))
    escalation = FRAGMENT_DIR / "escalations.md"
    if escalation.exists():
        inputs.append(escalation)
    if RENDERER.exists():
        inputs.append(RENDERER)
    if not inputs:
        raise RuntimeError(f"没有可发布的看板真源：{FRAGMENT_DIR}")
    for path in inputs:
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def prepare_site() -> None:
    subprocess.run(["/usr/bin/python3", str(RENDERER)], cwd=ROOT, check=True)
    page = SOURCE_HTML.read_text()
    page = re.sub(
        r'<meta http-equiv="refresh" content="\d+">',
        '<meta http-equiv="refresh" content="300">\n'
        '<meta name="robots" content="noindex,nofollow,noarchive">',
        page,
        count=1,
    )
    page = page.replace(
        "每 30s 自刷新",
        "网页每 5 分钟刷新；云端内容最长约 20 分钟更新",
        1,
    )
    DEPLOY_DIR.mkdir(parents=True, exist_ok=True)
    (DEPLOY_DIR / "index.html").write_text(page)
    (DEPLOY_DIR / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
    (DEPLOY_DIR / "vercel.json").write_text(
        json.dumps(
            {
                "$schema": "https://openapi.vercel.sh/vercel.json",
                "cleanUrls": True,
                "headers": [
                    {
                        "source": "/(.*)",
                        "headers": [
                            {"key": "X-Robots-Tag", "value": "noindex, nofollow, noarchive"},
                            {"key": "Cache-Control", "value": "public, max-age=0, must-revalidate"},
                        ],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        value = json.loads(STATE_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def save_state(value: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def publish(force: bool, min_interval_seconds: int, dry_run: bool) -> int:
    current_digest = source_digest()
    state = load_state()
    now = int(time.time())
    age = now - int(state.get("deployed_at_epoch", 0))

    if not force and state.get("source_sha256") == current_digest:
        print("SKIP：看板真源没有变化")
        return 0
    if not force and age < min_interval_seconds:
        remaining = min_interval_seconds - age
        print(f"SKIP：免费额度保护，约 {remaining // 60 + 1} 分钟后可再次发布")
        return 0

    prepare_site()
    if dry_run:
        print(f"DRY_RUN：已准备 {DEPLOY_DIR}，未调用 Vercel")
        return 0

    vercel = shutil.which("vercel")
    if not vercel:
        raise RuntimeError("未找到 Vercel CLI")
    completed = subprocess.run(
        [vercel, "deploy", "--prod", "--yes", "--cwd", str(DEPLOY_DIR)],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
    print(output)
    urls = re.findall(r"https://[^\s]+", output)
    save_state(
        {
            "source_sha256": current_digest,
            "deployed_at_epoch": now,
            "deployment_url": urls[-1].rstrip(".\x1b[0m") if urls else None,
            "minimum_interval_seconds": min_interval_seconds,
        }
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="限频发布 Pro 生命周期看板到 Vercel")
    parser.add_argument("--force", action="store_true", help="忽略内容与时间限频检查")
    parser.add_argument("--dry-run", action="store_true", help="只生成待部署目录")
    parser.add_argument(
        "--min-interval-seconds",
        type=int,
        default=DEFAULT_MIN_INTERVAL_SECONDS,
        help="两次云端发布之间的最短秒数（默认 1200）",
    )
    args = parser.parse_args()
    if args.min_interval_seconds < 60:
        parser.error("最短发布间隔不得小于 60 秒")
    return publish(args.force, args.min_interval_seconds, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
