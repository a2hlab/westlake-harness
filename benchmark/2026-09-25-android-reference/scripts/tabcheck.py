#!/usr/bin/env python3
"""Stack the category tab strip 1.5 s after every tab tap of the given runs,
so the tab actually selected can be read off (the strip auto-scrolls to centre
the selected tab, so a fixed x does not always hit the same category)."""
import subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from analyze import winscope, drive
import numpy as np
out = sys.argv[1]; parts = []
for run in map(Path, sys.argv[2:]):
    off, ft = winscope(run / 'screen.mp4')
    for e in drive(run / 'drive.log'):
        if 'x' not in e or e['name'] == 'consent':
            continue
        i = int(np.searchsorted(ft, e['real'] - off + 1.5)) - 1
        png = run / f"tab_{e['name']}.png"
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(run / 'screen.mp4'), '-fps_mode', 'passthrough',
                        '-vf', f"select='eq(n\\,{i})',crop=1200:80:0:150,scale=900:-1", '-frames:v', '1', str(png)], check=True)
        parts.append(png); print(run.name, e['name'], len(parts) - 1)
args = sum((['-i', str(p)] for p in parts), [])
subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', *args, '-filter_complex', f"vstack=inputs={len(parts)}", out], check=True)
