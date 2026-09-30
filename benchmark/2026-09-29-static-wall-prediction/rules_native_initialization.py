"""Bounded source-order checks, not a C++ compiler or a runtime-success proof."""
from collections import defaultdict
import re


TOKEN = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_]\w*|\d+|::|->|==|!=|&&|\|\||[^\s]', re.S)
CONTROL = {"if", "for", "while", "switch", "catch", "sizeof", "decltype"}
FAMILIES = ("noload-before-namespace-mapping", "jni-cache-before-native-registration")


class Source:
    def __init__(self, name, text, first_line=1):
        self.name = name
        self.text = text
        self.first_line = first_line
        self.tokens = [(match.group(), match.start()) for match in TOKEN.finditer(text)
                       if not match.group().startswith(("//", "/*"))]
        self.pairs = {}
        stack = []
        for index, (token, _) in enumerate(self.tokens):
            if token in {"(", "{", "["}:
                stack.append((token, index))
            elif token in {")", "}", "]"}:
                if not stack or stack[-1][0] != {")": "(", "}": "{", "]": "["}[token]:
                    raise ValueError(f"unbalanced source: {name}")
                _, opening = stack.pop()
                self.pairs[opening] = index
        if stack:
            raise ValueError(f"unbalanced source: {name}")
        self.constants = {}
        for index in range(2, len(self.tokens)):
            if self.tokens[index][0].startswith('"') and self.tokens[index - 1][0] == "=":
                self.constants[self.tokens[index - 2][0]] = self.tokens[index][0][1:-1]
        self.tables = {}
        for index, (token, _) in enumerate(self.tokens[:-3]):
            if token != "JNINativeMethod" or self.tokens[index + 2][0] != "[":
                continue
            closing = self.pairs[index + 2]
            if self.expression(closing + 1, closing + 3) != "={":
                continue
            end = self.pairs[closing + 2]
            methods = []
            for row in range(closing + 3, end - 3):
                if self.tokens[row][0] == "{" and self.tokens[row + 2][0] == ",":
                    method, descriptor = self.tokens[row + 1][0], self.tokens[row + 3][0]
                    if method.startswith('"') and descriptor.startswith('"'):
                        methods.append((method[1:-1], descriptor[1:-1]))
            self.tables[self.tokens[index + 1][0]] = methods
        self.functions = {}
        for index, (token, _) in enumerate(self.tokens[:-1]):
            if not re.fullmatch(r"[A-Za-z_]\w*", token) or token in CONTROL or self.tokens[index + 1][0] != "(":
                continue
            closing = self.pairs[index + 1]
            if closing + 1 < len(self.tokens) and self.tokens[closing + 1][0] == "{":
                if token in self.functions:
                    raise ValueError(f"ambiguous overloaded function: {name}:{token}")
                self.functions[token] = (closing + 2, self.pairs[closing + 1])

    def witness(self, index):
        offset = self.tokens[index][1]
        line = self.text.count("\n", 0, offset) + 1
        return dict(source=self.name, line=line + self.first_line - 1, text=self.text.splitlines()[line - 1].strip())

    def expression(self, start, end):
        return "".join(token for token, _ in self.tokens[start:end])

    def literal(self, expression):
        if re.fullmatch(r'"(?:\\.|[^"\\])*"', expression):
            return expression[1:-1]
        return self.constants.get(expression.split("::")[-1])

    def assigned(self, index):
        for cursor in range(index - 1, max(-1, index - 7), -1):
            if self.tokens[cursor][0] in {";", "{", "}"}:
                break
            if self.tokens[cursor][0] == "=" and cursor > 0:
                return self.tokens[cursor - 1][0]
        return None

    def calls(self, start, end):
        for index in range(start, end - 1):
            name = self.tokens[index][0]
            if not re.fullmatch(r"[A-Za-z_]\w*", name) or name in CONTROL or self.tokens[index + 1][0] != "(":
                continue
            closing = self.pairs[index + 1]
            arguments, beginning, cursor = [], index + 2, index + 2
            while cursor < closing:
                token = self.tokens[cursor][0]
                if token == ",":
                    arguments.append(self.expression(beginning, cursor))
                    beginning = cursor + 1
                elif token in {"(", "[", "{"}:
                    cursor = self.pairs[cursor]
                cursor += 1
            if beginning < closing:
                arguments.append(self.expression(beginning, closing))
            yield dict(name=name, args=arguments, index=index, end=closing)

    def blocks(self, index):
        return tuple(opening for opening, closing in self.pairs.items()
                     if self.tokens[opening][0] == "{" and opening < index < closing)


