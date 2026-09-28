#!/usr/bin/env python3
"""Builds fixtures for test_resources_hap.cpp from the real G1 HelloWorld.apk.

Usage: make_resources_hap_fixtures.py <g1.apk> <out-dir>

Outputs in <out-dir>:
  g1.apk            verbatim copy of the icon-less G1 APK
  truncated.apk     first 4096 bytes — tampered package
  corrupt_icon.apk  G1 + res/mipmap-xxxhdpi-v4/ic_launcher.png with a
                    destroyed deflate stream (present but unreadable)
"""
import shutil
import struct
import sys
import zipfile

CORRUPT_ENTRY = "res/mipmap-xxxhdpi-v4/ic_launcher.png"


def main() -> int:
    src, out_dir = sys.argv[1], sys.argv[2]
    g1 = f"{out_dir}/g1.apk"
    shutil.copyfile(src, g1)

    with open(g1, "rb") as f:
        head = f.read(4096)
    with open(f"{out_dir}/truncated.apk", "wb") as f:
        f.write(head)

    # Copy every entry, adding one deflated icon entry whose compressed data
    # we then destroy in place. Central-directory metadata stays intact, so
    # unzLocateFile finds the path but unzReadCurrentFile fails — the exact
    # "present but unreadable" tampering signature.
    tmp = f"{out_dir}/corrupt_icon.apk"
    with zipfile.ZipFile(g1) as zin, \
         zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            zout.writestr(item, zin.read(item.filename))
        zout.writestr(CORRUPT_ENTRY, b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 8)

    data = bytearray(open(tmp, "rb").read())
    # Locate the entry's local header and destroy its compressed payload.
    sig = b"PK\x03\x04"
    off = 0
    destroyed = False
    while True:
        off = data.find(sig, off)
        if off < 0:
            break
        name_len = struct.unpack_from("<H", data, off + 26)[0]
        extra_len = struct.unpack_from("<H", data, off + 28)[0]
        comp_size = struct.unpack_from("<I", data, off + 18)[0]
        name = bytes(data[off + 30:off + 30 + name_len]).decode()
        payload = off + 30 + name_len + extra_len
        if name == CORRUPT_ENTRY:
            for i in range(payload, payload + comp_size):
                data[i] ^= 0xFF
            destroyed = True
            break
        off = payload + comp_size
    if not destroyed:
        print("ERROR: corrupt entry not found", file=sys.stderr)
        return 1
    open(tmp, "wb").write(data)
    print(f"fixtures ready in {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
