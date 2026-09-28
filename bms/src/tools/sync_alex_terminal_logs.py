#!/usr/bin/env python3
"""Archive recent iTerm2 and Orca terminal output by visible terminal title.

The active Bridge worktree may be dirty and behind origin/main while long-running
lanes are active.  Generation happens in the active worktree, while --push uses
an isolated sparse clone to commit only this tool and var/logs/alex to main.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import filecmp
import hashlib
import json
import os
import pathlib
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from collections import defaultdict, deque
from typing import Any, Iterable


REPO = pathlib.Path("/opt/Bridge")
OUTPUT_DIR = REPO / "var/logs/alex"
SCRIPT_PATH = REPO / "src/tools/sync_alex_terminal_logs.py"
PLIST_PATH = REPO / "src/tools/launchd/com.alexyang.bridge-terminal-log-sync.plist"
STATE_DIR = pathlib.Path.home() / "Library/Caches/BridgeTerminalLogSync"
STATE_PATH = STATE_DIR / "state.json"
SNAPSHOT_DIR = STATE_DIR / "sources"
PUSH_REPO = STATE_DIR / "push-repo"
LOCK_PATH = STATE_DIR / "sync.lock"
ARCHIVE_DIR = pathlib.Path.home() / "Documents"
LOG_ROOTS = (
    pathlib.Path("/opt/10.Project/16-WestLake/16.81-Oracale/session-logs/iterm"),
    pathlib.Path("/opt/10.Project/16-WestLake % cd 16.81-Oracale"),
)
REMOTE_URL = "https://github.com/a2hlab/00.Workspace.git"
ANSI_CSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
ANSI_OSC = re.compile(r"\x1b\][^\x07]*(?:\x07|\x1b\\)")
ANSI_OTHER = re.compile(r"\x1b(?:[@-_]|[()][0-2A-Z])")
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
UUID_RE = re.compile(
    r"(?i)([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
)
SPINNER_RE = re.compile(r"^[\s⠁-⣿•·.]*$")
WORKING_NOISE_RE = re.compile(
    r"^(?:[\s⠁-⣿•·]*)(?:(?:Wor(?:king?)?|orking|rking|king|ing|ng|g)"
    r"(?:\([^)]*\))?[\s⠁-⣿•·]*){3,}$",
    re.IGNORECASE,
)
MAX_GITHUB_BLOB = 95 * 1024 * 1024


def run(
    args: list[str], *, cwd: pathlib.Path | None = None, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def load_json(path: pathlib.Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def atomic_write(path: pathlib.Path, data: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == data:
        return False
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        tmp.write(data)
        tmp_path = pathlib.Path(tmp.name)
    os.chmod(tmp_path, 0o644)
    os.replace(tmp_path, path)
    return True


def safe_title(title: str | None, fallback: str) -> str:
    value = unicodedata.normalize("NFC", title or "").strip()
    value = ANSI_CSI.sub("", value)
    value = CONTROL.sub("", value)
    value = value.replace("/", "／").replace("\\", "＼").replace(":", "：")
    value = value.strip(" .") or fallback
    if len(value.encode("utf-8")) > 180:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]
        while len(value.encode("utf-8")) > 160:
            value = value[:-1]
        value = f"{value}-{digest}"
    return value


def archive_title(path: pathlib.Path) -> str:
    name = path.name.removesuffix(".itermarchive")
    return name.split(" - ", 1)[-1] if " - " in name else name


def walk_key_values(value: Any, wanted: set[str]) -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in wanted:
                yield key, child
            yield from walk_key_values(child, wanted)
    elif isinstance(value, list):
        for child in value:
            yield from walk_key_values(child, wanted)


def source_uuid(path: pathlib.Path) -> str:
    match = UUID_RE.search(path.name)
    return match.group(1).upper() if match else ""


def collect_archive_mappings(cutoff: float) -> dict[pathlib.Path, tuple[str, float]]:
    mappings: dict[pathlib.Path, tuple[str, float]] = {}
    for archive in ARCHIVE_DIR.glob("*.itermarchive"):
        try:
            archive_mtime = archive.stat().st_mtime
        except OSError:
            continue
        if archive_mtime < cutoff:
            continue
        try:
            with archive.open("rb") as stream:
                payload = plistlib.load(stream)
        except (OSError, plistlib.InvalidFileException, ValueError):
            continue
        title = archive_title(archive)
        for key, raw_value in walk_key_values(
            payload, {"AutoLog File Name", "logFilename"}
        ):
            if key not in {"AutoLog File Name", "logFilename"}:
                continue
            if not isinstance(raw_value, str) or not raw_value.endswith(".log"):
                continue
            source = pathlib.Path(os.path.expandvars(os.path.expanduser(raw_value)))
            if source.exists():
                previous = mappings.get(source)
                if previous is None or archive_mtime >= previous[1]:
                    mappings[source] = (title, archive_mtime)
    return mappings


def collect_live_iterm() -> dict[str, str]:
    script = r'''
set myRows to {}
tell application "iTerm2"
  repeat with w in windows
    repeat with t in tabs of w
      repeat with s in sessions of t
        set end of myRows to ((name of s) as text) & (ASCII character 31) & ((unique ID of s) as text)
      end repeat
    end repeat
  end repeat
end tell
set AppleScript's text item delimiters to ASCII character 30
return myRows as text
'''
    try:
        result = run(["/usr/bin/osascript", "-e", script])
    except (OSError, subprocess.CalledProcessError):
        return {}
    sessions: dict[str, str] = {}
    for row in result.stdout.split("\x1e"):
        fields = row.split("\x1f")
        if len(fields) == 2 and fields[1].strip():
            sessions[fields[1].strip().upper()] = fields[0].strip()
    return sessions


def fallback_title(path: pathlib.Path) -> str:
    parts = path.name.split(".")
    if len(parts) > 1 and parts[1]:
        return parts[1]
    return "iTerm2"


def discover_iterm_sources(cutoff: float) -> list[dict[str, Any]]:
    archives = collect_archive_mappings(cutoff)
    live = collect_live_iterm()
    candidates: list[dict[str, Any]] = []
    seen: set[pathlib.Path] = set()

    def add_source(path: pathlib.Path, title: str, priority: int) -> None:
        try:
            resolved = path.resolve()
            stat = resolved.stat()
        except OSError:
            return
        if resolved in seen or not resolved.is_file():
            return
        if stat.st_mtime < cutoff and resolved not in archives:
            return
        seen.add(resolved)
        uuid = source_uuid(resolved)
        live_title = live.get(uuid)
        candidates.append(
            {
                "id": f"iterm:{resolved}",
                "kind": "iterm",
                "path": str(resolved),
                "title": live_title or title,
                "priority": 4 if live_title else priority,
                "uuid": uuid,
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "inode": stat.st_ino,
                "device": stat.st_dev,
            }
        )

    for source, (title, _) in archives.items():
        add_source(source, title, 3)
    for root in LOG_ROOTS:
        if not root.exists():
            continue
        for source in root.glob("*.log"):
            try:
                if source.stat().st_mtime >= cutoff:
                    add_source(source, fallback_title(source), 1)
            except OSError:
                continue

    # iTerm sometimes writes a raw AutoLog and a second wrapper with identical
    # session UUID and near-identical byte count. Prefer the live/archive mapping.
    chosen: list[dict[str, Any]] = []
    for candidate in sorted(
        candidates,
        key=lambda item: (-item["priority"], -item["mtime"], item["path"]),
    ):
        duplicate = any(
            candidate["uuid"]
            and candidate["uuid"] == item["uuid"]
            and abs(candidate["size"] - item["size"]) <= 4096
            for item in chosen
        )
        if not duplicate:
            chosen.append(candidate)
    return sorted(chosen, key=lambda item: (item["mtime"], item["path"]))


def pane_handles(node: Any, title: str, mapping: dict[str, str]) -> None:
    if not isinstance(node, dict):
        return
    handle = node.get("handle")
    if isinstance(handle, str):
        mapping[handle] = title
    for key in ("panes", "children"):
        child = node.get(key)
        if isinstance(child, list):
            for entry in child:
                pane_handles(entry, title, mapping)
        elif isinstance(child, dict):
            pane_handles(child, title, mapping)


def collect_orca_sources(state: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        payload = json.loads(run(["/opt/homebrew/bin/orca", "terminal", "list", "--json"]).stdout)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError):
        return []
    result = payload.get("result", {})
    visible_titles: dict[str, str] = {}
    for layout in result.get("visualLayouts", []):
        root = layout.get("root", {})
        for tab in root.get("tabs", []) if isinstance(root, dict) else []:
            tab_title = tab.get("title") or "Orca"
            pane_handles(tab.get("panes", {}), tab_title, visible_titles)

    sources: list[dict[str, Any]] = []
    for terminal in result.get("terminals", []):
        handle = terminal.get("handle")
        if not handle:
            continue
        old = state.get("sources", {}).get(f"orca:{handle}", {})
        cursor = str(old.get("offset", "0"))
        try:
            read_payload = json.loads(
                run(
                    [
                        "/opt/homebrew/bin/orca",
                        "terminal",
                        "read",
                        "--terminal",
                        handle,
                        "--cursor",
                        cursor,
                        "--limit",
                        "100000",
                        "--json",
                    ]
                ).stdout
            )
        except (OSError, subprocess.CalledProcessError, json.JSONDecodeError):
            continue
        if not read_payload.get("ok"):
            continue
        data = read_payload.get("result", {}).get("terminal", {})
        title = visible_titles.get(handle) or terminal.get("title")
        sources.append(
            {
                "id": f"orca:{handle}",
                "kind": "orca",
                "handle": handle,
                "title": title or f"Orca-{handle[5:13]}",
                "lines": data.get("tail", []),
                "offset": cursor,
                "next_offset": str(data.get("nextCursor", cursor)),
                "latest_offset": str(data.get("latestCursor", cursor)),
                "mtime": float(terminal.get("lastOutputAt", 0)) / 1000.0,
                "truncated": bool(data.get("truncated", False)),
            }
        )
    return sources


def clean_line(value: str) -> str:
    value = ANSI_OSC.sub("", value)
    value = ANSI_CSI.sub("", value)
    value = ANSI_OTHER.sub("", value)
    while "\b" in value:
        value = re.sub(r".\x08", "", value)
        value = value.replace("\b", "")
    value = CONTROL.sub("", value).rstrip()
    if SPINNER_RE.fullmatch(value) or WORKING_NOISE_RE.fullmatch(value):
        return ""
    if len(value) > 512 and value.count("Working") > 5:
        return ""
    return value


def append_normalized(snapshot: pathlib.Path, chunks: Iterable[str], reset: bool) -> int:
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if reset else "a"
    written = 0
    recent: deque[str] = deque(maxlen=512)
    recent_set: set[str] = set()
    last = ""
    if not reset and snapshot.exists():
        try:
            with snapshot.open("rb") as previous:
                previous.seek(max(0, snapshot.stat().st_size - 65536))
                tail = previous.read().decode("utf-8", errors="replace").splitlines()
                for line in tail[-512:]:
                    recent.append(line)
                    recent_set.add(line)
                last = tail[-1] if tail else ""
        except OSError:
            pass
    with snapshot.open(mode, encoding="utf-8", newline="\n") as output:
        for chunk in chunks:
            cleaned_chunk = chunk.replace("\r", "\n")
            for raw_line in cleaned_chunk.split("\n"):
                line = clean_line(raw_line)
                if not line or line == last:
                    continue
                # Screen redraws repeat the same lines in a short window. Keeping
                # one copy preserves semantic content while removing TUI noise.
                if line in recent_set and len(line) > 3:
                    continue
                output.write(line + "\n")
                written += len((line + "\n").encode("utf-8"))
                last = line
                if len(recent) == recent.maxlen:
                    dropped = recent.popleft()
                    if dropped not in recent:
                        recent_set.discard(dropped)
                recent.append(line)
                recent_set.add(line)
    return written


def file_chunks(path: pathlib.Path, offset: int) -> Iterable[str]:
    with path.open("rb") as stream:
        stream.seek(offset)
        while True:
            raw = stream.read(1024 * 1024)
            if not raw:
                break
            yield raw.decode("utf-8", errors="replace")


def update_snapshots(
    state: dict[str, Any], sources: list[dict[str, Any]]
) -> tuple[dict[str, Any], bool]:
    records = state.setdefault("sources", {})
    changed = False
    for source in sources:
        source_id = source["id"]
        key = hashlib.sha256(source_id.encode("utf-8")).hexdigest()
        snapshot = SNAPSHOT_DIR / f"{key}.log"
        old = records.get(source_id, {})
        title = safe_title(source.get("title"), "terminal")
        reset = False
        if source["kind"] == "iterm":
            offset = int(old.get("offset", 0))
            same_file = (
                old.get("inode") == source["inode"]
                and old.get("device") == source["device"]
                and source["size"] >= offset
            )
            if not same_file:
                offset = 0
                reset = True
            if source["size"] > offset or reset:
                append_normalized(
                    snapshot, file_chunks(pathlib.Path(source["path"]), offset), reset
                )
                changed = True
            record = {
                "id": source_id,
                "kind": "iterm",
                "title": title,
                "path": source["path"],
                "uuid": source["uuid"],
                "offset": source["size"],
                "raw_size": source["size"],
                "mtime": source["mtime"],
                "inode": source["inode"],
                "device": source["device"],
                "snapshot": str(snapshot),
            }
        else:
            lines = source.get("lines", [])
            if lines:
                append_normalized(snapshot, (line for line in lines), False)
                changed = True
            record = {
                "id": source_id,
                "kind": "orca",
                "title": title,
                "handle": source["handle"],
                "offset": source["next_offset"],
                "latest_offset": source["latest_offset"],
                "mtime": source["mtime"],
                "truncated": source["truncated"],
                "snapshot": str(snapshot),
            }
        if old.get("title") != title:
            changed = True
        records[source_id] = record
    return state, changed


def render_outputs(state: dict[str, Any]) -> tuple[list[pathlib.Path], bool]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in state.get("sources", {}).values():
        snapshot = pathlib.Path(record.get("snapshot", ""))
        if snapshot.is_file():
            grouped[record["title"]].append(record)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generated: list[pathlib.Path] = []
    any_changed = False
    for title, records in sorted(grouped.items()):
        output_path = OUTPUT_DIR / f"{safe_title(title, 'terminal')}.log"
        with tempfile.NamedTemporaryFile(dir=OUTPUT_DIR, delete=False) as tmp:
            for record in sorted(
                records, key=lambda item: (item.get("mtime", 0), item["id"])
            ):
                header = (
                    f"\n===== source: {record['id']} =====\n"
                    f"title: {record['title']}\n"
                    f"kind: {record['kind']}\n"
                    f"source_mtime_epoch: {record.get('mtime', 0)}\n"
                    "normalization: ANSI/control stripped; short-window exact "
                    "TUI redraws collapsed\n"
                    "===== transcript =====\n"
                ).encode("utf-8")
                tmp.write(header)
                with pathlib.Path(record["snapshot"]).open("rb") as source:
                    shutil.copyfileobj(source, tmp)
            tmp_path = pathlib.Path(tmp.name)
        size = tmp_path.stat().st_size
        if size > MAX_GITHUB_BLOB:
            tmp_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"{output_path.name} normalized size {size} exceeds "
                f"{MAX_GITHUB_BLOB}; refusing an unpushable Git blob"
            )
        os.chmod(tmp_path, 0o644)
        if output_path.exists() and filecmp.cmp(output_path, tmp_path, shallow=False):
            tmp_path.unlink()
        else:
            os.replace(tmp_path, output_path)
            any_changed = True
        generated.append(output_path)

    manifest_sources = []
    max_mtime = 0.0
    for record in sorted(
        state.get("sources", {}).values(), key=lambda item: item["id"]
    ):
        snapshot = pathlib.Path(record.get("snapshot", ""))
        if not snapshot.is_file():
            continue
        item = {key: value for key, value in record.items() if key != "snapshot"}
        item["normalized_size"] = snapshot.stat().st_size
        manifest_sources.append(item)
        max_mtime = max(max_mtime, float(record.get("mtime", 0)))
    manifest = {
        "schema": 1,
        "capture_window": "initial rolling 24h plus all subsequently observed sources",
        "last_source_update_epoch": max_mtime,
        "normalization": (
            "UTF-8 readable transcript; ANSI/control sequences and exact TUI "
            "redraw repetitions within a 512-line window are removed"
        ),
        "sources": manifest_sources,
    }
    manifest_path = OUTPUT_DIR / "manifest.json"
    if atomic_write(
        manifest_path,
        (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    ):
        any_changed = True
    generated.append(manifest_path)
    return generated, any_changed


def save_state(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write(
        STATE_PATH,
        (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )


def ensure_push_repo() -> None:
    if (PUSH_REPO / ".git").is_dir():
        ready = run(
            ["/usr/bin/git", "rev-parse", "--verify", "HEAD"],
            cwd=PUSH_REPO,
            check=False,
        )
        if ready.returncode == 0:
            return
    if PUSH_REPO.exists():
        shutil.rmtree(PUSH_REPO)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    run(
        [
            "/usr/bin/git",
            "clone",
            "--reference",
            str(REPO),
            "--filter=blob:none",
            "--no-checkout",
            "--single-branch",
            "--branch",
            "main",
            REMOTE_URL,
            str(PUSH_REPO),
        ]
    )
    run(
        ["/usr/bin/git", "sparse-checkout", "init", "--no-cone"],
        cwd=PUSH_REPO,
    )
    run(
        [
            "/usr/bin/git",
            "sparse-checkout",
            "set",
            "var/logs/alex",
            "src/tools/sync_alex_terminal_logs.py",
            "src/tools/launchd/com.alexyang.bridge-terminal-log-sync.plist",
        ],
        cwd=PUSH_REPO,
    )
    run(["/usr/bin/git", "checkout", "main"], cwd=PUSH_REPO)
    run(["/usr/bin/git", "config", "user.name", "Codex Bot"], cwd=PUSH_REPO)
    run(["/usr/bin/git", "config", "user.email", "codex@a2hlab.com"], cwd=PUSH_REPO)


def copy_for_push() -> None:
    target_logs = PUSH_REPO / "var/logs/alex"
    target_logs.mkdir(parents=True, exist_ok=True)
    run(
        [
            "/usr/bin/rsync",
            "-a",
            f"{OUTPUT_DIR}/",
            f"{target_logs}/",
        ]
    )
    for source in (SCRIPT_PATH, PLIST_PATH):
        target = PUSH_REPO / source.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def commit_and_push() -> str:
    ensure_push_repo()
    last_error = ""
    for _ in range(3):
        run(["/usr/bin/git", "fetch", "origin", "main"], cwd=PUSH_REPO)
        run(
            ["/usr/bin/git", "reset", "--hard", "origin/main"],
            cwd=PUSH_REPO,
        )
        copy_for_push()
        paths = [
            "var/logs/alex",
            "src/tools/sync_alex_terminal_logs.py",
            "src/tools/launchd/com.alexyang.bridge-terminal-log-sync.plist",
        ]
        # The repository intentionally ignores *.log globally. This dedicated
        # archive is an explicit exception requested by the owner.
        run(["/usr/bin/git", "add", "-f", "--", *paths], cwd=PUSH_REPO)
        diff = run(
            ["/usr/bin/git", "diff", "--cached", "--quiet"],
            cwd=PUSH_REPO,
            check=False,
        )
        if diff.returncode != 0:
            stamp = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
            run(
                [
                    "/usr/bin/git",
                    "commit",
                    "-m",
                    f"chore(logs): sync terminal logs {stamp}",
                    "--",
                    *paths,
                ],
                cwd=PUSH_REPO,
            )
        pushed = run(
            ["/usr/bin/git", "push", "origin", "main"],
            cwd=PUSH_REPO,
            check=False,
        )
        if pushed.returncode == 0:
            return run(
                ["/usr/bin/git", "rev-parse", "HEAD"], cwd=PUSH_REPO
            ).stdout.strip()
        last_error = (pushed.stderr or pushed.stdout).strip()
    raise RuntimeError(f"git push failed after 3 retries: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=float, default=24.0)
    parser.add_argument("--push", action="store_true")
    args = parser.parse_args()

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("another terminal-log sync is already running")
            return 0
        state = load_json(STATE_PATH, {"schema": 1, "sources": {}})
        cutoff = dt.datetime.now().timestamp() - args.hours * 3600
        iterm_sources = discover_iterm_sources(cutoff)
        orca_sources = collect_orca_sources(state)
        state, snapshots_changed = update_snapshots(
            state, iterm_sources + orca_sources
        )
        generated, outputs_changed = render_outputs(state)
        save_state(state)
        print(
            f"synced {len(iterm_sources)} iTerm sources, "
            f"{len(orca_sources)} Orca sources, {len(generated)} outputs"
        )
        if args.push:
            commit = commit_and_push()
            print(f"origin/main updated at {commit}")
        elif snapshots_changed or outputs_changed:
            print("local outputs changed; --push was not requested")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"terminal-log sync failed: {exc}", file=sys.stderr)
        raise