def namespace_walls(source):
    findings, unknown, checked = [], [], []
    for function, (start, end) in source.functions.items():
        created, loads = {}, []
        for call in source.calls(start, end):
            name, args, index = call["name"], call["args"], call["index"]
            if name in {"dlns_create", "dlns_create2"} and args:
                created[args[0]] = index
            if name not in {"dlopen", "dlopen_ns"} or len(args) < 2:
                continue
            namespace, target, flags = (args[0], args[1], args[2]) if name == "dlopen_ns" and len(args) == 3 else ("default", args[0], args[1])
            library = source.literal(target)
            flag_tokens = {match.group() for match in TOKEN.finditer(flags)}
            if "RTLD_NOLOAD" not in flag_tokens:
                names = {token for token in flag_tokens if re.fullmatch(r"[A-Za-z_]\w*", token)}
                if names <= {"RTLD_NOW", "RTLD_LAZY", "RTLD_LOCAL", "RTLD_GLOBAL", "RTLD_NODELETE"} and names & {"RTLD_NOW", "RTLD_LAZY"}:
                    loads.append((namespace, library, call))
                continue
            witness = dict(function=function, namespace=namespace, library=library,
                           target_expression=target, evidence=source.witness(index))
            if namespace not in created or library is None:
                unknown.append(dict(**witness, reason="fresh namespace or literal target not established"))
                continue
            mapping = None
            for prior_namespace, prior_library, prior in loads:
                if prior_namespace != namespace or prior_library != library or prior["index"] < created[namespace]:
                    continue
                prior_blocks, current_blocks = source.blocks(prior["index"]), source.blocks(index)
                if current_blocks[:len(prior_blocks)] != prior_blocks:
                    continue
                assigned = source.assigned(prior["index"])
                after = source.expression(prior["end"] + 1, index)
                if assigned and re.search(r"if\((?:!" + re.escape(assigned) + r"|" + re.escape(assigned) + r"==(?:NULL|nullptr|0))\)\{?return", after) and "dlclose(" not in after:
                    mapping = source.witness(prior["index"])
            if mapping:
                checked.append(dict(**witness, status="prior-guarded-load", mapping=mapping))
            else:
                findings.append(dict(**witness, family=FAMILIES[0], verdict="static-risk",
                                     namespace_creation=source.witness(created[namespace]),
                                     reason="NOLOAD cannot establish a first local mapping; no dominating guarded same-namespace load found"))
    return dict(findings=findings, unknown=unknown, checked=checked)


def java_native_requirements(classes, root):
    requirements, unknown = [], set()
    initialized, active = set(), set()

    def initialize(owner, chain):
        if owner in initialized:
            return
        initialized.add(owner)
        if owner not in classes:
            unknown.add(owner)
            return
        parent = classes[owner].get("super")
        if parent:
            initialize(parent, chain + [dict(class_name=owner, edge="super", target=parent)])
        method(owner, "<clinit>", "()V", chain)

    def method(owner, name, descriptor, chain):
        key = (owner, name, descriptor)
        if key in active:
            return
        active.add(key)
        if owner not in classes:
            unknown.add(owner)
            return
        candidate = next((item for item in classes[owner]["methods"]
                          if (item["name"], item["descriptor"]) == (name, descriptor)), None)
        if candidate is None:
            if name != "<clinit>":
                unknown.add("->".join(key))
            return
        if candidate["native"]:
            requirements.append(dict(class_name=owner, method=name, descriptor=descriptor, chain=chain))
            return
        for instruction in candidate["instructions"]:
            opcode, output = instruction["opcode"], instruction["output"]
            step = dict(class_name=owner, method=name, descriptor=descriptor, **instruction)
            if opcode == "new-instance":
                target = re.search(r"L([^;]+);", output)
                if target:
                    initialize(target[1], chain + [step])
            elif opcode.startswith("invoke-"):
                target = re.search(r"L([^;]+);->([^\s(]+)(\(.*)", output)
                if target:
                    callee, called, signature = target.groups()
                    if opcode.startswith("invoke-static"):
                        initialize(callee, chain + [step])
                    method(callee, called, signature.replace(" ", ""), chain + [step])

    initialize(root, [])
    return requirements, sorted(unknown)


