"""Bounded lifecycle reachability: prediction evidence, never execution proof."""

import re


STARTS = {"startActivity", "startActivityForResult", "startActivities", "startActivityIfNeeded"}
LIFECYCLE = [("onCreate", "(Landroid/os/Bundle;)V"), ("onResume", "()V"),
             ("onCreate", "(Landroid/os/Bundle;Landroid/os/PersistableBundle;)V")]
CALL = re.compile(r"(L[^ ;]+;)\.([^\s:]+):(\([^ ]*\).+)\s+// method@")


def qualified(package, name):
    return package + name if name.startswith(".") else name if "." in name else package + "." + name


def manifest(text):
    stack, roots = [], []
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        depth = len(line) - len(stripped)
        if stripped.startswith("E: "):
            while stack and stack[-1][0] >= depth:
                stack.pop()
            node = dict(tag=stripped.split()[1], attrs={}, children=[], line=number)
            (stack[-1][1]["children"] if stack else roots).append(node)
            stack.append((depth, node))
        elif stripped.startswith("A: ") and stack:
            field, value = stripped[3:].split("=", 1)
            name = field.split("(")[0].rsplit(":", 1)[-1]
            stack[-1][1]["attrs"][name] = value.split('"')[1] if value.startswith('"') else value.split()[0]
    root = next(node for node in roots if node["tag"] == "manifest")
    package = root["attrs"]["package"]
    application = next(node for node in root["children"] if node["tag"] == "application")
    activities, aliases, launchers = [], [], []
    for node in application["children"]:
        if node["tag"] not in {"activity", "activity-alias"}:
            continue
        name = qualified(package, node["attrs"]["name"])
        target = qualified(package, node["attrs"].get("targetActivity", node["attrs"]["name"]))
        enabled = node["attrs"].get("enabled", "true") not in {"false", "0", "0x00000000"}
        entry = dict(name=name, target=target, enabled=enabled, manifest_line=node["line"])
        (activities if node["tag"] == "activity" else aliases).append(entry)
        for child in node["children"]:
            if child["tag"] != "intent-filter":
                continue
            actions = {item["attrs"].get("name") for item in child["children"] if item["tag"] == "action"}
            categories = {item["attrs"].get("name") for item in child["children"] if item["tag"] == "category"}
            if "android.intent.action.MAIN" in actions and "android.intent.category.LAUNCHER" in categories:
                launchers.append(dict(entry, alias=node["tag"] == "activity-alias"))
    return dict(package=package, activities=activities, aliases=aliases, launchers=launchers)


def parse_dex(lines, dex, digest):
    classes, methods = {}, {}
    owner, name, current, in_methods = None, None, None, False
    for number, line in enumerate(lines, 1):
        if "Class descriptor  : '" in line:
            owner = line.split("'")[1]
            classes[owner] = None
            current, in_methods = None, False
        elif line.startswith("  Superclass"):
            classes[owner] = line.split("'")[1] if "'" in line else None
        elif line.startswith(("  Direct methods", "  Virtual methods")):
            in_methods = True
        elif in_methods and re.match(r"    #\d+\s+: \(in ", line):
            current, name = None, None
        elif in_methods and line.startswith("      name"):
            name = line.split("'")[1]
        elif in_methods and name and line.startswith("      type"):
            descriptor = line.split("'")[1]
            identifier = owner + "->" + name + descriptor
            current = dict(id=identifier, owner=owner, name=name, descriptor=descriptor, dex=dex, dex_sha256=digest,
                           code=False, calls=[], constants=[], branches=0)
            methods[identifier] = current
        elif current:
            instruction = re.search(r"\|([0-9a-f]{4,}): (.+)", line)
            if not instruction:
                continue
            current["code"] = True
            offset, body = instruction.groups()
            opcode = body.split()[0]
            if opcode.startswith(("if-", "packed-switch", "sparse-switch")):
                current["branches"] += 1
            call = CALL.search(body) if opcode.startswith("invoke-") else None
            if call:
                target_owner, target_name, target_descriptor = call.groups()
                current["calls"].append(dict(line=number, offset=offset, instruction=body, opcode=opcode,
                                             owner=target_owner, name=target_name, descriptor=target_descriptor,
                                             target=target_owner + "->" + target_name + target_descriptor))
            elif opcode == "const-class":
                current["constants"].append(dict(line=number, offset=offset, instruction=body))
    return classes, methods


