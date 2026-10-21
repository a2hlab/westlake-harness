"""T34 UI only. Operator supplies fresh session; no runtime/install/lock creation."""
import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shlex
import time

SERIAL = "61b0657200000000000000000324012c"
ACTOR = "inner(cc-video)"
BMS = "benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py"
LOCK = "scripts/lab/board_note.sh"
HERE = Path(__file__).resolve().parent


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


class Budget:
    def __init__(self, session, recovery, action, wall=time.time, mono=time.monotonic):
        require(session["serial"] == SERIAL, "wrong serial")
        fields = session["holder"].split()
        require(len(fields) == 3 and fields[0] == ACTOR and fields[1].isdigit(),
                "exact actor/PID/time holder required")
        start = session["start"]
        require(type(start) in (int, float) and math.isfinite(start), "invalid start")
        stamp = datetime.fromisoformat(fields[2])
        require(stamp.utcoffset() is not None and abs(stamp.timestamp() - start) <= 1,
                "start must match actual holder time")
        require(re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}",
                             session["boot"]) is not None, "fresh boot required")
        require(not recovery or action in ("launch", "capture", "power"),
                "recovery mode permits normal launch/capture/power only")
        age = wall() - start
        limit = 1800 if recovery else 1200
        require(0 <= age < limit, "window deadline or future start")
        self.mono = mono
        self.deadline = mono() + limit - age

    def left(self, maximum=60):
        left = self.deadline - self.mono()
        require(left > 0, "monotonic window deadline")
        return min(maximum, left)


def ui_envelope(command, boot):
    """One remote dispatch, original UI rc retained; awake even on UI rc failure."""
    require(command.startswith("uitest "), "not a UI command")
    return (
        '( test "$(cat /proc/sys/kernel/random/boot_id)" = ' + shlex.quote(boot) +
        " || exit 97; " + command +
        '; u=$?; printf "\\nT34_UI_RC=%s\\n" "$u"; '
        'power-shell timeout -o 86400000; p=$?; '
        'printf "\\nT34_AWAKE_RC=%s\\n" "$p"; '
        'power-shell dump -s; d=$?; printf "\\nT34_POWER_READ_RC=%s\\n" "$d"; '
        '[ "$u" -eq 0 ] || exit "$u"; [ "$p" -eq 0 ] || exit "$p"; exit "$d" )'
    )


def board_class(b):
    class GuardedBoard(b.Board):
        def __init__(self, session, budget, repo, hdc, out):
            super().__init__(SERIAL, hdc, shlex.join(["bash", str(repo / LOCK)]),
                             ACTOR, out / "commands")
            self.session, self.budget, self.ui_out = session, budget, out
            self.boot = session["boot"]
            self.ui_count = 0
            self.record = None

        def guard(self):
            rc, held = b.Board.command(self, self.lock + ["held", SERIAL],
                                       self.budget.left(10))
            require(rc == 0 and held.strip() == self.session["holder"],
                    "exact holder changed")
            rc, text = b.Board.raw_shell(self, "cat /proc/sys/kernel/random/boot_id",
                                         self.budget.left(10))
            require(rc == 0 and text.strip() == self.boot, "fresh boot changed")
            self.budget.left()

        def command(self, argv, timeout=60):
            # Boot read used by guard enters here: bypass only while guard is active.
            if not getattr(self, "_guarding", False):
                self._guarding = True
                try:
                    self.guard()
                finally:
                    self._guarding = False
            return b.Board.command(self, argv, self.budget.left(timeout))

        def ready(self):
            self._guarding = True
            try:
                self.guard()
            finally:
                self._guarding = False

        def shell(self, command, required=True, timeout=60):
            self.ready()
            if not command.startswith("uitest "):
                return super().shell(command, required, self.budget.left(timeout))
            self.ui_count += 1
            path = self.ui_out / f"ui-{self.ui_count:03d}.json"
            receipt = {"command": command, "status": "intent_unknown",
                       "remote_rc": None, "at": time.time(), "boot": self.boot}
            save(path, receipt)
            # raw_shell writes a single dispatch, with the normal BMS remote rc marker.
            rc, text = super().raw_shell(ui_envelope(command, self.boot),
                                         self.budget.left(timeout))
            receipt.update(status="completed", remote_rc=rc, stdout=text,
                           completed_at=time.time())
            save(path, receipt)  # preserve action result even if awake verification fails
            selected = (self.record or {}).get("selected_icon")
            if selected:
                x, y = selected["center"]
                if command == f"uitest uiInput click {x} {y}":
                    receipt["selected_icon_click"] = True
                    save(path, receipt)
            # All uitest calls (including layout) must restore and verify override.
            require("T34_AWAKE_RC=0" in text and "T34_POWER_READ_RC=0" in text
                    and re.search(r"\bOverrideTimeout=86400000ms\b", text),
                    "awake restoration/readback failed; do not retry UI")
            if required:
                require(rc == 0, "UI remote failure; do not retry")
            return rc, text
    return GuardedBoard


