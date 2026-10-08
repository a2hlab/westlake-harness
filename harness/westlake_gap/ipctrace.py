"""Binder IPC actually made by an app on real Android, from `am trace-ipc`.

The gap map's system-service rows come from the app's DEX: the `getSystemService` names and manager
calls its own code contains. Two things stay invisible to that read, and both decide whether a
Westlake / BridgeAOSP adapter has to answer:

1. which of those requested services the run actually reaches, and through which AIDL methods;
2. binders the *framework* calls on the app's behalf (window session, input, display, graphics
   stats, accessibility, ...) during bindApplication, first draw and input setup. No app code names
   them, so no scan of the app can list them, yet an in-process `IXxx` adapter must answer each.

`am trace-ipc start|stop --dump-file F` (frameworks/base ActivityManagerShellCommand) makes every
process record a stack for each Java `BinderProxy.transact` and dumps them grouped by process. The
`$Stub$Proxy.<method>` frame names the interface and method; the nearest non-framework frame names
the app call site, if any. Native binder clients (libgui, libbinder users in C++) do not go through
`BinderProxy` and are not in this record.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from .services import OH_ANALOG

SCHEMA_VERSION = "westlake-ipc-observed/v0.1"

PROCESS_RE = re.compile(r"^Traces for process:\s*(?P<process>\S+)\s*$")
COUNT_RE = re.compile(r"^Count:\s*(?P<count>\d+)\s*$")
FRAME_RE = re.compile(r"^\s*at\s+(?P<method>[\w$.<>]+)\((?P<where>[^)]*)\)\s*$")
PROXY_RE = re.compile(r"^(?P<interface>[\w.$]+)\$Stub\$Proxy\.(?P<method>[\w$<>]+)$")

# Code that ships in the platform rather than in the APK. Everything else (androidx, kotlin, the app's
# own and its SDKs') counts as app code when deciding who made the call.
FRAMEWORK_PREFIXES = (
    "android.", "com.android.", "java.", "javax.", "jdk.", "sun.", "dalvik.", "libcore.",
    "org.apache.harmony.", "org.json.", "org.xmlpull.", "com.google.android.collect.",
)

# AIDL interface -> the ServiceManager name its proxy is fetched under (AOSP 16; Context.*_SERVICE).
# Interfaces handed out by another service (a window session, an activity client controller) are
# attributed to the service that hands them out. Curated; an unknown interface keeps service=None.
INTERFACE_SERVICE: dict[str, str] = {
    "android.app.IActivityManager": "activity",
    "android.app.IActivityTaskManager": "activity_task",
    "android.app.IActivityClientController": "activity_task",
    "android.content.pm.IPackageManager": "package",
    "android.content.pm.IPackageInstaller": "package",
    "android.permission.IPermissionManager": "permissionmgr",
    "android.view.IWindowManager": "window",
    "android.view.IWindowSession": "window",
    "android.hardware.display.IDisplayManager": "display",
    "android.hardware.input.IInputManager": "input",
    "com.android.internal.view.IInputMethodManager": "input_method",
    "android.view.accessibility.IAccessibilityManager": "accessibility",
    "android.view.autofill.IAutoFillManager": "autofill",
    "android.view.contentcapture.IContentCaptureManager": "content_capture",
    "android.app.IUiModeManager": "uimode",
    "android.os.IUserManager": "user",
    "android.os.storage.IStorageManager": "mount",
    "android.net.IConnectivityManager": "connectivity",
    "android.net.wifi.IWifiManager": "wifi",
    "com.android.internal.app.IAppOpsService": "appops",
    "android.view.IGraphicsStats": "graphicsstats",
    "com.android.internal.app.IVoiceInteractionManagerService": "voiceinteraction",
    "com.android.internal.protolog.IProtoLogConfigurationService": "protolog_configuration",
    "android.os.IPowerManager": "power",
    "android.os.IThermalService": "thermalservice",
    "android.os.IDeviceIdleController": "deviceidle",
    "android.os.IVibratorManagerService": "vibrator_manager",
    "android.media.IAudioService": "audio",
    "android.media.session.ISessionManager": "media_session",
    "android.app.INotificationManager": "notification",
    "android.content.IClipboard": "clipboard",
    "android.content.IContentService": "content",
    "android.location.ILocationManager": "location",
    "android.app.job.IJobScheduler": "jobscheduler",
    "android.app.IAlarmManager": "alarm",
    "android.app.ISearchManager": "search",
    "android.app.ILocaleManager": "locale",
    "android.app.IWallpaperManager": "wallpaper",
    "android.app.IGameManagerService": "game",
    "android.app.usage.IUsageStatsManager": "usagestats",
    "android.hardware.ISensorPrivacyManager": "sensor_privacy",
    "com.android.internal.telephony.ITelephony": "phone",
    "com.android.internal.telephony.ITelephonyRegistry": "telephony.registry",
    "com.android.internal.statusbar.IStatusBarService": "statusbar",
    "android.os.IServiceManager": "servicemanager",
}

# Proxies written by hand instead of generated from AIDL: class -> the interface they speak.
HANDWRITTEN_PROXIES = {
    "android.content.ContentProviderProxy": "android.content.IContentProvider",
}


def parse_dump(text: str) -> dict[str, list[dict[str, Any]]]:
    """Group one `am trace-ipc` dump into {process: [{count, frames}]}; frames are innermost first."""
    processes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    process: str | None = None
    current: dict[str, Any] | None = None
    for raw in text.splitlines():
        line = raw.rstrip("\r")
        match = PROCESS_RE.match(line)
        if match:
            process = match.group("process")
            current = None
            continue
        match = COUNT_RE.match(line)
        if match and process is not None:
            current = {"count": int(match.group("count")), "frames": []}
            processes[process].append(current)
            continue
        match = FRAME_RE.match(line)
        if match and current is not None:
            current["frames"].append((match.group("method"), match.group("where")))
    return dict(processes)


def is_framework(method: str) -> bool:
    return method.startswith(FRAMEWORK_PREFIXES)


def classify_trace(frames: list[tuple[str, str]]) -> dict[str, Any] | None:
    """The proxy call a stack records and who made it; None if the stack has no AIDL proxy frame."""
    for index, (method, _where) in enumerate(frames):
        match = PROXY_RE.match(method)
        owner, _, name = method.rpartition(".")
        if match:
            interface, called = match.group("interface"), match.group("method")
        elif owner in HANDWRITTEN_PROXIES:
            interface, called = HANDWRITTEN_PROXIES[owner], name
        else:
            continue
        service = INTERFACE_SERVICE.get(interface)
        if interface == "android.content.IContentProvider":
            # Settings.Global/Secure/System and DeviceConfig reads go to the settings provider, which
            # an OH port has to back from its own settings data; any other authority is app-level.
            settings = any(m.startswith("android.provider.Settings") for m, _ in frames[index + 1:])
            service = "settings-provider" if settings else "content-provider"
        caller = next(((m, w) for m, w in frames[index + 1:] if not is_framework(m)), None)
        entry = next(((m, w) for m, w in frames[index + 1:]
                      if not m.startswith(("android.os.", "java.", "dalvik.", "com.android.internal.os."))
                      and "$Stub$Proxy" not in m), None)
        return {
            "interface": interface,
            "method": called,
            "service": service,
            "app_frame": f"{caller[0]}({caller[1]})" if caller else None,
            "framework_entry": f"{entry[0]}({entry[1]})" if entry else None,
        }
    return None


def observe(text: str, package: str, *, scenario: str = "", device: str = "") -> dict[str, Any]:
    """Every binder call one app process made during the recorded window, grouped by service and method."""
    processes = parse_dump(text)
    traces = processes.get(package, [])
    calls: dict[tuple[str, str], dict[str, Any]] = {}
    unparsed = 0
    for trace in traces:
        call = classify_trace(trace["frames"])
        if call is None:
            unparsed += trace["count"]
            continue
        key = (call["interface"], call["method"], call["service"])
        row = calls.setdefault(key, {
            "interface": call["interface"],
            "method": call["method"],
            "service": call["service"],
            "count": 0,
            "app_frames": set(),
            "framework_entries": set(),
        })
        row["count"] += trace["count"]
        if call["app_frame"]:
            row["app_frames"].add(call["app_frame"])
        elif call["framework_entry"]:
            row["framework_entries"].add(call["framework_entry"])

    services: dict[str, dict[str, Any]] = {}
    for row in calls.values():
        name = row["service"] or f"?{row['interface']}"
        svc = services.setdefault(name, {
            "service": name,
            "oh_analog": OH_ANALOG.get(name),
            "calls": 0,
            "methods": [],
            "app_initiated": False,
        })
        svc["calls"] += row["count"]
        svc["methods"].append(f"{row['interface'].rsplit('.', 1)[-1]}.{row['method']}")
        svc["app_initiated"] = svc["app_initiated"] or bool(row["app_frames"])

    rows = []
    for row in sorted(calls.values(), key=lambda r: (-r["count"], r["interface"], r["method"])):
        rows.append({
            **{k: row[k] for k in ("interface", "method", "service", "count")},
            "app_frames": sorted(row["app_frames"]),
            "framework_entries": sorted(row["framework_entries"])[:3],
        })
    for svc in services.values():
        svc["methods"] = sorted(set(svc["methods"]))
    return {
        "schema": SCHEMA_VERSION,
        "package": package,
        "scenario": scenario,
        "device": device,
        "processes_in_dump": sorted(processes),
        "summary": {
            "binder_calls": sum(r["count"] for r in rows),
            "distinct_methods": len(rows),
            "services": len(services),
            "app_initiated_services": sum(1 for s in services.values() if s["app_initiated"]),
            "unparsed_traces": unparsed,
        },
        "services": sorted(services.values(), key=lambda s: (-s["calls"], s["service"])),
        "calls": rows,
    }


# Managers whose binder is spoken from native code (SystemSensorManager -> libsensor -> sensorservice):
# their traffic never passes BinderProxy, so a Java IPC trace cannot show it either way.
NATIVE_CLIENT_SERVICES = {"sensor", "sensorservice"}

# PackageManager API name -> the IPackageManager method behind it, where the two differ (AOSP 16).
PM_AIDL_ALIAS = {
    "queryBroadcastReceivers": "queryIntentReceivers",
}


def join_gap_map(observed: dict[str, Any], gap_map: dict[str, Any]) -> dict[str, Any]:
    """Which rows of a static gap map the run reached, and which binders it used that no row names.

    `svc:<binder>` rows are reached when that binder was called; `pm:call:<method>` rows when the
    IPackageManager method behind that PackageManager call was.
    """
    seen = {s["service"]: s for s in observed["services"]}
    pm_methods = {c["method"] for c in observed["calls"] if c["interface"] == "android.content.pm.IPackageManager"}
    reached, not_reached, not_observable = [], [], []
    covered: set[str] = set()
    for row in sorted(gap_map.get("rows", []), key=lambda r: str(r.get("id", ""))):
        rid = str(row.get("id", ""))
        entry = {"id": rid, "effort": row.get("effort"), "app_calls": row.get("app_calls", [])}
        if rid.startswith("svc:"):
            name = rid[4:]
            covered.add(name)
            if name in seen:
                observed_names = {m.rsplit(".", 1)[-1] for m in seen[name]["methods"]}
                reached.append({**entry, "observed_methods": seen[name]["methods"], "observed_calls": seen[name]["calls"],
                                "app_calls_observed": sorted(set(entry["app_calls"]) & observed_names)})
            elif "needs binder(s) []" in str(row.get("aosp_contract", "")) or name in NATIVE_CLIENT_SERVICES:
                not_observable.append(entry)   # binderless, or a native binder client: invisible to trace-ipc
            else:
                not_reached.append(entry)
        elif rid.startswith("pm:call:"):
            covered.add("package")
            api = rid[len("pm:call:"):]
            aidl = PM_AIDL_ALIAS.get(api, api)
            if aidl in pm_methods:
                reached.append({**entry, "observed_methods": [f"IPackageManager.{aidl}"]})
            else:
                not_reached.append(entry)
    unmapped = [
        {k: s[k] for k in ("service", "oh_analog", "calls", "methods", "app_initiated")}
        for name, s in sorted(seen.items())
        if name not in covered and name not in {"servicemanager", "content-provider"}
    ]
    rows_considered = len(reached) + len(not_reached) + len(not_observable)
    return {
        "gap_map_app": gap_map.get("app", {}),
        "reached": reached,
        "not_reached": not_reached,
        "not_observable": not_observable,
        "observed_but_not_in_map": unmapped,
        "summary": {
            "rows_considered": rows_considered,
            "svc_rows": sum(1 for r in reached + not_reached + not_observable if r["id"].startswith("svc:")),
            "pm_call_rows": sum(1 for r in reached + not_reached if r["id"].startswith("pm:call:")),
            "reached": len(reached),
            "not_reached": len(not_reached),
            "not_observable": len(not_observable),
            "observed_but_not_in_map": len(unmapped),
        },
    }


def markdown(observed: dict[str, Any], joined: dict[str, Any] | None = None) -> str:
    s = observed["summary"]
    out = [
        f"# Binder IPC observed: `{observed['package']}`",
        "",
        f"Scenario: {observed['scenario'] or 'unspecified'}. Device: {observed['device'] or 'unspecified'}.",
        "",
        f"{s['binder_calls']} Java binder calls, {s['distinct_methods']} distinct AIDL methods, "
        f"{s['services']} services ({s['app_initiated_services']} with an app frame on some call; "
        f"the rest the framework called on the app's behalf).",
        "",
        "| Service | OH analog | Calls | App frame | Methods |",
        "|---|---|---:|---|---|",
    ]
    for svc in observed["services"]:
        out.append(
            f"| `{svc['service']}` | {svc['oh_analog'] or ''} | {svc['calls']} | "
            f"{'yes' if svc['app_initiated'] else 'framework only'} | {', '.join(svc['methods'])} |"
        )
    if joined:
        j = joined["summary"]
        out += [
            "",
            "## Against the static gap map",
            "",
            f"{j['reached']} of {j['rows_considered']} rows reached on this run "
            f"({j['svc_rows']} `svc:` + {j['pm_call_rows']} `pm:call:`); "
            f"{j['observed_but_not_in_map']} services used that no row names.",
            "",
            "Reached: " + (", ".join(f"`{r['id']}`" for r in joined["reached"]) or "none"),
            "",
            "Not reached on this run: " + (", ".join(f"`{r['id']}`" for r in joined["not_reached"]) or "none"),
            "",
            "Not observable by a Java IPC trace (binderless or native client): "
            + (", ".join(f"`{r['id']}`" for r in joined["not_observable"]) or "none"),
            "",
            "Used but not in the map (framework-implied): "
            + (", ".join(f"`{u['service']}`" for u in joined["observed_but_not_in_map"]) or "none"),
        ]
    return "\n".join(out) + "\n"
