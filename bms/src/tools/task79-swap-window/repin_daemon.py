#!/usr/bin/env python3
"""
appspawn-x.real 换钉器 —— runtime 换装必伴，漏此步 = daemon exit(1)
"exact Android runtime admission failed"，startReg 永不执行（runbook 永入纪律）。

daemon 的 .rodata 里把 liboh_android_runtime.so 的 sha256(64 hex) 与 BuildID(40 hex)
各钉两份（Load/Verify 双函数 -D 宏注入族）。两者都是纯 ASCII 十六进制串，
**等长替换 ⟹ 零偏移漂移**，不需要重定位。

a14 (0f4616fd, 136,040B) 实测钉位：
    runtime sha256  @ 0x2b0a, 0x2bde
    runtime BuildID @ 0x2b4b, 0x2c1f

本脚本不写死偏移——按旧值全文搜索替换，并强制校验「命中数必须 ≥1 且新旧等长」，
这样换到别代 daemon 也能用。

用法:
  repin_daemon.py <daemon 输入> <daemon 输出> \
      --old-sha <64hex> --new-sha <64hex> \
      --old-build <40hex> --new-build <40hex>
"""
import argparse
import hashlib
import sys


def replace_all(buf: bytearray, old: bytes, new: bytes, label: str) -> int:
    if len(old) != len(new):
        raise SystemExit(f"FAIL: {label} 新旧不等长 ({len(old)} vs {len(new)})，"
                         f"等长替换纪律不满足")
    hits, i = [], buf.find(old)
    while i >= 0:
        hits.append(i)
        i = buf.find(old, i + 1)
    if not hits:
        raise SystemExit(f"FAIL: {label} 旧值在件内零命中 —— 钉位假设不成立，中止")
    for o in hits:
        buf[o:o + len(old)] = new
    print(f"  {label}: {len(hits)} 处已换 -> {[hex(o) for o in hits]}")
    return len(hits)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("--old-sha", required=True)
    p.add_argument("--new-sha", required=True)
    p.add_argument("--old-build", required=True)
    p.add_argument("--new-build", required=True)
    a = p.parse_args()

    for name, v, n in (("old-sha", a.old_sha, 64), ("new-sha", a.new_sha, 64),
                       ("old-build", a.old_build, 40), ("new-build", a.new_build, 40)):
        if len(v) != n or any(c not in "0123456789abcdef" for c in v.lower()):
            raise SystemExit(f"FAIL: --{name} 必须是 {n} 位小写十六进制，得到 {v!r}")

    raw = open(a.src, "rb").read()
    buf = bytearray(raw)
    print(f"输入 {a.src} ({len(raw)} B) sha256={hashlib.sha256(raw).hexdigest()}")

    replace_all(buf, a.old_sha.encode(), a.new_sha.encode(), "runtime sha256")
    replace_all(buf, a.old_build.encode(), a.new_build.encode(), "runtime BuildID")

    if len(buf) != len(raw):
        raise SystemExit("FAIL: 尺寸变了，等长纪律被破坏")

    out = bytes(buf)
    open(a.dst, "wb").write(out)
    print(f"输出 {a.dst} ({len(out)} B) sha256={hashlib.sha256(out).hexdigest()}")
    print("提醒：旧钉必须零残留 —— 下面复核")
    if a.old_sha.encode() in out or a.old_build.encode() in out:
        raise SystemExit("FAIL: 旧钉仍有残留")
    print("  旧钉零残留 OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
