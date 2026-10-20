#!/usr/bin/env python3
from pathlib import Path
import hashlib
HERE=Path(__file__).resolve().parent
original=(HERE/'original.c').read_bytes();assert hashlib.sha256(original).hexdigest()=='45f0b40c168acfd47d1b83d97dc8b11aa55ae300d9e40744859785278411c92f'
start=original.index(b'int ANativeWindow_lock(void*');end=original.index(b'\nlong sysconf(int name)',start)
replacement=b'''extern int wl_r20_pair_lock(void*,void*,void*,void*);
extern int wl_r20_pair_unlock(void*,void*);
int ANativeWindow_lock(void* window, void* outBuffer, void* inOutDirtyBounds)
{
    return wl_r20_pair_lock(window,outBuffer,inOutDirtyBounds,__builtin_return_address(0));
}
int ANativeWindow_unlockAndPost(void* window)
{
    return wl_r20_pair_unlock(window,__builtin_return_address(0));
}
'''
result=original[:start]+replacement+original[end:];(HERE/'candidate.c').write_bytes(result)
print(hashlib.sha256(result).hexdigest())
