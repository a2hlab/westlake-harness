"""Check one complete child log and matching PID maps CSV after device testing.

Zero exit means only these assertions passed, not that UI/content/video passed.
"""
import argparse
import csv
import json
from pathlib import Path
import re

def verify(log, rows):
    counts = {name:len(re.findall(pattern, log, re.M)) for name,pattern in {
        'gles_translated': r'GLES library translated libGLESv2\.so -> /system/lib64/platformsdk/libGLESv3\.so',
        'grgl_failure': r'GrGLInterface creation failed',
        'initialize_gl_failure': r'InitializeGL failure',
        'unsatisfied_link_error': r'UnsatisfiedLinkError',
        'sigtrap': r'SIGTRAP|Fatal signal 5\b|killed by signal 5\b',
        'get_own_codec_missing': r'No implementation found.*getOwnCodecInfo',
    }.items()}
    points = [(float(r['uptime']), int(r['maps']), int(r['limit'])) for r in rows]
    maps_ok = (len(points) >= 2 and
               all(a[0] < b[0] for a,b in zip(points, points[1:])) and
               all(0 < maps < limit and limit >= 1048576 for _,maps,limit in points))
    passed = counts['gles_translated'] == 1 and all(
        count == 0 for name,count in counts.items() if name != 'gles_translated') and maps_ok
    return dict(passed=passed, counts=counts, maps_curve_valid=maps_ok, samples=len(points),
                maps_peak=max((x[1] for x in points), default=None),
                duration_s=points[-1][0]-points[0][0] if points else None,
                note='Full child log; matching PID/time coverage and visible UI must be verified separately')

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('log', type=Path); p.add_argument('maps_csv', type=Path)
    a = p.parse_args()
    with a.maps_csv.open() as f: rows = list(csv.DictReader(f))
    result = verify(a.log.read_text(errors='replace'), rows)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)

if __name__ == '__main__': main()
