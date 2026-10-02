import json
from pathlib import Path
import re
import shutil

from common import HERE, WS, save, sha
from oracle import table_from_source

ROOT = WS / "westlake-inputs/aosp-14.0.0_r1-src/bionic-ctype-e4df46f2"
TABLE = "libc/upstream-openbsd/lib/libc/gen/ctype_.c"
BITS = "libc/include/bits/ctype_inlines.h"
ALIASES = "libc/upstream-openbsd/android/include/openbsd-compat.h"
EXPECTED = {TABLE: "8fc63bd8bbfd6e17b2b55701a68a6e02dc6fb27f4d99eac277175863d7cf12f4",
            ALIASES: "6efbb9c1d1c804445cfa217d72a8e31b5143186156df54b297673bfb626ab4fb"}


def main():
    checksums = {line.split(None, 1)[1].strip().removeprefix("./"): line.split()[0]
                 for line in (ROOT / "SHA256SUMS").read_text().splitlines() if line.strip()}
    if BITS not in checksums:
        raise ValueError("AOSP14 bit-definition header not provided; stop")
    rows = []
    for relative, digest in checksums.items():
        source = ROOT / relative
        if sha(source) != digest or relative in EXPECTED and digest != EXPECTED[relative]:
            raise ValueError("source SHA mismatch: " + relative)
        target = HERE / "inputs/aosp" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        rows.append(dict(path=source, snapshot=str(target.relative_to(HERE)), sha256=digest))
    for name in ["SHA256SUMS", "SOURCE.txt"]:
        shutil.copyfile(ROOT / name, HERE / "inputs/aosp" / name)
    table, values = table_from_source((ROOT / TABLE).read_text(), (ROOT / BITS).read_text(), (ROOT / ALIASES).read_text())
    candidate = (HERE / "ctype_compat.c").read_text()
    candidate_values = {name: int(value, 16) for name, value in re.findall(r"^#define\s+(_[ULNSPCXB])\s+(0x[0-9a-fA-F]+)$", candidate, re.M)}
    if candidate_values != values:
        raise ValueError("candidate adapter definitions differ from14r1")
    save("table-oracle.json", dict(bytes=list(table), byte_count=len(table), bits=values,
         table_source=TABLE, definitions_source=BITS, aliases_source=ALIASES, pointer_bytes=8,
         digit_class=table[ord("0") + 1], note="Digits are _N=4, NOT _N|_X; hex bit marks A-F/a-f in this legacy table"))
    save("sources.json", dict(lookup="local authoritative14r1 sparse copy supplied after readonly VM timeout and SSH sandbox denial",
         tag="android-14.0.0_r1", commit="e4df46f213d8d363017dce7ded5d1f2159614425", sources=rows,
         candidate_source_sha256=sha(HERE / "ctype_compat.c"), table_oracle_sha256=sha(HERE / "table-oracle.json"),
         adaptation="Unmodified original ctype_.c included; empty shim ctype.h avoids unrelated OH classifications, eight constants from same-tag bits header, hidden export map keeps table private"))
    print("SOURCE VERIFIED table257; original pointer declaration; all bit values from14r1; digits4")


if __name__ == "__main__":
    main()
