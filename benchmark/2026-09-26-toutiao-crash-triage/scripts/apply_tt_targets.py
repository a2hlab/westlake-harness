#!/usr/bin/env python3
"""#46: add the tt crypto reverse-dependency closure to a run.sh's
WESTLAKE_ANDROID_NATIVE_TARGETS (idempotent; order of existing entries kept).
usage: apply_tt_targets.py <run.sh in> <run.sh out> <lib,lib,...>
"""
import re
import sys

src, dst, add = sys.argv[1], sys.argv[2], [x for x in sys.argv[3].split(',') if x]
text = open(src).read()
pattern = re.compile(r'^(export WESTLAKE_ANDROID_NATIVE_TARGETS=)(\S*)$', re.M)
match = pattern.search(text)
if match is None or len(pattern.findall(text)) != 1:
    sys.exit('expected exactly one WESTLAKE_ANDROID_NATIVE_TARGETS export')
current = [x for x in match.group(2).split(':') if x]
merged = current + [x for x in add if x not in current]
text = text[:match.start(2)] + ':'.join(merged) + text[match.end(2):]
open(dst, 'w').write(text)
print('added %d: %s' % (len(merged) - len(current), ' '.join(x for x in merged if x not in current)))
