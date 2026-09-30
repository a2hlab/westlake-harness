#!/usr/bin/env python3
"""Restore authenticated B91 cache; never reuse a changed TU based on mtime."""
import hashlib,json,shutil,os
from pathlib import Path
R=Path(__file__).resolve().parents[2]
expected=json.loads((R/'benchmark/2026-09-30-asset-fd-runtime/baseline-objects.json').read_text())
source=R/'bms/src/.work/b91-common-event/runtime-objects'
dest=R/'bms/src/.work/n1-native/runtime-objects';dest.mkdir(parents=True,exist_ok=True)
changed={'AndroidRuntime.o','android_graphics_compat_shim.o','android_view_SurfaceControl.o','android_util_AssetManager_aosp.o','android_media_AudioSystemCapabilities.o'}
for name,digest in expected.items():
 f=source/name
 if hashlib.sha256(f.read_bytes()).hexdigest()!=digest:raise RuntimeError('B91 object changed: '+name)
 if name in changed:
  (dest/name).unlink(missing_ok=True)
 else:
  shutil.copy2(f,dest/name);os.utime(dest/name,None)
print('N1 cache: verified original objects; five changed TUs require compilation')
