"""PID-scoped candidate triage; no log marker implies visible UI."""

import re


HEADER = re.compile(r"^(\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2}\.\d+)\s+(\d+)\s+(\d+)\s+([VDIWEF])\s+([^:]+):\s*(.*)$")
CATEGORIES = ("waiting-network", "waiting-permission-or-dialog", "window-without-frame", "caught-exception", "other")
OLD_RENDER = re.compile(r"Displayed|surfaceCreated|flushWindow|AceAbility|ArkUI|RSRenderNode|onWindowFocusChanged|WindowStageImpl|AbilityStage|firstFrame|first frame|AddSurfaceNode|CommitAndReleaseBuffer")
FATAL = re.compile(r"J_invokeStaticMain_main_threw|FATAL EXCEPTION:|Fatal signal \d+|SIGSEGV|JNI DETECTED ERROR IN APPLICATION")


def parse(line, number):
    match = HEADER.match(line)
    if not match:
        return None
    date, time, pid, tid, level, tag, message = match.groups()
    return dict(line=number, timestamp=date + " " + time, pid=int(pid), tid=int(tid), level=level, tag=tag, message=message, text=line)


def scoped(events, pids, cutoff=None):
    if not pids or any(not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0 for pid in pids):
        raise ValueError("verified positive integer PIDs required")
    return [event for event in events if event["pid"] in pids and (cutoff is None or event["timestamp"] <= cutoff)]


def is_execution(event):
    message = event["message"]
    return not ("class_linker.cc:" in message or "-> fn=" in message
                or event["tag"].endswith("/OH_RegHook")
                or re.match(r"\d+: (?:void|boolean|int|long|java\.)", message))


def matches(events, pattern):
    regex = re.compile(pattern)
    return [event for event in events if is_execution(event) and regex.search(event["message"])]


def summarize(events, pids, cutoff=None, registry=None, context=None):
    app = scoped(events, pids, cutoff)
    if registry is not None:
        from benign import partition
        triage, noise = partition(app, registry, context)
    else:
        triage, noise = app, []
    raw_execution = [event for event in app if is_execution(event)]
    execution = [event for event in triage if is_execution(event)]
    main = {}
    for event in execution:
        if "ActivityThread on dedicated pthread" in event["message"]:
            main[event["pid"]] = {"tid": event["tid"], "binding": event}
    processes = []
    for pid in sorted(pids):
        logs = [event for event in raw_execution if event["pid"] == pid]
        binding = main.get(pid)
        java = [event for event in logs if binding and event["tid"] == binding["tid"]]
        leader = [event for event in logs if event["tid"] == pid]
        processes.append(dict(pid=pid, java_main=binding, java_main_last=java[-1] if java else None,
                              leader_last=leader[-1] if leader else None, last_process_log=logs[-1] if logs else None,
                              sampled_thread_state="unknown: no thread stack/state snapshot in selected evidence"))
    return {
        "app_lines": len(app),
        "benign_noise": {str(item["event"]["line"]): item["signature_id"] for item in noise},
        "execution_lines": len(execution),
        "processes": processes,
        "fatal": matches(triage, FATAL.pattern),
        "caught_ssl": [event for event in execution if event["tag"].endswith("/SubscriptionRepository") and "IOException: canceled due to" in event["message"] and "SSLSockets" in event["message"]],
        "window_created": matches(triage, r"getOhNativeWindow: created self-drawing content child=|createSession: published process window target"),
        "swap_entered": matches(triage, r"\[G2\.14ax r2d (?:SwapDmgKHR|SwapBuffers) #\d+ pre-clear-sample\]"),
        "submit_success": matches(triage, r"(?:FlushBuffer|CommitAndReleaseBuffer) (?:result|rc)=0\b"),
        "lifecycle_callback": matches(triage, r"activityResumed \(first-frame\):"),
        "activity_finish": matches(triage, r"^finishActivity: OH TerminateAbility"),
        "activity_start": matches(triage, r"nativeStartAbility:|LaunchActivity transaction scheduled:"),
        "no_decor": matches(triage, r"mFinished=true mWindowAdded=false.*decorClass=null"),
        "exception_events": matches(triage, r"(?:^|\[stderr\] )(?:java\.[\w.]+(?:Exception|Error)|Caused by:|Suppressed:)|FAILED.*Exception|Exception:|failed: java\."),
        "network_errors": matches(triage, r"(?:SocketTimeoutException|UnknownHostException|Network is unreachable)"),
        "network_wait": matches(triage, r"(?:waiting for network callback|awaiting network response)"),
        "permission_wait": matches(triage, r"(?:waiting for (?:permission|dialog)|permission request pending|dialog callback pending)"),
        "frame_wait": matches(triage, r"(?:frame submission pending|waiting for first buffer|draw skipped: no buffer)"),
    }


def category(facts):
    if facts["caught_ssl"]:
        return "caught-exception"
    if facts["permission_wait"]:
        return "waiting-permission-or-dialog"
    if facts["network_wait"]:
        return "waiting-network"
    if facts["window_created"] and facts["frame_wait"] and not facts["submit_success"] and not facts["swap_entered"]:
        return "window-without-frame"
    return "other"


def eligibility(visual, alive, fatal):
    if visual not in {"white", "desktop"}:
        return "excluded-visual-" + visual
    if not alive:
        return "excluded-no-live-target-at-t20"
    if fatal:
        return "excluded-target-fatal-even-if-another-process-survives"
    return "selected"
