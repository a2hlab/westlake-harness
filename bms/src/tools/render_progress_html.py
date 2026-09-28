#!/usr/bin/env python3
"""Render docs/progress.md into the generated docs/boards/progress.html view."""

from __future__ import annotations

import html
import os
from pathlib import Path
import re
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "progress.md"
OUTPUT = ROOT / "docs" / "progress.html"


def inline(text: str) -> str:
    escaped = html.escape(text, quote=True)
    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2">\1</a>',
        escaped,
    )
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)


def render(markdown: str) -> str:
    body: list[str] = []
    list_kind: str | None = None
    pending_item: str | None = None

    def flush_item() -> None:
        nonlocal pending_item
        if pending_item is not None:
            body.append(f"      <li>{inline(pending_item)}</li>")
            pending_item = None

    def close_list() -> None:
        nonlocal list_kind
        flush_item()
        if list_kind is not None:
            body.append(f"    </{list_kind}>")
            list_kind = None

    for raw in markdown.splitlines():
        heading = re.fullmatch(r"(#{1,6})\s+(.+)", raw)
        item = re.fullmatch(r"(-|\d+\.)\s+(.+)", raw)
        if heading:
            close_list()
            level = len(heading.group(1))
            body.append(f"    <h{level}>{inline(heading.group(2))}</h{level}>")
        elif item:
            kind = "ul" if item.group(1) == "-" else "ol"
            if list_kind != kind:
                close_list()
                list_kind = kind
                body.append(f"    <{kind}>")
            else:
                flush_item()
            pending_item = item.group(2)
        elif raw.startswith("   ") and pending_item is not None:
            pending_item += " " + raw.strip()
        elif not raw.strip():
            close_list()
        else:
            close_list()
            body.append(f"    <p>{inline(raw.strip())}</p>")
    close_list()

    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1">',
            "  <title>Bridge Progress</title>",
            "</head>",
            "<body>",
            "  <!-- Generated view. Edit docs/progress.md and rerun src/tools/render_progress_html.py. -->",
            "  <main>",
            *body,
            "  </main>",
            "</body>",
            "</html>",
            "",
        ]
    )


def main() -> None:
    rendered = render(SOURCE.read_text(encoding="utf-8"))
    descriptor, temporary = tempfile.mkstemp(
        prefix=".progress.html.", dir=OUTPUT.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, OUTPUT)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise
    print(f"PASS: rendered {SOURCE} -> {OUTPUT}")


if __name__ == "__main__":
    main()
