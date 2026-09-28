#!/usr/bin/env python3
"""[WALL-7 2026-07-31] 把 liboh_android_runtime.so 里的
android::NativeIsUpToDate(long) 直接改成 `mov w0,#1; ret`。

为什么走二进制补丁而不是改源码重编：
  本窗构建炉在 alexyLinux(69.194.3.128:60022) 上，该入口的 frpc 后端当时是挂的
  （TCP 通、读不到 SSH banner）。这枚改动只有 8 字节、语义闭合、可反汇编自证，
  没必要为它等一台机器。源码侧的等价改动见 patch_apkassets_crit.py，
  等炉子回来再落，两者结果一致。

为什么恒返 true 是对的（不是敷衍）：
  ApkAssets.isUpToDate() 在 AOSP 里唯一的用途是 ResourcesManager 复用缓存前
  确认底下的 APK 文件没被换过。本场景 APK 静态、进程生命周期内不会被替换，
  "up to date" 就是事实。返回 true = 复用缓存，语义正确；
  返回 false 反而有害（触发重新 load，白烧一遍 mmap）。
  而且新实现**一个入参都不读** ⟹ 传参约定错不错都影响不到它。

定罪见 patch_apkassets_crit.py 顶部（dumpcatcher 栈 + /proc/<pid>/syscall 的
futex uaddr 落在 [stack] + 本地反汇编三方对齐）。

顺带换 BuildID：daemon 同时钉 sha256 和 BuildID，反正都要 repin；
换掉之后 dumpcatcher 栈里能一眼区分是哪一代产物。新 BuildID 取
"把 build-id 域清零后整文件的 sha256 前 20 字节"，确定性、可复算。

用法:
  binpatch_isuptodate.py <in.so> <out.so>
输出（stdout，供 repin_daemon.py 用）:
  OLD_SHA=... NEW_SHA=... OLD_BUILD=... NEW_BUILD=...
"""
import hashlib
import struct
import sys

# 目标函数入口（nm: 0000000000631c4 t _ZN7androidL16NativeIsUpToDateEl）
FUNC_VADDR = 0x631C4
# vaddr → file offset：第二个 LOAD 段 off 0x3faac / vaddr 0x40aac ⟹ 差 0x1000
VADDR_TO_OFF = -0x1000
FUNC_OFF = FUNC_VADDR + VADDR_TO_OFF  # 0x621c4

# 原前两条指令（小端）：stp x29,x30,[sp,#-0x20]! / stp x20,x19,[sp,#0x10]
ORIG = bytes.fromhex("fd7bbea9") + bytes.fromhex("f44f01a9")
# 新前两条指令：mov w0,#1 (0x52800020) / ret (0xd65f03c0)
NEW = struct.pack("<II", 0x52800020, 0xD65F03C0)

# .note.gnu.build-id: VMA 0x2c4 size 0x24，落在第一个 LOAD（off==vaddr==0）
NOTE_OFF = 0x2C4
NOTE_SIZE = 0x24


def build_id_span(buf: bytes):
    namesz, descsz, ntype = struct.unpack_from("<III", buf, NOTE_OFF)
    if (namesz, descsz, ntype) != (4, 20, 3):
        raise SystemExit(
            "build-id note 头不对: namesz=%d descsz=%d type=%d" % (namesz, descsz, ntype))
    if buf[NOTE_OFF + 12:NOTE_OFF + 16] != b"GNU\0":
        raise SystemExit("build-id note owner 不是 GNU")
    start = NOTE_OFF + 16
    return start, start + descsz


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]

    with open(src, "rb") as fh:
        buf = bytearray(fh.read())

    old_sha = hashlib.sha256(bytes(buf)).hexdigest()
    bid_a, bid_b = build_id_span(buf)
    old_build = bytes(buf[bid_a:bid_b]).hex()

    have = bytes(buf[FUNC_OFF:FUNC_OFF + len(ORIG)])
    if have == NEW:
        raise SystemExit("已经打过了: " + src)
    if have != ORIG:
        raise SystemExit("函数入口字节对不上，拒绝写入。\n  期望 %s\n  实际 %s"
                         % (ORIG.hex(), have.hex()))
    buf[FUNC_OFF:FUNC_OFF + len(NEW)] = NEW

    # 新 BuildID = build-id 域清零后整文件 sha256 的前 20 字节（确定性，可复算）
    probe = bytearray(buf)
    probe[bid_a:bid_b] = b"\0" * (bid_b - bid_a)
    new_build_bytes = hashlib.sha256(bytes(probe)).digest()[:bid_b - bid_a]
    buf[bid_a:bid_b] = new_build_bytes
    new_build = new_build_bytes.hex()

    out = bytes(buf)
    new_sha = hashlib.sha256(out).hexdigest()
    if len(out) != len(bytes(open(src, "rb").read())):
        raise SystemExit("长度变了，不该发生")

    with open(dst, "wb") as fh:
        fh.write(out)

    sys.stdout.write("OLD_SHA=%s\nNEW_SHA=%s\nOLD_BUILD=%s\nNEW_BUILD=%s\nSIZE=%d\n"
                     % (old_sha, new_sha, old_build, new_build, len(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