def observe(b, board, out, remote, record, seconds):
    anchor = time.monotonic()
    offsets = sorted({0, seconds} | {x for x in (5, 10, 20, 30, 45, 60, 75) if x < seconds})
    for offset in offsets:
        while time.monotonic() < anchor + offset:
            time.sleep(min(2, anchor + offset - time.monotonic(), board.budget.left(2)))
        board.ready()
        shot = b.capture(board, remote + f"/t{offset}.jpeg", out / f"t{offset}.jpeg")
        record["screenshots"].append(dict(shot, captured=True, requested_offset=offset))
        record["visual_verdict"] = "PENDING_HUMAN_REVIEW"
        b.save(out / "record.json", record)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--app", choices=("boatattack", "libresudoku"), required=True)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--window", type=Path, required=True)
    p.add_argument("--session", type=Path, required=True,
                   help="fresh serial/boot/full holder/start JSON; never an old apply admission")
    p.add_argument("--tag", required=True, help="unique intent/evidence tag; never retry same tag")
    p.add_argument("--recovery", action="store_true")
    p.add_argument("--observe-seconds", type=int, default=0, choices=range(0, 91))
    p.add_argument("--x", type=int)
    p.add_argument("--y", type=int)
    p.add_argument("--power", choices=("awake", "original"), default="awake")
    p.add_argument("action", choices=("launch", "capture", "tap", "back", "power"))
    a = p.parse_args(argv)
    require(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", a.tag), "invalid tag")
    require(a.action == "tap" or (a.x is None and a.y is None), "coordinates only for tap")
    if a.action == "tap":
        require(a.x is not None and a.y is not None and 0 <= a.x < 1200 and 0 <= a.y < 1920,
                "61b portrait coordinates required after human image review")
    require(a.power != "original" or (a.action == "power" and a.recovery),
            "original power only in explicit recovery")
    require(a.action != "power" or a.observe_seconds == 0, "power has no observation schedule")
    session = json.loads(a.session.read_text())
    budget = Budget(session, a.recovery, a.action)
    repo, window = a.repo.resolve(), a.window.resolve()
    require(window.is_dir(), "existing window required; helper cannot create a lock/window")
    pins = json.loads((HERE / "source-pins.json").read_text())
    for name, expected in pins.items():
        require(hashlib.sha256((repo / name).read_bytes()).hexdigest() == expected,
                "source pin drift: " + name)
    spec = importlib.util.spec_from_file_location("t34_bms_ui", repo / BMS)
    b = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b)
    out = window / ("ui-" + a.tag)
    out.mkdir()  # exclusive durable intent; no automatic retries after unknown outcomes
    save(out / "intent.json", dict(session=session, action=a.action, recovery=a.recovery,
                                  status="intent_unknown", at=time.time()))
    board = board_class(b)(session, budget, repo, os.environ.get("HDC", "hdc"), out)
    remote = "/data/local/tmp/t34-ui-" + hashlib.sha256(
        (str(window) + session["holder"] + session["boot"] + a.tag).encode()).hexdigest()[:20]
    record = {"key": a.tag, "serial": SERIAL, "boot": session["boot"],
              "screenshots": [], "visual_verdict": "PENDING_HUMAN_REVIEW"}
    board.record = record
    try:
        board.ready()
        board.shell("mkdir -p " + shlex.quote(remote))
        if a.action == "launch":
            b.desktop_launch(board, {
                "boatattack": {"package": "com.Unity3d.BoatAttackDay",
                               "launch_activity": "com.unity3d.player.UnityPlayerActivity"},
                "libresudoku": {"package": "com.kaajjo.libresudoku",
                               "launch_activity": "com.kaajjo.libresudoku.MainActivity"},
            }[a.app], remote, out, record)
        elif a.action == "tap":
            board.shell(f"uitest uiInput click {a.x} {a.y}")
        elif a.action == "back":
            board.shell("uitest uiInput keyEvent Back")
        elif a.action == "power":
            override = 86400000
            board.shell(f"power-shell timeout -o {override}")
            text = board.shell("power-shell dump -s")[1]
            require(re.search(r"\bTimeout=30000ms\b", text) and
                    re.search(r"\bOverrideTimeout=86400000ms\b", text), "61b original power mismatch")
            save(out / "power.json", {"stdout": text, "original_verified": True})
        if a.action != "power":
            observe(b, board, out, remote, record, a.observe_seconds)
        record["status"] = "completed"
    except Exception as exc:
        record.update(status="FAILED_OR_UNKNOWN_NO_AUTOMATIC_RETRY", error=str(exc))
        raise
    finally:
        b.save(out / "record.json", record)
        print(out)


if __name__ == "__main__":
    main()
