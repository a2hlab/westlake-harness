#!/usr/bin/env python3
"""One-shot repair for compile_oh_adapter_bridge.sh broken-include line.
The previous sed put literal '\\n' (two chars) where a newline was needed.
"""
import sys
p = sys.argv[1] if len(sys.argv) > 1 else "/home/HanBingChen/adapter/build/compile_oh_adapter_bridge.sh"
with open(p) as f:
    txt = f.read()
needle = ('  -I$OH/foundation/window/window_manager/window_scene/session_manager_service/include \\'
          '\\n  -I$OH/out/rk3568/gen/foundation/window/window_manager/wmserver \\'
          '\\n  -I$OH/foundation/window/window_manager/wmserver/include/zidl \n')
replacement = ('  -I$OH/foundation/window/window_manager/window_scene/session_manager_service/include \\\n'
               '  -I$OH/out/rk3568/gen/foundation/window/window_manager/wmserver \\\n'
               '  -I$OH/foundation/window/window_manager/wmserver/include/zidl \\\n')
if needle not in txt:
    print("NEEDLE NOT FOUND, no change made")
    sys.exit(1)
txt = txt.replace(needle, replacement, 1)
with open(p, "w") as f:
    f.write(txt)
print("OK")
