"""Post-hoc U4 requirements and runtime witnesses, independent of app keys."""
import re

from scan_apps import INVOKE

FAMILIES = (
    "native-owner-configuration",
    "egl-jni-field-contract",
    "native-transitive-symbol",
    "renderthread-signal",
)
LOG = re.compile(r"^\S+ \S+\s+(\d+)\s+(\d+)\s+[A-Z]\s+(.*)$")


def inspect_method(method, dex, insns):
    rows = []
    for offset, line, instruction in insns:
        match = INVOKE.search(instruction)
        if not match:
            continue
        _, _, owner, name, signature = match.groups()
        family = None
        if ((owner in {"java/lang/System", "java/lang/Runtime"} and
             name in {"load", "loadLibrary"}) or
            (owner.startswith(("com/facebook/soloader/", "io/flutter/embedding/engine/")) and
             name in {"loadLibrary", "init", "ensureInitializationComplete", "startInitialization"})):
            family = FAMILIES[0]
        elif owner in {"com/google/android/gles_jni/EGLImpl", "javax/microedition/khronos/egl/EGL10"}:
            family = FAMILIES[1]
        if family:
            rows.append(dict(family=family, method=method, dex=dex, offset=offset,
                             line=line, instruction=instruction,
                             target=owner + "." + name + signature,
                             verdict="conditional-runtime-requirement",
                             startup_reachable="unknown", active_wall="unknown"))
    return rows


def native_requirements(library, needed, undefined_symbols):
    return dict(library=library, family=FAMILIES[2], needed=sorted(needed),
                undefined_symbols=sorted(undefined_symbols),
                requirement="Check the consumer's effective namespace and transitive symbol closure, not package presence",
                active_wall="unknown", resolution="requires-runtime-witness")


def target_rows(lines, package):
    bindings = []
    for number, text in enumerate(lines, 1):
        match = LOG.match(text)
        binding = re.search(r"bindApplication: bundle=(\S+) process=(\S+) pid=(\d+)", text)
        if match and binding and binding[1] == package and binding[3] == match[1]:
            bindings.append(dict(line=number, pid=match[1], text=text))
    starts = {row["pid"]: row["line"] for row in bindings}
    rows = []
    for number, text in enumerate(lines, 1):
        match = LOG.match(text)
        if match and match[1] in starts and number >= starts[match[1]]:
            rows.append(dict(line=number, pid=match[1], tid=match[2], text=text))
    return bindings, rows


def runtime_walls(rows):
    found = {}
    for index, row in enumerate(rows):
        text = row["text"]
        family = None
        context = []
        if re.search(r"(?:UnsatisfiedLinkError: )?Flutter default-owner namespace configuration failed: [1-9]\d*\b", text):
            family = FAMILIES[0]
        elif "JNI DETECTED ERROR IN APPLICATION: fid == null" in text:
            context = [later for later in rows[index + 1:index + 9]
                       if (later["pid"], later["tid"]) == (row["pid"], row["tid"])
                       and "from boolean com.google.android.gles_jni.EGLImpl.eglInitialize(" in later["text"]]
            if context:
                family = FAMILIES[1]
        elif re.search(r"Error relocating \S+: \S+: symbol not found", text):
            family = FAMILIES[2]
        elif "DFX_SignalHandler" in text and "signo(11)" in text and "threadName(RenderThread)" in text:
            family = FAMILIES[3]
        if family and family not in found:
            found[family] = dict(family=family, evidence=row, context=context[:1],
                                 verdict="observed-runtime-wall", prospective=False)
    return list(found.values())