def jni_order_walls(sources, entry_source, entry_function, classes):
    by_name = defaultdict(list)
    for source in sources.values():
        for name in source.functions:
            by_name[name].append(source)
    if entry_source not in sources or entry_function not in sources[entry_source].functions:
        raise ValueError("native entry function not found")
    registrations, lookups, unknown_calls = {}, [], set()
    active = set()
    sequence = 0

    def walk(source, function, stack):
        nonlocal sequence
        identity = (source.name, function)
        if identity in active:
            unknown_calls.add("recursive:" + function)
            return
        active.add(identity)
        class_vars = {}
        start, end = source.functions[function]
        for call in source.calls(start, end):
            name, args, index = call["name"], call["args"], call["index"]
            sequence += 1
            evidence = source.witness(index)
            trace = stack + [dict(function=function, **evidence)]
            if name == "FindClass" and args:
                assigned = source.assigned(index)
                if assigned:
                    class_vars[assigned] = source.literal(args[0])
            elif name in {"registerNativeMethods", "RegisterNatives", "jniRegisterNativeMethods"}:
                class_arg = args[1] if name != "RegisterNatives" and len(args) > 1 else (args[0] if args else "")
                owner = source.literal(class_arg) or class_vars.get(class_arg)
                table_arg = args[1] if name == "RegisterNatives" and len(args) > 1 else (args[2] if len(args) > 2 else "")
                methods = source.tables.get(table_arg.split("::")[-1])
                if owner and methods is not None:
                    for method, descriptor in methods:
                        registrations.setdefault((owner, method, descriptor), dict(sequence=sequence, evidence=evidence, trace=trace))
                else:
                    unknown_calls.add("unresolved-registration-or-table:" + class_arg + ":" + table_arg)
            elif name in {"GetFieldID", "GetStaticFieldID", "GetMethodID", "GetStaticMethodID"} and args:
                owner = class_vars.get(args[0])
                lookups.append(dict(class_name=owner, operation=name, sequence=sequence,
                                    evidence=evidence, trace=trace))
            else:
                candidates = [source] if name in source.functions else by_name.get(name, [])
                if len(candidates) == 1:
                    walk(candidates[0], name, trace)
                elif name not in CONTROL:
                    unknown_calls.add(name)
        active.remove(identity)

    walk(sources[entry_source], entry_function, [])
    findings, unknown, checked = [], [], []
    for lookup in lookups:
        owner = lookup["class_name"]
        if not owner:
            unknown.append(dict(**lookup, reason="JNI class variable not resolved"))
            continue
        requirements, missing = java_native_requirements(classes, owner)
        if missing:
            unknown.append(dict(**lookup, reason="incomplete DEX initialization closure", missing=missing))
        for requirement in requirements:
            registration = registrations.get((requirement["class_name"], requirement["method"], requirement["descriptor"]))
            row = dict(cache=lookup, dependency=requirement, registration=registration)
            if registration and registration["sequence"] < lookup["sequence"]:
                checked.append(dict(**row, status="registration-call-precedes-cache"))
            elif registration:
                findings.append(dict(**row, family=FAMILIES[1], verdict="static-risk",
                                     reason="cache lookup can initialize a class whose native registration call occurs later"))
            else:
                unknown.append(dict(**row, reason="required native registration not found in bounded call graph"))
    return dict(findings=findings, checked=checked, unknown=unknown,
                unresolved_calls=sorted(unknown_calls), coverage="bounded-source-order-not-runtime-success")