def hierarchy(owner, classes):
    result = []
    while owner and owner not in result:
        result.append(owner)
        owner = classes.get(owner)
    return result


def resolve(owner, name, descriptor, classes, methods):
    for ancestor in hierarchy(owner, classes):
        identifier = ancestor + "->" + name + descriptor
        if identifier in methods:
            return identifier
    return None


def start_kind(call, ancestors, classes):
    context = call["owner"] in ancestors or call["owner"].startswith(("Landroid/", "Landroidx/"))
    if call["name"] in STARTS and context and "Landroid/content/Intent;" in call["descriptor"]:
        return "literal-startActivity"
    if call["name"] == "launch" and "Landroidx/activity/result/ActivityResultLauncher;" in hierarchy(call["owner"], classes):
        return "activity-result-launch"
    return None


def modern_input(witness, lines):
    site = witness["instruction"]
    operands = re.search(r"\{([^}]+)\}", site["instruction"])
    registers = [value.strip() for value in operands.group(1).split(",")] if operands else []
    if len(registers) < 2:
        return dict(kind="unknown")
    argument = registers[1]
    for entry in reversed(lines):
        if not site["line"] - 35 <= entry["line"] < site["line"]:
            continue
        match = re.search(r"\|[0-9a-f]+: ([\w/-]+) " + re.escape(argument) + r"(?:,|$)(.*)", entry["text"])
        if not match:
            continue
        opcode, tail = match.groups()
        if opcode.startswith(("if-", "return", "iput", "sput", "aput", "monitor", "check-cast", "packed-switch", "sparse-switch")):
            continue
        if opcode.startswith("const-string") and '"android.permission.' in tail:
            return dict(kind="permission-string-input", argument=argument, evidence=entry)
        if opcode == "new-instance" and "Landroid/content/Intent;" in tail:
            return dict(kind="intent-object-input", argument=argument, evidence=entry)
        return dict(kind="unknown", argument=argument, last_definition=entry)
    return dict(kind="unknown", argument=argument)


def inspect_activity(activity, classes, methods, max_depth=3):
    owner = "L" + activity.replace(".", "/") + ";"
    ancestors = hierarchy(owner, classes)
    if owner not in classes:
        return dict(activity=activity, status="unknown-missing-class", starts=[], finishes=[], methods=[], limits=["launcher target absent from selected DEX"])
    roots = [resolved for name, descriptor in LIFECYCLE if (resolved := resolve(owner, name, descriptor, classes, methods))]
    visited, starts, finishes, limits = {}, [], [], []
    pending = [(root, [root], 0) for root in roots]
    while pending:
        identifier, path, depth = pending.pop(0)
        if identifier in visited:
            continue
        method = methods[identifier]
        visited[identifier] = method
        if not method["code"]:
            limits.append("no bytecode: " + identifier)
            continue
        for call in method["calls"]:
            framework_owner = call["owner"].startswith(("Landroid/", "Landroidx/"))
            context_call = call["owner"] in ancestors or framework_owner
            witness = dict(method=identifier, dex=method["dex"], dex_sha256=method["dex_sha256"], path=path,
                           instruction=call, conditional=any(methods[step]["branches"] for step in path),
                           class_constants_in_caller=method["constants"])
            kind = start_kind(call, ancestors, classes)
            if kind:
                starts.append(dict(witness, kind=kind))
            if call["name"] in {"finish", "finishAffinity", "finishAndRemoveTask"} and context_call:
                finishes.append(witness)
            same_hierarchy = call["owner"] in ancestors
            if not same_hierarchy or (framework_owner and call["name"] not in {"onCreate", "onResume"}):
                continue
            target = resolve(call["owner"], call["name"], call["descriptor"], classes, methods)
            if target and target not in visited:
                next_depth = depth + (0 if (call["name"], call["descriptor"]) in LIFECYCLE else 1)
                if next_depth <= max_depth:
                    pending.append((target, path + [target], next_depth))
                else:
                    limits.append("helper-depth-limit: " + target)
    return dict(activity=activity, status="possible-lifecycle-trampoline" if starts else "no-lifecycle-start-found" if not limits else "unknown-bounded-analysis",
                starts=starts, finishes=finishes, methods=list(visited), limits=sorted(set(limits)), roots=roots,
                hierarchy=ancestors, scope="onCreate/onResume plus same-hierarchy synchronous helpers, helper-depth<=3; superclass lifecycle delegation free; callbacks and cross-class helpers not traversed")
