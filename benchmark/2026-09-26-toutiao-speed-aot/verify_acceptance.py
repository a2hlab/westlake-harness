"""Acceptance witnesses for one child: ART app image + executable speed odex.

Also inspect mismatch/rejection text manually with the saved complete log. This
does not prove latency or that every application method was AOT compiled.
"""
import argparse
import json
from pathlib import Path
import re

def verify(log, maps, text_bytes):
    loaded = re.findall(r'^\[IMG\] Loaded /data/local/tmp/asx/oat/arm64/toutiao\.art at ', log, re.M)
    executable = []
    for line in maps.splitlines():
        parts = line.split(None, 5)
        if len(parts) == 6 and parts[5].endswith('/oat/arm64/toutiao.odex') and 'x' in parts[1]:
            lo, hi = (int(x, 16) for x in parts[0].split('-'))
            executable.append(dict(start=lo, end=hi, bytes=hi-lo, mapping=line))
    rejection = [line[:2000] for line in log.splitlines() if 'toutiao' in line.lower()
                 and re.search(r'oat_file(?:_assistant|_manager)?\.cc:\d+\]|^\[OAT',line[:200])
                 and re.search(r'checksum.*mismatch|class.loader.context.*mismatch|reject', line, re.I)]
    total = sum(x['bytes'] for x in executable)
    return dict(passed=bool(loaded) and total >= text_bytes and not rejection,
                app_image_loaded=len(loaded), executable_bytes=total, executable_mappings=executable,
                possible_rejection_lines=rejection, performance_verified=False)

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('child_log', type=Path); p.add_argument('maps', type=Path)
    a = p.parse_args()
    result = verify(a.child_log.read_text(errors='replace'), a.maps.read_text(), 483412476)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
