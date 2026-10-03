import re


def parse_blocks(text):
    blocks = {}
    matches = list(re.finditer(r"^\s*Class descriptor\s*:\s*'([^']+)'", text, re.MULTILINE))
    if not matches:
        raise ValueError("Nonempty DEX class output required")
    for index, match in enumerate(matches):
        descriptor = match.group(1)
        if descriptor in blocks:
            raise ValueError("Duplicate descriptor: " + descriptor)
        stop = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks[descriptor] = text[match.start():stop]
    return blocks


def contract(descriptor, text):
    parent = re.search(r"Superclass\s*:\s*'([^']*)'", text)
    if not parent:
        raise ValueError("Superclass missing: " + descriptor)
    interfaces, methods, section = [], [], ""
    method = None
    for line in text.splitlines():
        heading = re.match(r"\s*(Interfaces|Static fields|Instance fields|Direct methods|Virtual methods)\s*-", line)
        if heading:
            section = heading.group(1)
            continue
        interface = re.match(r"\s*#\d+\s*:\s*'(L[^']+;)'", line)
        if section == "Interfaces" and interface:
            interfaces.append(interface.group(1))
        if section in ["Direct methods", "Virtual methods"]:
            name = re.match(r"\s*name\s*:\s*'([^']+)'", line)
            signature = re.match(r"\s*type\s*:\s*'([^']+)'", line)
            access = re.match(r"\s*access\s*:\s*(.*)", line)
            if name:
                method = dict(name=name.group(1), section=section)
                methods.append(method)
            elif signature and method is not None:
                method["descriptor"] = signature.group(1)
                method["signature"] = descriptor + "->" + method["name"] + signature.group(1)
            elif access and method is not None:
                method["access"] = access.group(1)
    if any("signature" not in method for method in methods):
        raise ValueError("Incomplete method signature: " + descriptor)
    return dict(descriptor=descriptor, superclass=parent.group(1), interfaces=interfaces, methods=methods)
