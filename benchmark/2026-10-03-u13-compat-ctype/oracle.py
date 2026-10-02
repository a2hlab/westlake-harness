import re


def table_from_source(source, bits, aliases):
    definitions = dict(re.findall(r"^#define\s+(_CTYPE_[A-Z])\s+(0x[0-9a-fA-F]+)\s*$", bits, re.M))
    mapping = dict(re.findall(r"^#define\s+(_[ULNSPCXB])\s+(_CTYPE_[A-Z])\s*$", aliases, re.M))
    values = {name: int(definitions[target], 16) for name, target in mapping.items()}
    if len(values) != 8:
        raise ValueError("incomplete source bit definitions")
    body = re.search(r"const char _C_ctype_\[1 \+ CTYPE_NUM_CHARS\] = \{(.*?)\};", source, re.S)
    if not body or "const char *_ctype_ = _C_ctype_;" not in source:
        raise ValueError("original pointer/table layout mismatch")
    text = re.sub(r"/\*.*?\*/", "", body.group(1), flags=re.S).replace("(char)", "")
    result = []
    for expression in text.split(","):
        expression = expression.strip()
        if not expression:
            continue
        value = 0
        for token in expression.split("|"):
            token = token.strip()
            if token == "0":
                continue
            if token not in values:
                raise ValueError("unexpected table token: " + token)
            value |= values[token]
        result.append(value)
    if len(result) != 257 or result[0] != 0 or any(result[129:]):
        raise ValueError("wrong table extent or high-byte semantics")
    return bytes(result), values
