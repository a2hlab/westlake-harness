#!/usr/bin/env python3
"""Derive owner TU only; never produce a replacement deployment library."""
import argparse
import hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent
SOURCE_SHA = '8e922c5de969aeeebc61f4c22188611e5f909689e25b70b4db43e51d529d2650'
def derive():
    raw = (HERE/'source-profile/oh_audiotrack_shim.cpp').read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
        raise ValueError('owner profile SHA mismatch')
    marker = b'int register_AudioTrack_shim(JNIEnv* env) {'
    row = b'        { {"native_get_position", "()I", (void*)nGetPos}, true },'
    if raw.count(marker) != 1 or raw.count(row) != 1 or b'"native_get_buffer_size_frames"' in raw:
        raise ValueError('unexpected owner integration surface')
    return raw.replace(marker, b'#include "audiotrack_effective_size.inc"\n\n'+marker).replace(row, row+b'\n        { {"native_get_buffer_size_frames", "()I", (void*)nGetEffectiveBufferSizeFrames}, true },')
if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--out',type=Path,required=True); a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'oh_audiotrack_shim.cpp').write_bytes(derive())
    (a.out/'audiotrack_effective_size.inc').write_bytes((HERE/'audiotrack_effective_size.inc').read_bytes())
