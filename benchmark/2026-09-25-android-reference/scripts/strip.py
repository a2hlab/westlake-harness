#!/usr/bin/env python3
"""Contact sheet of frames at given offsets (s) after a tap, for eyeballing."""
import subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from analyze import winscope, drive
import numpy as np
run, tap, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
offs = [float(x) for x in sys.argv[4].split(',')]
off, ft = winscope(run / 'screen.mp4')
t = next(e['real'] - off for e in drive(run / 'drive.log') if e['name'] == tap)
idx = sorted(set(max(0, int(np.searchsorted(ft, t + o)) - 1) for o in offs))
sel = '+'.join(f'eq(n\\,{i})' for i in idx)
n = len(idx)
subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(run / 'screen.mp4'), '-fps_mode', 'passthrough',
                '-vf', f"select='{sel}',scale=240:-1,tile={n}x1",
                '-frames:v', '1', out], check=True)
print([round((ft[i] - t) * 1000) for i in idx])
