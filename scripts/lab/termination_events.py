"""Correlate app terminal events and system-emitted lifecycle observations."""

import re


HILOG = re.compile(r"^(\d\d-\d\d\s+\S+)\s+(\d+)\s+(\d+)\s+([A-Z])\s+(\S+):\s*(.*)$")
IGNORED_SIGNALS = {4, 35, 42}


def parse(line, number):
    match = HILOG.match(line)
    if not match:
        return None
    timestamp, pid, tid, level, tag, message = match.groups()
    return dict(line=number, text=line, timestamp=timestamp, pid=int(pid),
                tid=int(tid), level=level, tag=tag, message=message)


def classify(event, pids, package):
    message = event["message"]
    tag = event["tag"]
    own = event["pid"] in pids
    role = None
    kind = None
    value = None
    victim = event["pid"] if own else None
    if own and not re.search(r"\[IFACE|\[VTBL|\[VTLEN|^\s*at ", message):
        if "J_invokeStaticMain_main_threw:" in message or "FATAL EXCEPTION:" in message:
            kind, role = "java-terminal", "terminal"
        elif match := re.search(r"System\.exit called, status:\s*(-?\d+)\b", message):
            kind, role, value = "system-exit", "terminal", int(match[1])
        elif "ASSERT FAILED" in message or "abort() called from libhwui" in message:
            kind, role = "native-abort", "terminal"
        elif match := re.search(r"Fatal signal (\d+)\b", message):
            value = int(match[1])
            kind, role = "fatal-signal", "observation" if value in IGNORED_SIGNALS else "terminal"
    if "APPSPAWN" in tag:
        match = re.search(r"(?<![\w.])" + re.escape(package) + r" with pid (\d+) exit with (signal|code):\s*(-?\d+)\b", message)
        if match and int(match[1]) in pids:
            victim, value = int(match[1]), int(match[3])
            kind = "appspawn-" + match[2]
            role = "wait-result" if match[2] == "code" or value not in IGNORED_SIGNALS else "observation"
    target = re.search(r"\bpid\s*[:=]\s*(\d+)\b", message, re.I)
    if target and int(target[1]) in pids:
        victim = int(target[1])
        if "Client died" in message or "null killProcessByPid" in message:
            kind, role = "remote-death", "observation"
        if re.search(r"lmkd|memmgr|lowmemory", tag, re.I) and re.search(r"\bkill(?:ed|ing)?\b", message, re.I):
            kind, role = "memory-kill", "terminal"
        if re.search(r"watchdog|ANR|APP_FREEZE", tag + " " + message, re.I):
            kind, role = "watchdog-anr", "terminal" if re.search(r"\bkill(?:ed|ing)?\b", message, re.I) else "observation"
    remote = re.search(r"kill reason=OnRemoteDied,\s*(\d+)\b", message)
    if "AppMS" in tag and remote and int(remote[1]) in pids:
        kind, role, victim = "remote-death-cleanup", "observation", int(remote[1])
    ability = re.search(r"Ability on scheduler died:\s*'([^']+)'", message)
    if "AMS" in tag and ability and (ability[1] == package or ability[1].startswith(package + ".")):
        kind, role, victim = "ability-scheduler-death", "observation", None
    if not kind:
        return None
    return dict(event, kind=kind, role=role, victim_pid=victim, value=value)


def analyze(lines, pids, package):
    output = []
    for number, line in enumerate(lines, 1):
        event = parse(line, number)
        if event and (matched := classify(event, pids, package)):
            output.append(matched)
    return output
